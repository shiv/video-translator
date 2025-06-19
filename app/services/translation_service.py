import logging
import os
import sys
import warnings
from typing import Optional, Dict, Any
from dataclasses import dataclass

import transformers
from iso639 import Lang

from app import logger
from app.services.processing.dubbing import Dubber, PostprocessingArtifacts
from app.services.processing.ffmpeg import FFmpeg
from app.services.stt.speech_to_text_faster_whisper import SpeechToTextFasterWhisper
from app.services.stt.speech_to_text_whisper_transformers import SpeechToTextWhisperTransformers
from app.services.tts.text_to_speech_api import TextToSpeechAPI
from app.services.tts.text_to_speech_mms import TextToSpeechMMS
from app.services.translation.translation_nllb import TranslationNLLB
from app.services.tts.text_to_speech_openai import TextToSpeechOpenAI
from app.services.util import get_env_var

@dataclass
class TranslationRequest:
    """Request parameters for video translation."""
    input_file: str
    source_language: Optional[str]
    target_language: str
    tts: str = "mms"
    stt: str = "auto"
    translator: str = "nllb"
    translator_model: str = "nllb-200-1.3B"
    stt_model: str = "medium"
    output_directory: Optional[str] = None


@dataclass
class TranslationResult:
    """Result of video translation operation."""
    success: bool
    audio_file: Optional[str] = None
    video_file: Optional[str] = None
    error_message: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class TranslationServiceError(Exception):
    """Base exception for translation service errors."""
    pass


class InvalidLanguageError(TranslationServiceError):
    """Raised when language validation fails."""
    pass


class InvalidFileFormatError(TranslationServiceError):
    """Raised when file format is not supported."""
    pass


class MissingDependencyError(TranslationServiceError):
    """Raised when required dependencies are missing."""
    pass


class ConfigurationError(TranslationServiceError):
    """Raised when configuration is invalid."""
    pass


