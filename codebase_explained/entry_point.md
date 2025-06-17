# Entry Point and Initialization

This document explains how the open-dubbing application starts, initializes, and prepares for execution.

## Primary Entry Point

### Console Script Entry Point

The application is installed as a console script through `setup.py`:

```python
entry_points={
    "console_scripts": [
        "open-dubbing=open_dubbing.main:main",
    ]
}
```

When users run `open-dubbing` from the command line, it directly calls the `main()` function in `open_dubbing/main.py`.

### Main Function (`main.py:main()`)

The `main()` function serves as the primary entry point and orchestrates the entire initialization and execution process:

```python
def main():
    args = CommandLine.read_parameters()
    _init_logging(args.log_level)
    
    check_is_a_video(args.input_file)
    hugging_face_token = get_token(args.hugging_face_token)
    
    if not FFmpeg.is_ffmpeg_installed():
        msg = "You need to have ffmpeg (which includes ffprobe) installed."
        log_error_and_exit(msg, ExitCode.NO_FFMPEG)
    
    # Component initialization and execution...
```

## Initialization Sequence

### 1. Command Line Parsing

**Function:** `CommandLine.read_parameters()`
**Location:** `command_line.py`

The initialization begins with parsing command-line arguments:

```python
args = CommandLine.read_parameters()
```

**Key Parameters Parsed:**
- `input_file`: Path to the video file to be dubbed
- `target_language`: Target language for dubbing (ISO 639-3 code)
- `source_language`: Source language (optional, auto-detected if not provided)
- `hugging_face_token`: Token for accessing PyAnnote models
- `device`: Processing device ("cpu", "cuda", "mps")
- `tts`: Text-to-speech engine selection
- `translator`: Translation engine selection
- `whisper_model`: Whisper model size for speech-to-text
- `output_directory`: Directory for output files
- Various engine-specific configuration options

### 2. Logging Configuration

**Function:** `_init_logging(log_level)`
**Location:** `main.py`

Sets up the logging system with both file and console output:

```python
def _init_logging(log_level):
    logging.basicConfig(level=logging.ERROR)  # Suppress third-party loggers
    
    # Create application logger
    app_logger = logging.getLogger("open_dubbing")
    app_logger.setLevel(log_level)
    app_logger.propagate = False
    
    # File and console handlers
    file_handler = logging.FileHandler("open_dubbing.log")
    console_handler = logging.StreamHandler()
    
    # Formatter for log messages
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)
```

**Logging Features:**
- Separate application logger (`open_dubbing`) from third-party libraries
- Dual output: `open_dubbing.log` file and console
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Suppression of verbose third-party library logs

### 3. Input Validation

#### Video Format Validation

**Function:** `check_is_a_video(input_file)`
**Location:** `main.py`

```python
def check_is_a_video(input_file: str):
    _, file_extension = os.path.splitext(input_file)
    file_extension = file_extension.lower().lstrip(".")
    
    if file_extension in _ACCEPTED_VIDEO_FORMATS:
        return
    msg = f"Unsupported file format: {file_extension}"
    log_error_and_exit(msg, ExitCode.INVALID_FILEFORMAT)
```

**Supported Formats:**
- Currently only MP4 format is supported
- Future expansion planned for additional formats

#### HuggingFace Token Validation

**Function:** `get_token(provided_token)`
**Location:** `main.py`

```python
def get_token(provided_token: str) -> str:
    token = provided_token or os.getenv(HUGGING_FACE_VARNAME)
    if not token:
        msg = "You must either provide the '--hugging_face_token' argument or"
        msg += f" set the '{HUGGING_FACE_VARNAME.upper()}' environment variable."
        log_error_and_exit(msg, ExitCode.MISSING_HF_KEY)
    return token
```

**Token Sources:**
1. Command-line argument `--hugging_face_token`
2. Environment variable `HF_TOKEN`
3. Error if neither is provided

### 4. System Dependency Checks

#### FFmpeg Installation Check

**Function:** `FFmpeg.is_ffmpeg_installed()`
**Location:** `ffmpeg.py`

Verifies that FFmpeg (including ffprobe) is installed and accessible:

