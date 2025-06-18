# Environment Variables Configuration

The following environment variables can be used to configure open-dubbing instead of command line arguments:

> **Quick Start**: Copy `env.example` to `.env` and set your values, then source it with `source .env` or use it with Docker.

## Required Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `HUGGING_FACE_TOKEN` or `HF_TOKEN` | Hugging Face API token for PyAnnote models | None (required) | `hf_xxxxxxxxxxxxx` |

## Optional Environment Variables

| Variable | Description | Default | Valid Values | Example |
|----------|-------------|---------|--------------|---------|
| `OUTPUT_DIRECTORY` | Directory to save output files | `output/` | Any valid path | `/path/to/output` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `DEBUG` |
| `DEVICE` | Device to use for inference | `cpu` | `cpu`, `cuda` | `cuda` |
| `CPU_THREADS` | Number of CPU threads for inference | `0` | Any integer (0 = auto) | `4` |
| `VAD` | Enable VAD filter for faster-whisper | `false` | `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` | `true` |
| `CLEAN_INTERMEDIATE_FILES` | Clean intermediate files after processing | `false` | `true`, `false`, `1`, `0`, `yes`, `no`, `on`, `off` | `true` |
| `OPENAI_API_KEY` | OpenAI API key (required when using OpenAI TTS) | None | OpenAI API key | `sk-xxxxxxxxxxxxx` |
| `TTS_API_SERVER` | TTS API server URL (required when using API TTS) | Empty string | Any valid URL | `http://localhost:8080` |

## Usage Examples

### Basic Setup (Bash/Zsh)
```bash
export HUGGING_FACE_TOKEN="hf_xxxxxxxxxxxxx"
export OUTPUT_DIRECTORY="/home/user/dubbing_output"
export LOG_LEVEL="DEBUG"
export DEVICE="cuda"
export VAD="true"
```

### Using OpenAI TTS
```bash
export HUGGING_FACE_TOKEN="hf_xxxxxxxxxxxxx"
export OPENAI_API_KEY="sk-xxxxxxxxxxxxx"
export DEVICE="cuda"
```

### Using Custom TTS API
```bash
export HUGGING_FACE_TOKEN="hf_xxxxxxxxxxxxx"
export TTS_API_SERVER="http://localhost:8080"
```

### Docker Environment File (.env)
```env
HUGGING_FACE_TOKEN=hf_xxxxxxxxxxxxx
OUTPUT_DIRECTORY=/app/output
LOG_LEVEL=INFO
DEVICE=cpu
VAD=true
CLEAN_INTERMEDIATE_FILES=true
```

## Migration from Command Line Arguments

The following command line arguments have been moved to environment variables:

- `--output_directory` → `OUTPUT_DIRECTORY`
- `--hugging_face_token` → `HUGGING_FACE_TOKEN` or `HF_TOKEN`
- `--openai_api_key` → `OPENAI_API_KEY`
- `--vad` → `VAD`
- `--device` → `DEVICE`
- `--cpu_threads` → `CPU_THREADS`
- `--clean-intermediate-files` → `CLEAN_INTERMEDIATE_FILES`
- `--log_level` → `LOG_LEVEL`
- `--tts_api_server` → `TTS_API_SERVER`

## Remaining Command Line Arguments

These arguments are still available as command line options:

- `--input_file` (required)
- `--source_language`
- `--target_language` (required)
- `--tts`
- `--stt`
- `--translator`
- `--nllb_model`
- `--whisper_model` 