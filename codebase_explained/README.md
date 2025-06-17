# Open-Dubbing Codebase Documentation

Welcome to the comprehensive documentation for the **open-dubbing** project - an experimental AI-powered video dubbing system that automatically translates and synchronizes audio dialogue into different languages.

## 📋 Table of Contents

### Core Documentation Files

1. **[Project Overview](./overview.md)** 📖
   - Project purpose and main functionality
   - Technologies, frameworks, and programming languages used
   - Key features and capabilities
   - Installation requirements and system dependencies

2. **[Component Breakdown](./components.md)** 🔧
   - Detailed analysis of all system components
   - Core processing components (STT, TTS, Translation)
   - Supporting utilities and infrastructure
   - Component interactions and dependencies

3. **[Entry Point and Initialization](./entry_point.md)** 🚀
   - Application startup and initialization sequence
   - Command-line interface and parameter parsing
   - System validation and dependency checks
   - Component factory initialization

4. **[Execution Flow](./execution_flow.md)** ⚡
   - Complete step-by-step execution walkthrough
   - Seven-stage pipeline detailed breakdown
   - Data flow and metadata evolution
   - Error handling and recovery mechanisms

5. **[Design Patterns and Architecture](./architecture.md)** 🏗️
   - Architectural principles and design patterns
   - Strategy, Factory, and Template Method patterns
   - Pipeline and layered architecture
   - Scalability and extensibility considerations

6. **[Flow Diagrams](./flow_diagrams.md)** 📊
   - Visual representations using Mermaid diagrams
   - System flow, component interactions, and decision trees
   - Audio processing workflow and error handling
   - Performance monitoring and file organization

## 🎯 Quick Navigation

### For New Developers
Start with these files to understand the project:
1. [Project Overview](./overview.md) - Get the big picture
2. [Flow Diagrams](./flow_diagrams.md) - Visual system understanding
3. [Component Breakdown](./components.md) - Detailed component analysis

### For System Architects
Focus on these architectural aspects:
1. [Design Patterns and Architecture](./architecture.md) - System design principles
2. [Component Breakdown](./components.md) - Component relationships
3. [Flow Diagrams](./flow_diagrams.md) - System interaction patterns

### For Implementation Details
Dive into the technical specifics:
1. [Entry Point and Initialization](./entry_point.md) - How the system starts
2. [Execution Flow](./execution_flow.md) - How processing works
3. [Component Breakdown](./components.md) - Implementation details

## 🎬 What is Open-Dubbing?

Open-dubbing is an experimental AI-powered video dubbing system that combines multiple machine learning models to automatically:

- **Extract and separate** audio from video files
- **Transcribe speech** using Whisper models
- **Translate text** between 200+ language pairs
- **Generate synthetic speech** with multiple TTS engines
- **Synchronize timing** to match original video
- **Produce dubbed videos** with preserved background audio

### Key Technologies

- **Python 3.10+** with modern ML libraries
- **PyTorch** for deep learning model execution
- **Whisper** for speech-to-text transcription
- **NLLB-200** for neural machine translation
- **Multiple TTS engines** (Coqui, Edge, MMS, OpenAI)
- **PyAnnote** for speaker diarization
- **Demucs** for audio source separation

## 🏗️ System Architecture Overview

The system follows a **pipeline architecture** with seven sequential stages:

```
Input Video → Preprocessing → STT → Translation → TTS Config → TTS → Postprocessing → Output
```

### Core Design Principles

1. **Modular Design**: Each component has a single, well-defined responsibility
2. **Strategy Pattern**: Multiple implementations for STT, TTS, and translation
3. **Extensibility**: Easy to add new engines and capabilities
4. **Error Handling**: Comprehensive error detection and recovery
5. **Performance Monitoring**: Built-in resource tracking and optimization

## 📁 Project Structure

```
open_dubbing/
├── main.py                    # Application entry point
├── dubbing.py                 # Main orchestrator
├── command_line.py            # CLI interface
├── speech_to_text*.py         # STT implementations
├── text_to_speech*.py         # TTS implementations
├── translation*.py            # Translation engines
├── audio_processing.py        # Audio manipulation
├── video_processing.py        # Video handling
└── utilities/                 # Supporting components
```

## 🔄 Processing Pipeline

### Stage 1: Preprocessing
- Video/audio separation using FFmpeg
- Vocal isolation with Demucs AI
- Speaker diarization with PyAnnote
- Audio segmentation into utterances

### Stage 2: Speech-to-Text
- Audio transcription with Whisper models
- Gender detection for voice assignment
- Speaker information integration
- Metadata cleanup and validation

### Stage 3: Translation
- Text translation using NLLB or Apertium
- Context preservation and batch processing
- Language pair validation

### Stage 4: TTS Configuration
- Voice assignment based on speaker gender
- Regional voice preferences
- Speed and timing configuration

