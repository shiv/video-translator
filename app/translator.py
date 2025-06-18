import logging
import os
import sys
import warnings

import transformers

from iso639 import Lang

from app import logger
from app.command_line import CommandLine
from app.services.processing.dubbing import Dubber
from app.exit_code import ExitCode
from app.services.processing.ffmpeg import FFmpeg
from app.services.stt.speech_to_text_faster_whisper import SpeechToTextFasterWhisper
from app.services.stt.speech_to_text_whisper_transformers import (
    SpeechToTextWhisperTransformers,
)
from app.services.tts.text_to_speech_api import TextToSpeechAPI
from app.services.tts.text_to_speech_mms import TextToSpeechMMS
from app.services.translation.translation_nllb import TranslationNLLB
from app.services.tts.text_to_speech_openai import TextToSpeechOpenAI


def _init_logging(log_level):
    logging.basicConfig(level=logging.ERROR)  # Suppress third-party loggers

    # Create your application logger
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
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


def log_error_and_exit(msg: str, code: ExitCode):
    logger().error(msg)
    exit(code)


def check_languages(
    source_language, target_language, _tts, translation, _stt
):
    spt = _stt.get_languages()
    translation_languages = translation.get_language_pairs()
    logger().debug(f"check_languages. Pairs {len(translation_languages)}")

    tts = _tts.get_languages()

    if source_language not in spt:
        msg = f"source language '{source_language}' is not supported by the speech recognition system. Supported languages: '{spt}'"
        log_error_and_exit(msg, ExitCode.INVALID_LANGUAGE_SPT)

    pair = (source_language, target_language)
    if pair not in translation_languages:
        msg = f"language pair '{pair}' is not supported by the translation system."
        log_error_and_exit(msg, ExitCode.INVALID_LANGUAGE_TRANS)

    if target_language not in tts:
        msg = f"target language '{target_language}' is not supported by the text to speech system. Supported languages: '{tts}'"
        log_error_and_exit(msg, ExitCode.INVALID_LANGUAGE_TTS)

    voices = _tts.get_available_voices(language_code=target_language)
    if len(voices) == 0:
        msg = f"no voices available for language '{target_language}' in the text to speech system"
        log_error_and_exit(msg, ExitCode.INVALID_LANGUAGE_TTS)


_ACCEPTED_VIDEO_FORMATS = ["mp4"]


def check_is_a_video(input_file: str):
    _, file_extension = os.path.splitext(input_file)
    file_extension = file_extension.lower().lstrip(".")

    if file_extension in _ACCEPTED_VIDEO_FORMATS:
        return
    msg = f"Unsupported file format: {file_extension}"
    log_error_and_exit(msg, ExitCode.INVALID_FILEFORMAT)


HUGGING_FACE_VARNAME = "HF_TOKEN"


def get_env_var(var_name: str, default_value, var_type=str, choices=None):
    """Get environment variable with type conversion and validation."""
    value = os.getenv(var_name)
    
    if value is None:
        return default_value
    
    # Type conversion
    if var_type == bool:
        # For boolean environment variables, check for truthy values
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


def get_hugging_face_token() -> str:
    """Get Hugging Face token from environment variable."""
    token = os.getenv("HUGGING_FACE_TOKEN") or os.getenv(HUGGING_FACE_VARNAME)
    if not token:
        msg = f"Hugging Face token must be set via 'HUGGING_FACE_TOKEN' or '{HUGGING_FACE_VARNAME}' environment variable."
        log_error_and_exit(msg, ExitCode.MISSING_HF_KEY)
    return token


def _get_language_names(languages_iso_639_3):
    names = []
    for language in languages_iso_639_3:
        o = Lang(language)
        names.append(o.name)
    return sorted(names)


def list_supported_languages(_tts, translation, device):  # TODO: Not used
    s = SpeechToTextFasterWhisper(device=device)
    s.load_model()
    spt = s.get_languages()
    trans = translation.get_languages()
    tts = _tts.get_languages()

    source = _get_language_names(set(spt).intersection(set(trans)))
    print(f"Supported source languages: {source}")

    target = _get_language_names(set(tts).intersection(set(trans)))
    print(f"Supported target languages: {target}")


