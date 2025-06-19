# AI Video Translation Service - Phase 1: Core API Foundation

## 🎯 Project Overview

This project transforms a CLI-based video translation application into a production-ready web service MVP. **Phase 1** successfully refactors the core translation logic into a web-compatible API service.

## ✅ Phase 1 Achievements

### Core Refactoring Completed
- **✅ CLI Dependency Removal**: Eliminated `CommandLine.read_parameters()` dependency
- **✅ Service Layer Creation**: Created `TranslationService` class with parameterized interface
- **✅ Error Handling**: Converted `exit()` calls to proper exception handling for web context
- **✅ API Integration**: Built FastAPI endpoints using the refactored service
- **✅ Environment Configuration**: All settings configurable via environment variables

### Architecture Improvements
- **Modular Design**: Preserved existing service modularity while making it API-compatible
- **Structured Exceptions**: Created custom exception hierarchy for different error types
- **Type Safety**: Added Pydantic data models for request/response validation
- **Clean Separation**: Translation logic separated from presentation layer

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- FFmpeg installed
- Hugging Face account and token

### 1. Setup Environment
```bash
# Clone and navigate to project
cd open-dubbing

# Install dependencies
pip install -r requirements.txt

# Set required environment variables
export HUGGING_FACE_TOKEN="your_hf_token_here"
export HF_TOKEN="your_hf_token_here"  # Alternative name

# Optional environment variables
export LOG_LEVEL="INFO"
export DEVICE="cpu"  # or "cuda" if available
export OUTPUT_DIRECTORY="output/"
```

### 2. Start the Service
```bash
# Method 1: Direct execution
python -m uvicorn app.main:app --reload --port 8000

# Method 2: Using the main module
python app/main.py

# Method 3: Using python -m app.main (if configured)
python -m app.main
```

### 3. Verify Installation
```bash
# Run Phase 1 tests
python test_phase1.py

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/languages
```

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Available Endpoints

#### Health Check
```bash
GET /health
GET /
```

#### Language Support
```bash
GET /api/v1/languages
```

#### Video Translation
```bash
POST /api/v1/translate
```

**Parameters:**
- `file`: Video file (MP4, max 200MB)
- `target_language`: Target language (ISO 639-3 code)
- `source_language`: Source language (optional, auto-detected if not provided)
- `tts`: Text-to-speech engine (`mms`, `openai`, `api`)
- `stt`: Speech-to-text engine (`auto`, `faster-whisper`, `transformers`)
- `translator`: Translation engine (`nllb`)
- `nllb_model`: NLLB model size (`nllb-200-1.3B`, `nllb-200-3.3B`)
- `whisper_model`: Whisper model size (`medium`, `large-v2`, `large-v3`)

### Interactive API Documentation
Visit `http://localhost:8000/docs` for Swagger UI documentation.

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HUGGING_FACE_TOKEN` | Required | Hugging Face authentication token |
| `HF_TOKEN` | Required | Alternative name for HF token |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `DEVICE` | `cpu` | Processing device (cpu, cuda) |
| `OUTPUT_DIRECTORY` | `output/` | Directory for output files |
| `CPU_THREADS` | `0` | Number of CPU threads (0 = auto) |
| `VAD` | `false` | Voice Activity Detection |
| `CLEAN_INTERMEDIATE_FILES` | `false` | Clean up temporary files |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |

### TTS-Specific Configuration

#### OpenAI TTS
```bash
export OPENAI_API_KEY="your_openai_key"
```

#### Custom TTS API
```bash
export TTS_API_SERVER="http://your-tts-api-server"
```

## 🧪 Testing

### Run Phase 1 Tests
```bash
python test_phase1.py
```

### Test API with cURL
```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Languages
curl -X GET "http://localhost:8000/api/v1/languages"

# Video translation (example with dummy file)
curl -X POST "http://localhost:8000/api/v1/translate" \
  -F "file=@sample.mp4" \
  -F "target_language=spa" \
  -F "source_language=eng"
```

## 🏗 Architecture

### Service Layer Architecture
```
app/
├── main.py                     # FastAPI application
├── services/
│   └── translation_service.py  # Core translation service (NEW)
├── services/processing/
│   ├── dubbing.py              # Video dubbing pipeline
│   ├── ffmpeg.py               # FFmpeg utilities
│   └── ...
├── services/stt/               # Speech-to-text services
├── services/tts/               # Text-to-speech services
└── services/translation/       # Translation services
```

### Key Classes

#### TranslationService
```python
class TranslationService:
    """Main service for video translation without CLI dependencies."""
    
    def translate_video(self, request: TranslationRequest) -> TranslationResult:
        """Translate video with structured input/output."""
```

#### Data Models
```python
@dataclass
class TranslationRequest:
    input_file: str
    source_language: Optional[str]
    target_language: str
    # ... other parameters

@dataclass
class TranslationResult:
    success: bool
    audio_file: Optional[str]
    video_file: Optional[str]
    error_message: Optional[str]
    processing_time_seconds: Optional[float]
```

## 🔍 Comparison: Before vs After

### Before (CLI-based)
```python
# translator.py
def translate_video():
    args = CommandLine.read_parameters()  # ❌ CLI dependency
    # ... processing logic mixed with CLI concerns
    exit(ExitCode.SUCCESS)  # ❌ Direct exit calls
```

### After (API-compatible)
```python
# services/translation_service.py
class TranslationService:
    def translate_video(self, request: TranslationRequest) -> TranslationResult:
        # ✅ Parameterized input
        # ✅ Structured output
        # ✅ Proper exception handling
```

## 🎯 Next Steps (Phase 2-5)

### Phase 2: Model Management & Performance
- [ ] Application-startup model caching
- [ ] Model factory pattern implementation
- [ ] Health checks for model availability
- [ ] Resource configuration management

### Phase 3: Complete API Implementation
- [ ] SQLite job persistence
- [ ] Async job queue system
- [ ] WebSocket progress tracking
- [ ] Complete CRUD operations
- [ ] OpenAPI documentation enhancement

### Phase 4: Storage Abstraction
- [ ] File upload handling
- [ ] Local filesystem implementation
- [ ] S3 integration with feature flags
- [ ] Configuration-driven storage selection

### Phase 5: Frontend Interface
- [ ] React-based demo interface
- [ ] File upload with progress tracking
- [ ] Job status monitoring
- [ ] Download functionality

## 🚨 Troubleshooting

### Common Issues

#### FFmpeg Not Found
```bash
# Install FFmpeg
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# Verify installation
ffmpeg -version
```

#### Hugging Face Token Issues
```bash
# Verify token is set
echo $HUGGING_FACE_TOKEN

# Test token access
python -c "from transformers import AutoTokenizer; print('Token works!')"
```

#### Import Errors
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### Error Response Format
```json
{
  "error": "Error type",
  "message": "Human-readable error message",
  "detail": "Additional error details"
}
```

## 📊 Performance Notes

- **Model Loading**: Models load on first request (future: startup caching)
- **Memory Usage**: Monitor RAM usage during processing
- **Processing Time**: Varies by video length and model sizes
- **Concurrent Requests**: Currently synchronous (future: async queue)

## 🤝 Contributing

### Development Setup
```bash
# Development mode with auto-reload
python -m uvicorn app.main:app --reload --log-level debug

# Run tests before committing
python test_phase1.py
```

### Code Style
- Follow existing service modularity patterns
- Add docstrings to all public methods
- Use type hints consistently
- Handle errors gracefully with custom exceptions

---

## 📋 Summary

**Phase 1** successfully establishes the foundation for the AI Video Translation Service web API by:

1. **Removing CLI dependencies** from the core translation logic
2. **Creating a clean service interface** with parameterized inputs and structured outputs
3. **Implementing proper error handling** suitable for web applications
4. **Building FastAPI endpoints** that leverage the refactored service
5. **Maintaining all existing functionality** while making it web-compatible

The service is now ready for **Phase 2** implementation, which will focus on model management and performance optimizations.

🎉 **Ready for production demo and SDE2 interview demonstration!** 