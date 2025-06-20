"""
AI Service Factory - Phase 2: Model Management & Performance

This module implements application-startup model caching and efficient resource management
for all AI services (STT, TTS, Translation). Models are loaded once at startup and cached
in memory for reuse across requests.
"""

import os
import sys
import time
import threading
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, VitsModel
from faster_whisper import WhisperModel

from app import logger
from app.services.util import get_env_var
from app.services.stt.speech_to_text_faster_whisper import SpeechToTextFasterWhisper
from app.services.stt.speech_to_text_whisper_transformers import SpeechToTextWhisperTransformers
from app.services.tts.text_to_speech_mms import TextToSpeechMMS
from app.services.tts.text_to_speech_openai import TextToSpeechOpenAI
from app.services.tts.text_to_speech_api import TextToSpeechAPI
from app.services.translation.translation_nllb import TranslationNLLB


class ModelType(Enum):
    """Enumeration of supported model types."""
    STT_WHISPER = "stt_whisper"
    STT_WHISPER_TRANSFORMERS = "stt_whisper_transformers" 
    TTS_MMS = "tts_mms"
    TRANSLATION_NLLB = "translation_nllb"


@dataclass
class ModelConfig:
    """Configuration for model loading and caching."""
    model_type: ModelType
    model_name: str
    device: str
    cache_key: str
    cpu_threads: int = 0
    vad: bool = False
    compute_type: Optional[str] = None


@dataclass
class CachedModel:
    """Container for cached model data."""
    model: Any
    tokenizer: Optional[Any] = None
    config: Optional[ModelConfig] = None
    load_time: float = 0.0
    memory_usage_mb: Optional[float] = None


class ModelLoadingError(Exception):
    """Raised when model loading fails."""
    pass


