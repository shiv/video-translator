"""
Main FastAPI application for AI Video Translation Service.
This is the entry point for the web service.
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

# Initialize FastAPI application
app = FastAPI(
    title="AI Video Translation Service",
    description="A service for translating videos using AI models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize translation service
translation_service = TranslationService()

# Configure logging
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "AI Video Translation Service is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Video Translation Service",
        "version": "1.0.0"
    }


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
    processes the video using AI models, and returns the translated video.
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
        
        # Process the translation
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
                    }
                }
            )
        else:
            logger.error(f"Translation failed for file: {file.filename}, error: {result.error_message}")
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {result.error_message}"
            )
    
    except InvalidFileFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidLanguageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConfigurationError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")
    except MissingDependencyError as e:
        raise HTTPException(status_code=500, detail=f"Missing dependency: {str(e)}")
    except TranslationServiceError as e:
        raise HTTPException(status_code=500, detail=f"Translation service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during translation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/languages")
async def get_supported_languages():
    """
    Get list of supported languages.
    
    Returns the languages supported by the translation system.
    """
    # This is a placeholder - in a full implementation, we would
    # query the actual models for supported languages
    return {
        "supported_languages": {
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
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "message": "The requested resource was not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "An unexpected error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    ) 