### Stage 5: Text-to-Speech
- Synthetic speech generation
- Timing synchronization
- Audio post-processing

### Stage 6: Postprocessing
- Audio timeline assembly
- Background/vocal mixing
- Video/audio combination
- Subtitle generation (optional)

## 🎛️ Supported Engines

### Speech-to-Text
- **Faster-Whisper**: Optimized implementation (default for Linux/Windows)
- **Whisper Transformers**: Standard implementation (default for macOS)

### Translation
- **NLLB-200**: Neural translation for 200+ languages (default)
- **Apertium**: Rule-based translation via API

### Text-to-Speech
- **MMS**: Meta's Massively Multilingual Speech (default)
- **Edge TTS**: Microsoft Edge cloud service
- **Coqui TTS**: Open-source neural TTS
- **OpenAI TTS**: Commercial API service
- **CLI/API**: Custom external systems

## 🚀 Getting Started

### Basic Usage
```bash
open-dubbing --input_file video.mp4 --target_language=spa --hugging_face_token=TOKEN
```

### With Specific Engines
```bash
open-dubbing --input_file video.mp4 --target_language=fra --tts=edge --translator=nllb --hugging_face_token=TOKEN
```

### Post-Editing Workflow
```bash
# Initial dubbing
open-dubbing --input_file video.mp4 --target_language=deu --hugging_face_token=TOKEN

# Edit the generated utterance_metadata_deu.json file manually

# Regenerate with changes
open-dubbing --input_file video.mp4 --target_language=deu --hugging_face_token=TOKEN --update
```

## 📊 Key Features

### Language Support
- **80+ source languages** supported by Whisper
- **200+ target languages** depending on TTS engine
- **Automatic language detection** from audio
- **Regional voice variants** for natural dubbing

### Quality Features
- **Speaker diarization** for multi-speaker videos
- **Gender-aware voice assignment** for natural dubbing
- **Timing synchronization** with speed adjustment
- **Background audio preservation** during dubbing

### Workflow Features
- **Post-editing support** through JSON metadata
- **Incremental updates** for modified content
- **Subtitle generation** in source and target languages
- **Comprehensive logging** and progress tracking

## 🔧 Advanced Configuration

### Device Selection
```bash
--device=cuda    # Use GPU acceleration
--device=cpu     # Use CPU processing
--device=mps     # Use Apple Silicon GPU (macOS)
```

### Model Selection
```bash
--whisper_model=large-v3     # High accuracy STT
--nllb_model=nllb-200-3.3B   # Large translation model
```

### Output Options
```bash
--original_subtitles         # Generate source language subtitles
--dubbed_subtitles          # Generate target language subtitles
--clean_intermediate_files  # Remove temporary files
```

## 📈 Performance Considerations

### Resource Requirements
- **Memory**: 4-16GB RAM depending on model sizes
- **Storage**: 2-10GB for models and intermediate files
- **Processing**: GPU recommended for faster inference

### Optimization Tips
- Use GPU acceleration when available
- Choose appropriate model sizes for your hardware
- Enable intermediate file cleanup to save storage
- Monitor memory usage during processing

## 🛠️ Development and Extension

### Adding New TTS Engine
1. Implement the `TextToSpeech` abstract class
2. Add factory case in `_get_selected_tts()`
3. No changes needed to existing pipeline code

### Adding New Translation Service
1. Implement the `Translation` abstract class
2. Add factory case in `_get_selected_translator()`
3. Automatic integration with existing workflow

### Testing and Debugging
- Comprehensive unit tests for all components
- Detailed logging with configurable levels
- Performance monitoring and memory tracking
- Error codes for specific failure modes

## 📚 Additional Resources

### External Documentation
- [Original Project README](../README.md)
- [Technical Documentation](../DOCUMENTATION.md)
- [Changelog](../CHANGELOG.md)

### Community and Support
- [GitHub Repository](https://github.com/Softcatala/open-dubbing)
- [Live Demo](https://www.softcatala.org/doblatge/)
- [Issue Tracker](https://github.com/Softcatala/open-dubbing/issues)

## 🎯 Documentation Goals

This documentation aims to:

1. **Provide comprehensive understanding** of the system architecture
2. **Enable quick onboarding** for new developers
3. **Support system maintenance** and troubleshooting
4. **Facilitate system extension** and customization
5. **Document best practices** and design decisions

## 📝 Documentation Structure

Each documentation file is designed to be:
- **Self-contained** with complete information on its topic
- **Cross-referenced** with links to related sections
- **Visually enhanced** with diagrams and code examples
- **Practically focused** with real-world usage scenarios

---

**Note**: This is an experimental project under active development. The documentation reflects the current state of the system and will be updated as the project evolves.

For the most up-to-date information, please refer to the [main project repository](https://github.com/Softcatala/open-dubbing).