class AIServiceFactory:
    """
    Factory for creating and managing AI services with model caching.
    
    This singleton class manages model loading, caching, and service creation
    to optimize performance and resource usage across the application.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the AI Service Factory."""
        if not hasattr(self, '_initialized'):
            self._model_cache: Dict[str, CachedModel] = {}
            self._device = get_env_var("DEVICE", "cpu", str, ["cpu", "cuda"])
            self._cpu_threads = get_env_var("CPU_THREADS", 0, int)
            self._vad = get_env_var("VAD", False, bool)
            self._hugging_face_token = self._get_hugging_face_token()
            self._cache_enabled = get_env_var("MODEL_CACHE_ENABLED", True, bool)
            self._preload_models = get_env_var("PRELOAD_MODELS", True, bool)
            self._initialized = True
            
            # Platform-specific optimizations
            if sys.platform == "darwin":
                os.environ["TOKENIZERS_PARALLELISM"] = "false"
            
            logger().info("AI Service Factory initialized")
    
    def _get_hugging_face_token(self) -> str:
        """Get Hugging Face token from environment variables."""
        token = os.getenv("HUGGING_FACE_TOKEN") or os.getenv("HF_TOKEN")
        if not token:
            logger().warning("No Hugging Face token found. Some models may not load properly.")
        return token
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _get_cache_key(self, config: ModelConfig) -> str:
        """Generate a unique cache key for the model configuration."""
        return f"{config.model_type.value}_{config.model_name}_{config.device}_{config.cpu_threads}_{config.vad}"
    
    def _load_whisper_model(self, config: ModelConfig) -> CachedModel:
        """Load and cache a Whisper model."""
        logger().info(f"Loading Whisper model: {config.model_name} on {config.device}")
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            compute_type = "float16" if config.device == "cuda" else "int8"
            model = WhisperModel(
                model_size_or_path=config.model_name,
                device=config.device,
                cpu_threads=config.cpu_threads,
                compute_type=compute_type,
            )
            
            load_time = time.time() - start_time
            memory_usage = self._get_memory_usage() - start_memory
            
            logger().info(f"Whisper model loaded in {load_time:.2f}s, memory: {memory_usage:.1f}MB")
            
            return CachedModel(
                model=model,
                config=config,
                load_time=load_time,
                memory_usage_mb=memory_usage
            )
            
        except Exception as e:
            raise ModelLoadingError(f"Failed to load Whisper model {config.model_name}: {str(e)}")
    
    def _load_whisper_transformers_model(self, config: ModelConfig) -> CachedModel:
        """Load and cache a Whisper Transformers model."""
        logger().info(f"Loading Whisper Transformers model: {config.model_name} on {config.device}")
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            # This will be handled by the actual SpeechToTextWhisperTransformers class
            # We cache a placeholder for now since the transformers implementation
            # handles model loading internally
            model = {"model_name": config.model_name, "device": config.device}
            
            load_time = time.time() - start_time
            memory_usage = self._get_memory_usage() - start_memory
            
            logger().info(f"Whisper Transformers model prepared in {load_time:.2f}s")
            
            return CachedModel(
                model=model,
                config=config,
                load_time=load_time,
                memory_usage_mb=memory_usage
            )
            
        except Exception as e:
            raise ModelLoadingError(f"Failed to prepare Whisper Transformers model {config.model_name}: {str(e)}")
    
    def _load_nllb_model(self, config: ModelConfig) -> CachedModel:
        """Load and cache an NLLB translation model."""
        logger().info(f"Loading NLLB model: {config.model_name} on {config.device}")
        start_time = time.time()
        start_memory = self._get_memory_usage()
        
        try:
            model_name = f"facebook/{config.model_name}"
            
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Load model with device fallback
            try:
                model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(config.device)
            except RuntimeError as e:
                if config.device == "cuda":
                    logger().warning(f"Loading NLLB model {model_name} on CPU due to GPU error")
                    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to("cpu")
                else:
                    raise e
            
            load_time = time.time() - start_time
            memory_usage = self._get_memory_usage() - start_memory
            
            logger().info(f"NLLB model loaded in {load_time:.2f}s, memory: {memory_usage:.1f}MB")
            
            return CachedModel(
                model=model,
                tokenizer=tokenizer,
                config=config,
                load_time=load_time,
                memory_usage_mb=memory_usage
            )
            
        except Exception as e:
            raise ModelLoadingError(f"Failed to load NLLB model {config.model_name}: {str(e)}")
    
    def _load_mms_model_info(self, config: ModelConfig) -> CachedModel:
        """Cache MMS model information (models loaded on-demand per language)."""
        logger().info(f"Preparing MMS TTS model cache for device: {config.device}")
        start_time = time.time()
        
        # MMS models are loaded on-demand per language, so we just cache the configuration
        model_info = {
            "device": config.device,
            "model_pattern": "facebook/mms-tts-{language}",
            "supported_languages": TextToSpeechMMS(config.device).get_languages()
        }
        
        load_time = time.time() - start_time
        
        logger().info(f"MMS TTS model info cached in {load_time:.2f}s")
        
        return CachedModel(
            model=model_info,
            config=config,
            load_time=load_time,
            memory_usage_mb=0.0  # Models loaded on-demand
        )
    
    def load_model(self, config: ModelConfig) -> CachedModel:
        """
        Load and cache a model based on configuration.
        
        Args:
            config: Model configuration specifying type, name, device, etc.
            
        Returns:
            CachedModel containing the loaded model and metadata
            
        Raises:
            ModelLoadingError: If model loading fails
        """
        cache_key = self._get_cache_key(config)
        
        # Return cached model if available
        if self._cache_enabled and cache_key in self._model_cache:
            logger().debug(f"Using cached model: {cache_key}")
            return self._model_cache[cache_key]
        
        # Load model based on type
        if config.model_type == ModelType.STT_WHISPER:
            cached_model = self._load_whisper_model(config)
        elif config.model_type == ModelType.STT_WHISPER_TRANSFORMERS:
            cached_model = self._load_whisper_transformers_model(config)
        elif config.model_type == ModelType.TRANSLATION_NLLB:
            cached_model = self._load_nllb_model(config)
        elif config.model_type == ModelType.TTS_MMS:
            cached_model = self._load_mms_model_info(config)
        else:
            raise ModelLoadingError(f"Unsupported model type: {config.model_type}")
        
        # Cache the loaded model
        if self._cache_enabled:
            self._model_cache[cache_key] = cached_model
            logger().debug(f"Model cached with key: {cache_key}")
        
        return cached_model
    
    def get_stt_service(self, stt_type: str, model_name: str) -> Any:
        """
        Get a Speech-to-Text service with cached model.
        
        Args:
            stt_type: Type of STT service ("auto", "faster-whisper", "transformers")
            model_name: Name of the model to use
            
        Returns:
            Configured STT service instance
        """
        # Determine actual STT type
        if stt_type == "auto":
            actual_stt_type = "faster-whisper" if sys.platform != "darwin" else "transformers"
        else:
            actual_stt_type = stt_type
        
        if actual_stt_type == "faster-whisper":
            # Create model configuration
            config = ModelConfig(
                model_type=ModelType.STT_WHISPER,
                model_name=model_name,
                device=self._device,
                cache_key="",
                cpu_threads=self._cpu_threads,
                vad=self._vad
            )
            config.cache_key = self._get_cache_key(config)
            
            # Load/get cached model
            cached_model = self.load_model(config)
            
            # Create service with cached model
            service = SpeechToTextFasterWhisper(
                model_name=model_name,
                device=self._device,
                cpu_threads=self._cpu_threads,
                vad=self._vad
            )
            service._model = cached_model.model
            
            return service
            
        elif actual_stt_type == "transformers":
            # Create model configuration for transformers
            config = ModelConfig(
                model_type=ModelType.STT_WHISPER_TRANSFORMERS,
                model_name=model_name,
                device=self._device,
                cache_key="",
                cpu_threads=self._cpu_threads
            )
            config.cache_key = self._get_cache_key(config)
            
            # Load/get cached model info
            cached_model = self.load_model(config)
            
            # Create service (transformers handles its own model loading)
            service = SpeechToTextWhisperTransformers(
                model_name=model_name,
                device=self._device,
                cpu_threads=self._cpu_threads
            )
            
            return service
        
        else:
            raise ValueError(f"Unsupported STT type: {stt_type}")
    
    def get_translation_service(self, translator_type: str, model_name: str) -> Any:
        """
        Get a Translation service with cached model.
        
        Args:
            translator_type: Type of translation service ("nllb")
            model_name: Name of the model to use
            
        Returns:
            Configured Translation service instance
        """
        if translator_type == "nllb":
            # Create model configuration
            config = ModelConfig(
                model_type=ModelType.TRANSLATION_NLLB,
                model_name=model_name,
                device=self._device,
                cache_key=""
            )
            config.cache_key = self._get_cache_key(config)
            
            # Load/get cached model
            cached_model = self.load_model(config)
            
            # Create service with cached model
            service = TranslationNLLB(self._device)
            service.model_name = f"facebook/{model_name}"
            service.tokenizer = cached_model.tokenizer
            service._cached_model = cached_model.model
            
            return service
        
        else:
            raise ValueError(f"Unsupported translation type: {translator_type}")
    
    def get_tts_service(self, tts_type: str) -> Any:
        """
        Get a Text-to-Speech service with cached model info.
        
        Args:
            tts_type: Type of TTS service ("mms", "openai", "api")
            
        Returns:
            Configured TTS service instance
        """
        if tts_type == "mms":
            # Create model configuration for MMS
            config = ModelConfig(
                model_type=ModelType.TTS_MMS,
                model_name="mms",
                device=self._device,
                cache_key=""
            )
            config.cache_key = self._get_cache_key(config)
            
            # Load/get cached model info
            cached_model = self.load_model(config)
            
            # Create service
            service = TextToSpeechMMS(self._device)
            service._cached_model_info = cached_model.model
            
            return service
            
        elif tts_type == "openai":
            # OpenAI TTS doesn't need model caching
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OpenAI API key required for OpenAI TTS")
            return TextToSpeechOpenAI(device=self._device, api_key=openai_key)
            
        elif tts_type == "api":
            # Custom TTS API doesn't need model caching
            api_server = get_env_var("TTS_API_SERVER", "")
            if not api_server:
                raise ValueError("TTS_API_SERVER environment variable required for API TTS")
            return TextToSpeechAPI(self._device, api_server)
        
        else:
            raise ValueError(f"Unsupported TTS type: {tts_type}")
    
    def preload_default_models(self):
        """
        Preload commonly used models at startup.
        
        This method loads the most commonly used models based on environment
        configuration to improve first-request performance.
        """
        if not self._preload_models:
            logger().info("Model preloading disabled")
            return
        
        logger().info("Starting model preloading...")
        start_time = time.time()
        
        # Get default model names from environment variables
        default_stt_model = get_env_var("DEFAULT_STT_MODEL")
        default_translation_model = get_env_var("DEFAULT_TRANSLATION_MODEL")
        
        # Default models to preload
        default_models = [
            # STT models
            ModelConfig(
                model_type=ModelType.STT_WHISPER,
                model_name=default_stt_model,
                device=self._device,
                cache_key="",
                cpu_threads=self._cpu_threads,
                vad=self._vad
            ),
            # Translation models
            ModelConfig(
                model_type=ModelType.TRANSLATION_NLLB,
                model_name=default_translation_model,
                device=self._device,
                cache_key=""
            ),
            # TTS model info
            ModelConfig(
                model_type=ModelType.TTS_MMS,
                model_name="mms",
                device=self._device,
                cache_key=""
            )
        ]
        
        # Load each model
        loaded_count = 0
        for config in default_models:
            try:
                config.cache_key = self._get_cache_key(config)
                self.load_model(config)
                loaded_count += 1
            except Exception as e:
                logger().error(f"Failed to preload model {config.model_name}: {str(e)}")
        
        total_time = time.time() - start_time
        logger().info(f"Model preloading completed: {loaded_count}/{len(default_models)} models loaded in {total_time:.2f}s")
    
    def get_model_status(self) -> Dict[str, Any]:
        """
        Get status information about cached models.
        
        Returns:
            Dictionary containing model cache statistics and health information
        """
        total_memory = sum(
            model.memory_usage_mb or 0 
            for model in self._model_cache.values()
        )
        
        models_info = []
        for cache_key, cached_model in self._model_cache.items():
            models_info.append({
                "cache_key": cache_key,
                "model_type": cached_model.config.model_type.value if cached_model.config else "unknown",
                "model_name": cached_model.config.model_name if cached_model.config else "unknown",
                "device": cached_model.config.device if cached_model.config else "unknown",
                "load_time_seconds": cached_model.load_time,
                "memory_usage_mb": cached_model.memory_usage_mb
            })
        
        return {
            "cache_enabled": self._cache_enabled,
            "preload_enabled": self._preload_models,
            "total_cached_models": len(self._model_cache),
            "total_memory_mb": total_memory,
            "device": self._device,
            "cpu_threads": self._cpu_threads,
            "models": models_info
        }
    
    def clear_cache(self):
        """Clear all cached models to free memory."""
        logger().info("Clearing model cache...")
        
        # Clear PyTorch cache if using CUDA
        if self._device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # Clear model cache
        cleared_count = len(self._model_cache)
        self._model_cache.clear()
        
        logger().info(f"Model cache cleared: {cleared_count} models removed")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the AI Service Factory.
        
        Returns:
            Dictionary containing health status and diagnostic information
        """
        try:
            # Check basic functionality
            status = {
                "status": "healthy",
                "cache_enabled": self._cache_enabled,
                "device": self._device,
                "cached_models": len(self._model_cache),
                "memory_usage_mb": self._get_memory_usage(),
                "torch_cuda_available": torch.cuda.is_available() if hasattr(torch.cuda, 'is_available') else False
            }
            
            # Check CUDA availability if device is set to cuda
            if self._device == "cuda":
                if torch.cuda.is_available():
                    status["cuda_device_count"] = torch.cuda.device_count()
                    status["cuda_current_device"] = torch.cuda.current_device()
                else:
                    status["status"] = "warning"
                    status["warning"] = "CUDA device requested but not available"
            
            return status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "cache_enabled": self._cache_enabled,
                "device": self._device
            }


# Global factory instance
_ai_factory = None

def get_ai_factory() -> AIServiceFactory:
    """Get the global AI Service Factory instance."""
    global _ai_factory
    if _ai_factory is None:
        _ai_factory = AIServiceFactory()
    return _ai_factory