```python
if not FFmpeg.is_ffmpeg_installed():
    msg = "You need to have ffmpeg (which includes ffprobe) installed."
    log_error_and_exit(msg, ExitCode.NO_FFMPEG)
```

**Requirements:**
- FFmpeg must be in system PATH
- Both `ffmpeg` and `ffprobe` commands must be available

### 5. Component Factory Initialization

#### Text-to-Speech Engine Selection

**Function:** `_get_selected_tts()`
**Location:** `main.py`

Factory function that creates the appropriate TTS engine based on user selection:

```python
def _get_selected_tts(
    selected_tts: str,
    tts_cli_cfg_file: str,
    tts_api_server: str,
    device: str,
    openai_api_key: str,
):
    if selected_tts == "mms":
        tts = TextToSpeechMMS(device)
    elif selected_tts == "edge":
        tts = TextToSpeechEdge(device)
    elif selected_tts == "coqui":
        # Coqui-specific initialization with dependency checks
        try:
            from open_dubbing.coqui import Coqui
            from open_dubbing.text_to_speech_coqui import TextToSpeechCoqui
        except Exception:
            msg = "Make sure that Coqui-tts is installed by running 'pip install open-dubbing[coqui]'"
            log_error_and_exit(msg, ExitCode.NO_COQUI_TTS)
        
        tts = TextToSpeechCoqui(device)
        if not Coqui.is_espeak_ng_installed():
            msg = "To use Coqui-tts you have to have espeak or espeak-ng installed"
            log_error_and_exit(msg, ExitCode.NO_COQUI_ESPEAK)
    # Additional TTS engines...
    return tts
```

**Supported TTS Engines:**
- **MMS**: Meta's Massively Multilingual Speech
- **Edge**: Microsoft Edge TTS
- **Coqui**: Open-source neural TTS (requires additional dependencies)
- **CLI**: Custom command-line TTS tools
- **API**: Custom API-based TTS services
- **OpenAI**: OpenAI TTS API (requires API key)

#### Translation Engine Selection

**Function:** `_get_selected_translator()`
**Location:** `main.py`

Factory function for translation engine initialization:

```python
def _get_selected_translator(
    translator: str, nllb_model: str, apertium_server: str, device: str
):
    if translator == "nllb":
        translation = TranslationNLLB(device)
        translation.load_model(nllb_model)
    elif translator == "apertium":
        server = apertium_server
        if len(server) == 0:
            msg = "When using Apertium's API, you need to specify with --apertium_server the URL of the server"
            log_error_and_exit(msg, ExitCode.NO_APERTIUM_SERVER)
        
        translation = TranslationApertium(device)
        translation.set_server(server)
    return translation
```

**Supported Translation Engines:**
- **NLLB**: Meta's No Language Left Behind neural translation
- **Apertium**: Rule-based translation via API

#### Speech-to-Text Engine Selection

**Location:** `main.py`

STT engine selection with platform-specific defaults:

```python
stt_type = args.stt
if stt_type == "faster-whisper" or (stt_type == "auto" and sys.platform != "darwin"):
    stt = SpeechToTextFasterWhisper(
        model_name=args.whisper_model,
        device=args.device,
        cpu_threads=args.cpu_threads,
        vad=args.vad,
    )
else:
    stt = SpeechToTextWhisperTransformers(
        model_name=args.whisper_model,
        device=args.device,
        cpu_threads=args.cpu_threads,
    )
```

**STT Engine Logic:**
- **Faster-Whisper**: Default for Linux/Windows, optimized performance
- **Whisper Transformers**: Default for macOS, broader compatibility
- **Auto Selection**: Platform-based automatic selection
- **VAD Support**: Voice Activity Detection (Faster-Whisper only)

### 6. Model Loading and Initialization

#### Speech-to-Text Model Loading

```python
stt.load_model()
```

Loads the selected Whisper model variant:
- **Model Sizes**: tiny, base, small, medium, large, large-v2, large-v3
- **Device Placement**: Automatic GPU/CPU selection based on availability
- **Memory Management**: Efficient model loading with resource monitoring

#### Language Detection (Optional)