def _get_selected_tts(
    selected_tts: str,
    device: str,
):
    if selected_tts == "mms":
        tts = TextToSpeechMMS(device)
    elif selected_tts == "api":
        tts_api_server = get_env_var("TTS_API_SERVER", "")
        tts = TextToSpeechAPI(device, tts_api_server)
        if len(tts_api_server) == 0:
            msg = "When using TTS's API, you need to set the TTS_API_SERVER environment variable"
            log_error_and_exit(msg, ExitCode.NO_TTS_API_SERVER)
    elif selected_tts == "openai":
        key = _get_openai_key()
        tts = TextToSpeechOpenAI(device=device, api_key=key)
    else:
        raise ValueError(f"Invalid tts value {selected_tts}")

    return tts


def _get_selected_translator(
    translator: str, nllb_model: str, device: str
):
    if translator == "nllb":
        translation = TranslationNLLB(device)
        translation.load_model(nllb_model)
    else:
        raise ValueError(f"Invalid translator value {translator}")

    return translation


def _get_openai_key():
    VAR = "OPENAI_API_KEY"
    key = os.getenv(VAR)
    if key:
        return key

    msg = f"OpenAI TTS selected but no key has been defined in the environment variable {VAR}"
    log_error_and_exit(msg, ExitCode.NO_OPENAI_KEY)


def translate_video():

    args = CommandLine.read_parameters()
    
    # Get configuration from environment variables
    output_directory = get_env_var("OUTPUT_DIRECTORY", "output/")
    log_level = get_env_var("LOG_LEVEL", "INFO", str, ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    device = get_env_var("DEVICE", "cpu", str, ["cpu", "cuda"])
    cpu_threads = get_env_var("CPU_THREADS", 0, int)
    vad = get_env_var("VAD", False, bool)
    clean_intermediate_files = get_env_var("CLEAN_INTERMEDIATE_FILES", False, bool)
    
    _init_logging(log_level)

    check_is_a_video(args.input_file)

    hugging_face_token = get_hugging_face_token()

    if not FFmpeg.is_ffmpeg_installed():
        msg = "You need to have ffmpeg (which includes ffprobe) installed."
        log_error_and_exit(msg, ExitCode.NO_FFMPEG)

    tts = _get_selected_tts(
        args.tts,
        device,
    )

    if sys.platform == "darwin":
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

    stt_type = args.stt
    stt_text = args.stt
    if stt_type == "faster-whisper" or (
        stt_type == "auto" and sys.platform != "darwin"
    ):
        stt = SpeechToTextFasterWhisper(
            model_name=args.whisper_model,
            device=device,
            cpu_threads=cpu_threads,
            vad=vad,
        )
        if vad:
            stt_text += " (with vad filter)"
    else:
        stt = SpeechToTextWhisperTransformers(
            model_name=args.whisper_model,
            device=device,
            cpu_threads=cpu_threads,
        )
        if vad:
            logger().warning(
                "Vad filter is only supported in fasterwhisper Speech to Text library"
            )

    stt.load_model()
    source_language = args.source_language
    if not source_language:
        source_language = stt.detect_language(args.input_file)
        logger().info(f"Detected language '{source_language}'")

    translation = _get_selected_translator(
        args.translator, args.nllb_model, device
    )

    check_languages(
        source_language,
        args.target_language,
        tts,
        translation,
        stt,
    )

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    dubber = Dubber(
        input_file=args.input_file,
        output_directory=output_directory,
        source_language=source_language,
        target_language=args.target_language,
        hugging_face_token=hugging_face_token,
        tts=tts,
        translation=translation,
        stt=stt,
        device=device,
        cpu_threads=cpu_threads,
        clean_intermediate_files=clean_intermediate_files,
    )

    logger().info(
        f"Processing '{args.input_file}' file with stt '{stt_text}', tts '{args.tts}' and device '{device}'"
    )
    dubber.dub()


if __name__ == "__main__":
    translate_video()