class TranslationService:
    """Service for translating videos using AI models."""
    
    ACCEPTED_VIDEO_FORMATS = ["mp4"]
    
    def __init__(self):
        """Initialize the translation service."""
        self._init_logging()
        
    def _init_logging(self):
        """Initialize logging configuration."""
        logging.basicConfig(level=logging.ERROR)  # Suppress third-party loggers
        
        # Create application logger
        app_logger = logging.getLogger("app")
        log_level = get_env_var("LOG_LEVEL", "INFO", str, ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        app_logger.setLevel(getattr(logging, log_level))
        app_logger.propagate = False
        
        # File handler for logging to a file
        file_handler = logging.FileHandler("app.log")
        console_handler = logging.StreamHandler()
        
        # Formatter for log messages
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        app_logger.addHandler(file_handler)
        app_logger.addHandler(console_handler)
        
        transformers.logging.set_verbosity_error()
        warnings.filterwarnings("ignore", category=FutureWarning)
    
    def _get_env_var(self, var_name: str, default_value, var_type=str, choices=None):
        """Get environment variable with type conversion and validation."""
        value = os.getenv(var_name)
        
        if value is None:
            return default_value
        
        # Type conversion
        if var_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif var_type == int:
            try:
                value = int(value)
            except ValueError:
                logger().warning(f"Invalid integer value for {var_name}: {value}. Using default: {default_value}")
                return default_value
        elif var_type == str:
            pass  # No conversion needed
        
        # Validate choices if provided
        if choices and value not in choices:
            logger().warning(f"Invalid choice for {var_name}: {value}. Valid choices: {choices}. Using default: {default_value}")
            return default_value
        
        return value
    
    def _get_hugging_face_token(self) -> str:
        """Get Hugging Face token from environment variable."""
        token = os.getenv("HUGGING_FACE_TOKEN") or os.getenv("HF_TOKEN")
        if not token:
            raise ConfigurationError("Hugging Face token must be set via 'HUGGING_FACE_TOKEN' or 'HF_TOKEN' environment variable.")
        return token
    
    def _check_is_video(self, input_file: str) -> None:
        """Validate that the input file is a supported video format."""
        if not os.path.exists(input_file):
            raise InvalidFileFormatError(f"Input file does not exist: {input_file}")
        
        _, file_extension = os.path.splitext(input_file)
        file_extension = file_extension.lower().lstrip(".")
        
        if file_extension not in self.ACCEPTED_VIDEO_FORMATS:
            raise InvalidFileFormatError(f"Unsupported file format: {file_extension}. Supported formats: {self.ACCEPTED_VIDEO_FORMATS}")
    
    def _check_ffmpeg(self) -> None:
        """Check if FFmpeg is installed."""
        if not FFmpeg.is_ffmpeg_installed():
            raise MissingDependencyError("FFmpeg (which includes ffprobe) must be installed.")
    
    def _get_selected_tts(self, selected_tts: str, device: str):
        """Get the selected TTS service."""
        if selected_tts == "mms":
            return TextToSpeechMMS(device)
        elif selected_tts == "api":
            tts_api_server = get_env_var("TTS_API_SERVER", "")
            if not tts_api_server:
                raise ConfigurationError("When using TTS API, you need to set the TTS_API_SERVER environment variable")
            return TextToSpeechAPI(device, tts_api_server)
        elif selected_tts == "openai":
            key = self._get_openai_key()
            return TextToSpeechOpenAI(device=device, api_key=key)
        else:
            raise ConfigurationError(f"Invalid TTS value: {selected_tts}")
    
    def _get_selected_translator(self, translator: str, translator_model: str, device: str):
        """Get the selected translator service."""
        if translator == "nllb":
            translation = TranslationNLLB(device)
            translation.load_model(translator_model)
            return translation
        else:
            raise ConfigurationError(f"Invalid translator value: {translator}")
    
    def _get_openai_key(self) -> str:
        """Get OpenAI API key from environment variable."""
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ConfigurationError("OpenAI TTS selected but no key has been defined in the environment variable OPENAI_API_KEY")
        return key
    
    def _check_languages(self, source_language: str, target_language: str, tts, translation, stt) -> None:
        """Validate language support across all services."""
        spt = stt.get_languages()
        translation_languages = translation.get_language_pairs()
        tts_languages = tts.get_languages()
        
        if source_language not in spt:
            raise InvalidLanguageError(
                f"Source language '{source_language}' is not supported by the speech recognition system. "
                f"Supported languages: {spt}"
            )
        
        pair = (source_language, target_language)
        if pair not in translation_languages:
            raise InvalidLanguageError(f"Language pair '{pair}' is not supported by the translation system.")
        
        if target_language not in tts_languages:
            raise InvalidLanguageError(
                f"Target language '{target_language}' is not supported by the text to speech system. "
                f"Supported languages: {tts_languages}"
            )
        
        voices = tts.get_available_voices(language_code=target_language)
        if len(voices) == 0:
            raise InvalidLanguageError(f"No voices available for language '{target_language}' in the text to speech system")
    
    def translate_video(self, request: TranslationRequest) -> TranslationResult:
        """
        Translate a video from source language to target language.
        
        Args:
            request: TranslationRequest containing all necessary parameters
            
        Returns:
            TranslationResult with success status and output file paths or error message
        """
        import time
        start_time = time.time()
        
        try:
            # Validate inputs
            self._check_is_video(request.input_file)
            self._check_ffmpeg()
            
            # Get configuration from environment variables
            output_directory = request.output_directory or get_env_var("OUTPUT_DIRECTORY", "output/")
            print("output_directory", output_directory)
            device = get_env_var("DEVICE", "cpu", str, ["cpu", "cuda"])
            cpu_threads = get_env_var("CPU_THREADS", 0, int)
            vad = get_env_var("VAD", False, bool)
            clean_intermediate_files = get_env_var("CLEAN_INTERMEDIATE_FILES", False, bool)
            
            hugging_face_token = self._get_hugging_face_token()
            
            # Initialize services
            tts = self._get_selected_tts(request.tts, device)
            
            # Platform-specific configuration
            if sys.platform == "darwin":
                os.environ["TOKENIZERS_PARALLELISM"] = "false"
            
            # Initialize STT service
            stt_type = request.stt
            if stt_type == "faster-whisper" or (stt_type == "auto" and sys.platform != "darwin"):
                stt = SpeechToTextFasterWhisper(
                    model_name=request.stt_model,
                    device=device,
                    cpu_threads=cpu_threads,
                    vad=vad,
                )
            else:
                stt = SpeechToTextWhisperTransformers(
                    model_name=request.stt_model,
                    device=device,
                    cpu_threads=cpu_threads,
                )
                if vad:
                    logger().warning("VAD filter is only supported in faster-whisper Speech to Text library")
            
            stt.load_model()
            
            # Auto-detect source language if not provided
            source_language = request.source_language
            if not source_language:
                source_language = stt.detect_language(request.input_file)
                logger().info(f"Detected language '{source_language}'")
            
            # Initialize translation service
            translation = self._get_selected_translator(request.translator, request.translator_model, device)
            
            # Validate language support
            self._check_languages(source_language, request.target_language, tts, translation, stt)
            
            # Create output directory
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            
            # Initialize dubber and process video
            dubber = Dubber(
                input_file=request.input_file,
                output_directory=output_directory,
                source_language=source_language,
                target_language=request.target_language,
                hugging_face_token=hugging_face_token,
                tts=tts,
                translation=translation,
                stt=stt,
                device=device,
                cpu_threads=cpu_threads,
                clean_intermediate_files=clean_intermediate_files,
            )
            
            logger().info(f"Processing '{request.input_file}' file with STT '{stt_type}', TTS '{request.tts}' and device '{device}'")
            result = dubber.dub()
            
            processing_time = time.time() - start_time
            
            return TranslationResult(
                success=True,
                audio_file=result.audio_file,
                video_file=result.video_file,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_message = str(e)
            logger().error(f"Translation failed: {error_message}")
            
            return TranslationResult(
                success=False,
                error_message=error_message,
                processing_time_seconds=processing_time
            ) 