```python
source_language = args.source_language
if not source_language:
    source_language = stt.detect_language(args.input_file)
    logger().info(f"Detected language '{source_language}'")
```

**Language Detection Process:**
- Uses first 30 seconds of audio for detection
- Fallback to manual specification if detection fails
- Supports all Whisper-compatible languages

### 7. Language Compatibility Validation

**Function:** `check_languages()`
**Location:** `main.py`

Validates that the selected language pair is supported by all components:

```python
def check_languages(
    source_language, target_language, _tts, translation, _stt, target_language_region
):
    spt = _stt.get_languages()
    translation_languages = translation.get_language_pairs()
    tts = _tts.get_languages()
    
    # Validation checks for each component
    if source_language not in spt:
        msg = f"source language '{source_language}' is not supported by the speech recognition system"
        log_error_and_exit(msg, ExitCode.INVALID_LANGUAGE_SPT)
    
    pair = (source_language, target_language)
    if pair not in translation_languages:
        msg = f"language pair '{pair}' is not supported by the translation system"
        log_error_and_exit(msg, ExitCode.INVALID_LANGUAGE_TRANS)
    
    if target_language not in tts:
        msg = f"target language '{target_language}' is not supported by the text to speech system"
        log_error_and_exit(msg, ExitCode.INVALID_LANGUAGE_TTS)
```

### 8. Output Directory Preparation

```python
if not os.path.exists(args.output_directory):
    os.makedirs(args.output_directory)
```

Creates the output directory structure for intermediate and final files.

### 9. Platform-Specific Optimizations

#### macOS Tokenizer Configuration

```python
if sys.platform == "darwin":
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
```

Disables tokenizer parallelism on macOS to prevent threading issues.

#### CPU Thread Configuration

```python
if cpu_threads > 0:
    torch.set_num_threads(cpu_threads)
```

Configures PyTorch thread usage for optimal performance.

## Dubber Instantiation

After all initialization steps, the main `Dubber` object is created:

```python
dubber = Dubber(
    input_file=args.input_file,
    output_directory=args.output_directory,
    source_language=source_language,
    target_language=args.target_language,
    target_language_region=args.target_language_region,
    hugging_face_token=hugging_face_token,
    tts=tts,
    translation=translation,
    stt=stt,
    device=args.device,
    cpu_threads=args.cpu_threads,
    clean_intermediate_files=args.clean_intermediate_files,
    original_subtitles=args.original_subtitles,
    dubbed_subtitles=args.dubbed_subtitles,
)
```

## Execution Mode Selection

The application supports two execution modes:

### Standard Dubbing Mode

```python
if args.update:
    dubber.update()
else:
    dubber.dub()
```

**Standard Mode (`dubber.dub()`):**
- Complete dubbing pipeline execution
- Processes video from start to finish
- Generates all intermediate and final files

**Update Mode (`dubber.update()`):**
- Post-editing workflow
- Loads existing metadata and regenerates modified parts
- Allows manual adjustments to translation, timing, or voice assignment

## Error Handling During Initialization

### Standardized Error Reporting

**Function:** `log_error_and_exit(msg, code)`
**Location:** `main.py`

```python
def log_error_and_exit(msg: str, code: ExitCode):
    logger().error(msg)
    exit(code)
```

**Exit Code Categories:**
- `INVALID_FILEFORMAT`: Unsupported video format
- `MISSING_HF_KEY`: Missing HuggingFace token
- `NO_FFMPEG`: FFmpeg not installed
- `NO_COQUI_TTS`: Coqui TTS dependencies missing
- `NO_OPENAI_TTS`: OpenAI dependencies missing
- `INVALID_LANGUAGE_*`: Language compatibility issues

### Graceful Degradation

The initialization process includes several fallback mechanisms:
- Automatic STT engine selection based on platform
- Environment variable fallbacks for API keys
- Optional dependency handling for TTS engines
- Clear error messages with resolution guidance

## Summary

The initialization process ensures that:
1. All required dependencies are available
2. User configuration is valid and compatible
3. Selected components support the requested language pair
4. System resources are properly configured
5. Output directories are prepared
6. All models are loaded and ready for processing

This comprehensive initialization sequence provides a robust foundation for the dubbing pipeline execution.
