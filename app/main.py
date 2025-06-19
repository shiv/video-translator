"""
Main FastAPI application for AI Video Translation Service.
This is the entry point for the web service with Phase 2 model caching.
"""

import os
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import shutil

from app.services.translation_service import (
    TranslationService, 
    TranslationRequest, 
    TranslationResult,
    TranslationServiceError,
    InvalidLanguageError,
    InvalidFileFormatError,
    MissingDependencyError,
    ConfigurationError
)
from app.services.util import get_env_var
from app.services.ai_service_factory import get_ai_factory, ModelLoadingError

# Initialize FastAPI application
app = FastAPI(
    title="AI Video Translation Service",
    description="A service for translating videos using AI models with performance optimizations",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize translation service (this will also initialize the AI factory)
translation_service = TranslationService()

# Configure logging
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup with model preloading."""
    logger.info("Starting AI Video Translation Service...")
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs(get_env_var("OUTPUT_DIRECTORY", "output/"), exist_ok=True)
    
    # Initialize AI Service Factory and preload models
    ai_factory = get_ai_factory()
    logger.info("AI Service Factory initialized")
    
    # Preload default models for better performance
    try:
        ai_factory.preload_default_models()
        logger.info("Model preloading completed")
    except Exception as e:
        logger.error(f"Model preloading failed: {e}")
        # Continue startup even if preloading fails
    
    logger.info("AI Video Translation Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down AI Video Translation Service...")
    
    # Clear model cache
    try:
        ai_factory = get_ai_factory()
        ai_factory.clear_cache()
        logger.info("Model cache cleared")
    except Exception as e:
        logger.error(f"Error clearing model cache: {e}")
    
    logger.info("AI Video Translation Service shut down")


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "message": "AI Video Translation Service",
        "version": "2.0.0",
        "features": [
            "Model caching and preloading",
            "Performance optimization",
            "Multi-language support",
            "Video translation up to 200MB"
        ],
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "models": "/api/v1/models",
            "translate": "/api/v1/translate",
            "languages": "/api/v1/languages"
        }
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        health_status = translation_service.health_check()
        
        # Determine HTTP status code based on health
        status_code = 200
        if health_status.get("status") == "warning":
            status_code = 200  # Warning is still OK
        elif health_status.get("status") == "unhealthy":
            status_code = 503  # Service Unavailable
            
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": f"Health check failed: {str(e)}",
                "service": "AI Video Translation Service",
                "version": "2.0.0"
            }
        )


@app.get("/api/v1/models")
async def get_model_status():
    """
    Get status information about cached models and AI services.
    
    This endpoint provides detailed information about loaded models,
    memory usage, and performance metrics.
    """
    try:
        model_status = translation_service.get_model_status()
        
        return {
            "status": "success",
            "timestamp": os.popen('date -u +"%Y-%m-%dT%H:%M:%S.%fZ"').read().strip(),
            "model_cache": model_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model status: {str(e)}"
        )


@app.post("/api/v1/translate")
async def translate_video(
    file: UploadFile = File(..., description="Video file to translate (MP4 format, max 200MB)"),
    target_language: str = Form(..., description="Target language for translation (ISO 639-3 code)"),
    source_language: Optional[str] = Form(None, description="Source language (ISO 639-3 code). If not provided, will be auto-detected"),
    tts: str = Form("mms", description="Text-to-speech engine (mms, openai, api)"),
    stt: str = Form("auto", description="Speech-to-text engine (auto, faster-whisper, transformers)"),
    translator: str = Form("nllb", description="Translation engine (nllb)"),
    translator_model: str = Form("nllb-200-1.3B", description="NLLB model size (nllb-200-1.3B, nllb-200-3.3B)"),
    stt_model: str = Form("medium", description="Whisper model size (medium, large-v2, large-v3)")
):
    """
    Translate a video from source language to target language.
    
    This endpoint accepts a video file and translation parameters,
    processes the video using cached AI models, and returns the translated video.
    Performance is optimized through model caching and preloading.
    """
    
    # Validate file size (200MB limit)
    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB in bytes
    
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size ({file.size} bytes) exceeds maximum allowed size ({MAX_FILE_SIZE} bytes)"
        )
    
    # Validate file format
    if not file.filename.lower().endswith('.mp4'):
        raise HTTPException(
            status_code=400,
            detail="Only MP4 video files are supported"
        )
    
    # Create temporary file for processing
    temp_dir = get_env_var("OUTPUT_DIRECTORY", "output/")
    temp_file_path = None
    
    try:
        # Save uploaded file to temporary location
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create translation request
        request = TranslationRequest(
            input_file=temp_file_path,
            source_language=source_language,
            target_language=target_language,
            tts=tts,
            stt=stt,
            translator=translator,
            translator_model=translator_model,
            stt_model=stt_model,
            output_directory=temp_dir
        )
        
        # Process the translation using cached models
        logger.info(f"Starting translation for file: {file.filename}")
        result = translation_service.translate_video(request)
        
        if result.success:
            logger.info(f"Translation completed successfully for file: {file.filename}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Video translation completed successfully",
                    "result": {
                        "audio_file": result.audio_file,
                        "video_file": result.video_file,
                        "processing_time_seconds": result.processing_time_seconds
                    },
                    "performance": {
                        "used_cached_models": True,
                        "processing_time_seconds": result.processing_time_seconds
                    }
                }
            )
        else:
            logger.error(f"Translation failed for file: {file.filename}, error: {result.error_message}")
            
            # Determine appropriate HTTP status code based on error type
            if "Model loading failed" in result.error_message:
                status_code = 503  # Service Unavailable
            elif any(keyword in result.error_message.lower() for keyword in ["language", "format", "dependency"]):
                status_code = 400  # Bad Request
            else:
                status_code = 500  # Internal Server Error
                
            raise HTTPException(
                status_code=status_code,
                detail=result.error_message
            )
    
    except InvalidFileFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidLanguageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except MissingDependencyError as e:
        raise HTTPException(status_code=500, detail=f"Missing dependency: {str(e)}")
    except ModelLoadingError as e:
        raise HTTPException(status_code=503, detail=f"Model loading failed: {str(e)}")
    except TranslationServiceError as e:
        raise HTTPException(status_code=500, detail=f"Translation service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during translation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/languages")
async def get_supported_languages():
    """
    Get list of supported languages.
    
    Returns the languages supported by the translation system with enhanced
    information about model availability and performance.
    """
    try:
        # Get model status to provide enhanced language information
        model_status = translation_service.get_model_status()
        
        # Basic language support (placeholder - would be enhanced with actual model queries)
        languages = {
            "source_languages": [
                {"code": "eng", "name": "English"},
                {"code": "spa", "name": "Spanish"},
                {"code": "fra", "name": "French"},
                {"code": "deu", "name": "German"},
                {"code": "ita", "name": "Italian"},
                {"code": "por", "name": "Portuguese"},
                {"code": "jpn", "name": "Japanese"},
                {"code": "kor", "name": "Korean"},
                {"code": "cmn", "name": "Chinese (Mandarin)"},
                {"code": "hin", "name": "Hindi"}
            ],
            "target_languages": [
                {"code": "eng", "name": "English"},
                {"code": "spa", "name": "Spanish"},
                {"code": "fra", "name": "French"},
                {"code": "deu", "name": "German"},
                {"code": "ita", "name": "Italian"},
                {"code": "por", "name": "Portuguese"},
                {"code": "jpn", "name": "Japanese"},
                {"code": "kor", "name": "Korean"},
                {"code": "cmn", "name": "Chinese (Mandarin)"},
                {"code": "hin", "name": "Hindi"}
            ]
        }
        
        return {
            "supported_languages": languages,
            "model_info": {
                "cached_models": model_status.get("total_cached_models", 0),
                "cache_enabled": model_status.get("cache_enabled", False),
                "device": model_status.get("device", "unknown")
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting supported languages: {str(e)}")
        # Return basic language list even if model status fails
        return {
            "supported_languages": {
                "source_languages": [
                    {"code": "eng", "name": "English"},
                    {"code": "spa", "name": "Spanish"},
                    {"code": "fra", "name": "French"}
                ],
                "target_languages": [
                    {"code": "eng", "name": "English"},
                    {"code": "spa", "name": "Spanish"},
                    {"code": "fra", "name": "French"}
                ]
            },
            "model_info": {
                "error": "Could not retrieve model information"
            }
        }


@app.post("/api/v1/models/preload")
async def preload_models():
    """
    Manually trigger model preloading.
    
    This endpoint allows administrators to preload models without waiting
    for the first translation request.
    """
    try:
        ai_factory = get_ai_factory()
        ai_factory.preload_default_models()
        
        # Get updated model status
        model_status = translation_service.get_model_status()
        
        return {
            "success": True,
            "message": "Model preloading triggered successfully",
            "model_status": model_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model preloading failed: {str(e)}"
        )


@app.delete("/api/v1/models/cache")
async def clear_model_cache():
    """
    Clear the model cache to free memory.
    
    This endpoint allows administrators to clear cached models,
    which will free memory but may slow down subsequent requests.
    """
    try:
        ai_factory = get_ai_factory()
        ai_factory.clear_cache()
        
        return {
            "success": True,
            "message": "Model cache cleared successfully",
            "note": "Subsequent requests may be slower until models are reloaded"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear model cache: {str(e)}"
        )


# Enhanced error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "message": "The requested resource was not found",
            "service": "AI Video Translation Service",
            "version": "2.0.0"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "service": "AI Video Translation Service",
            "version": "2.0.0"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = get_env_var("HOST", "0.0.0.0")
    port = int(get_env_var("PORT", "8000"))
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )