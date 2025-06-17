# Project Overview

## Purpose and Main Functionality

**Open-dubbing** is an experimental AI-powered video dubbing system that uses machine learning models to automatically translate and synchronize audio dialogue into different languages. The system is designed as a command-line tool that processes video files through a sophisticated pipeline combining speech recognition, translation, and text-to-speech synthesis.

### Core Functionality
- **Automatic Video Dubbing**: Converts videos from source language to target language while preserving timing and speaker characteristics
- **Multi-language Support**: Supports dozens of source and target languages depending on the selected engines
- **Voice Preservation**: Attempts to maintain speaker gender and characteristics in the dubbed output
- **Subtitle Generation**: Can generate subtitles in both source and target languages
- **Post-editing Support**: Allows manual adjustment of generated content through JSON metadata files

## Technologies and Frameworks

### Programming Language
- **Python 3.10+**: Core implementation language with modern Python features

### Core Machine Learning Libraries
- **PyTorch (≥2.0.0, <2.5)**: Deep learning framework for model execution
- **Transformers (4.40-4.45.2)**: Hugging Face library for pre-trained models
- **PyAnnote Audio (3.3.2)**: Speaker diarization and audio analysis
- **Faster-Whisper (1.1.1)**: Optimized speech-to-text implementation
- **CTranslate2 (4.1.0-4.4.0)**: Efficient transformer model inference

### Audio/Video Processing
- **Demucs (4.0.1)**: AI-powered source separation for isolating vocals
- **MoviePy (2.2.1)**: Video processing and manipulation
- **FFmpeg**: External dependency for audio/video format conversion
- **PyDub**: Audio segment manipulation (embedded in codebase)

### Text-to-Speech Engines
- **Coqui TTS**: Open-source neural text-to-speech (optional dependency)
- **Microsoft Edge TTS (6.1.12)**: Cloud-based TTS service
- **Meta MMS**: Multilingual speech synthesis
- **OpenAI TTS**: Commercial TTS API (optional dependency)
- **Custom CLI/API**: Support for external TTS systems

### Translation Engines
- **Meta NLLB-200**: Neural machine translation for 200+ languages
- **Apertium**: Rule-based translation system via API
- **Extensible**: Framework supports additional translation engines

### Supporting Libraries
- **NumPy (≥1.17.3)**: Numerical computing
- **PSUtil (6.0.0)**: System and process monitoring
- **SpaCy (3.7.6)**: Natural language processing with Japanese support
- **ISO639-lang (2.3.0)**: Language code handling

## System Architecture

### Pipeline-Based Design
The system follows a sequential pipeline architecture with seven distinct processing stages:

1. **Preprocessing**: Video/audio separation and vocal isolation
2. **Speech-to-Text**: Audio transcription and speaker diarization
3. **Translation**: Text translation between languages
4. **TTS Configuration**: Voice assignment and speech synthesis setup
5. **Text-to-Speech**: Audio generation with timing synchronization
6. **Postprocessing**: Audio/video merging and final output generation
7. **Cleanup**: Optional removal of intermediate files

### Modular Component System
- **Abstract Base Classes**: Common interfaces for STT, TTS, and Translation components
- **Strategy Pattern**: Multiple implementations for each processing type
- **Plugin Architecture**: Easy addition of new engines and services
- **Dependency Injection**: Configurable component selection at runtime

## Key Features

### Language Support
- **Source Languages**: 80+ languages supported by Whisper models
- **Target Languages**: Varies by TTS engine (Coqui supports 100+ languages)
- **Automatic Detection**: Can automatically detect source language from audio
- **Regional Variants**: Support for language-specific regional voices

### Voice and Speaker Handling
- **Gender Detection**: AI-powered voice gender classification
- **Speaker Diarization**: Automatic identification of multiple speakers
- **Voice Assignment**: Intelligent matching of synthetic voices to original speakers
- **Speed Adjustment**: Automatic timing synchronization for natural dubbing

### Output Options
- **Video Dubbing**: Complete dubbed video with synchronized audio
- **Audio-only**: Dubbed audio track without video
- **Subtitles**: SRT subtitle files in source and/or target languages
- **Metadata**: JSON files containing all processing information for post-editing

### Performance and Scalability
- **Device Flexibility**: CPU and GPU support with automatic optimization
- **Memory Monitoring**: Built-in memory usage tracking and reporting
- **Parallel Processing**: Multi-threaded execution where supported
- **Incremental Updates**: Ability to modify and regenerate specific parts

## Project Status and Limitations

### Current Status
- **Experimental**: Explicitly marked as experimental software
- **Active Development**: Regular updates and improvements
- **Community Driven**: Open-source with contributions welcome
- **Production Use**: Limited production deployment (softcatala.org/doblatge/)

### Known Limitations
- **Quality Dependency**: Output quality depends on each pipeline stage
- **Resource Intensive**: Requires significant computational resources
- **Format Support**: Currently limited to MP4 video input
- **Error Propagation**: Errors in early stages affect final output quality
- **Language Combinations**: Not all language pairs are supported by all engines

### Future Roadmap
- **Voice Control**: Better control over voice selection and characteristics
- **Performance Optimization**: Reduced resource usage for long videos
- **Format Support**: Additional input video formats
- **Quality Improvements**: Enhanced accuracy across all processing stages

## Installation and Dependencies

### Core Installation
```bash
pip install open-dubbing
```

### Optional Components
```bash
# For Coqui TTS support
pip install open-dubbing[coqui]

# For OpenAI TTS support  
pip install open-dubbing[openai]
```

### System Dependencies
- **FFmpeg**: Required for audio/video processing
- **espeak-ng**: Required for Coqui TTS (Linux/macOS)
- **HuggingFace Token**: Required for PyAnnote model access

## Use Cases

### Primary Applications
- **Content Localization**: Dubbing videos for international audiences
- **Educational Content**: Making educational materials accessible in multiple languages
- **Entertainment**: Creating multilingual versions of video content
- **Accessibility**: Providing audio in preferred languages for diverse audiences

### Development and Research
- **ML Research**: Studying speech-to-speech translation pipelines
- **Component Testing**: Evaluating different STT, TTS, and translation engines
- **Workflow Automation**: Integrating dubbing into content production pipelines
- **Quality Assessment**: Analyzing automated dubbing quality and limitations
