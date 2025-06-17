# Flow Diagrams

This document provides visual representations of the major flows and processes in the open-dubbing system using Mermaid diagrams.

## 1. High-Level System Flow

This diagram shows the complete dubbing pipeline from input to output:

```mermaid
flowchart TD
    A[Input Video File] --> B[Initialization & Validation]
    B --> C[Video/Audio Separation]
    C --> D[Vocal Separation with Demucs]
    D --> E[Speaker Diarization with PyAnnote]
    E --> F[Audio Segmentation]
    F --> G[Speech-to-Text Transcription]
    G --> H[Gender Detection]
    H --> I[Text Translation]
    I --> J[Voice Assignment]
    J --> K[Text-to-Speech Synthesis]
    K --> L[Audio Timeline Assembly]
    L --> M[Background/Vocal Mixing]
    M --> N[Video/Audio Combination]
    N --> O[Subtitle Generation]
    O --> P[Final Output Files]
    
    style A fill:#e1f5fe
    style P fill:#e8f5e8
    style B fill:#fff3e0
    style I fill:#f3e5f5
```

**Purpose:** Provides a bird's-eye view of the entire dubbing process, showing how input video transforms through various stages to produce the final dubbed output.

## 2. Component Interaction Diagram

This diagram illustrates how the major components interact with each other:

```mermaid
graph TB
    subgraph "Application Layer"
        CLI[Command Line Interface]
        MAIN[Main Entry Point]
    end
    
    subgraph "Orchestration Layer"
        DUBBER[Dubber Orchestrator]
    end
    
    subgraph "Processing Components"
        STT[Speech-to-Text]
        TRANS[Translation Engine]
        TTS[Text-to-Speech]
        AUDIO[Audio Processing]
        VIDEO[Video Processing]
    end
    
    subgraph "Utility Components"
        FFMPEG[FFmpeg Wrapper]
        GENDER[Gender Classifier]
        DEMUCS[Demucs Integration]
        SUBS[Subtitle Generator]
    end
    
    subgraph "External Dependencies"
        PYANNOTE[PyAnnote Models]
        WHISPER[Whisper Models]
        NLLB[NLLB Models]
        COQUI[Coqui TTS]
    end
    
    CLI --> MAIN
    MAIN --> DUBBER
    DUBBER --> STT
    DUBBER --> TRANS
    DUBBER --> TTS
    DUBBER --> AUDIO
    DUBBER --> VIDEO
    
    AUDIO --> FFMPEG
    AUDIO --> PYANNOTE
    AUDIO --> DEMUCS
    STT --> WHISPER
    STT --> GENDER
    TRANS --> NLLB
    TTS --> COQUI
    VIDEO --> FFMPEG
    DUBBER --> SUBS
    
    style DUBBER fill:#ffeb3b
    style CLI fill:#e3f2fd
    style MAIN fill:#e3f2fd
```

**Purpose:** Shows the dependency relationships and communication patterns between different system components.

## 3. Engine Selection Decision Tree

This diagram shows how the system selects appropriate engines based on configuration:

```mermaid
flowchart TD
    START[System Initialization] --> PLATFORM{Platform Check}
    
    PLATFORM -->|macOS| STT_TRANS[Whisper Transformers]
    PLATFORM -->|Linux/Windows| STT_FASTER[Faster-Whisper]
    
    STT_TRANS --> TRANS_SELECT{Translation Engine}
    STT_FASTER --> TRANS_SELECT
    
    TRANS_SELECT -->|Default| NLLB[NLLB Translation]
    TRANS_SELECT -->|API Mode| APERTIUM[Apertium Translation]
    
    NLLB --> TTS_SELECT{TTS Engine Selection}
    APERTIUM --> TTS_SELECT
    
    TTS_SELECT -->|Default| MMS[MMS TTS]
    TTS_SELECT -->|High Quality| EDGE[Edge TTS]
    TTS_SELECT -->|Local Processing| COQUI[Coqui TTS]
    TTS_SELECT -->|Commercial| OPENAI[OpenAI TTS]
    TTS_SELECT -->|Custom| CLI_API[CLI/API TTS]
    
    MMS --> VALIDATION[Component Validation]
    EDGE --> VALIDATION
    COQUI --> COQUI_CHECK{espeak-ng Available?}
    OPENAI --> API_CHECK{API Key Available?}
    CLI_API --> CONFIG_CHECK{Config File Available?}
    
    COQUI_CHECK -->|Yes| VALIDATION
    COQUI_CHECK -->|No| ERROR1[Error: Missing espeak-ng]
    API_CHECK -->|Yes| VALIDATION
    API_CHECK -->|No| ERROR2[Error: Missing API Key]
    CONFIG_CHECK -->|Yes| VALIDATION
    CONFIG_CHECK -->|No| ERROR3[Error: Missing Config]
    
    VALIDATION --> READY[System Ready]
    
    style START fill:#e1f5fe
    style READY fill:#e8f5e8
    style ERROR1 fill:#ffebee
    style ERROR2 fill:#ffebee
    style ERROR3 fill:#ffebee
```

**Purpose:** Illustrates the decision-making process for selecting appropriate processing engines based on platform, availability, and configuration.

## 4. Data Flow Through Pipeline

This diagram shows how the utterance metadata evolves through each processing stage:

```mermaid
flowchart LR
    subgraph "Stage 1: Preprocessing"
        META1["{start, end, speaker_id, path}"]
    end
    
    subgraph "Stage 2: Speech-to-Text"
        META2["{..., text, gender}"]
    end
    
    subgraph "Stage 3: Translation"
        META3["{..., translated_text}"]
    end
    
    subgraph "Stage 4: TTS Config"
        META4["{..., assigned_voice, speed}"]
    end
    
    subgraph "Stage 5: TTS Generation"
        META5["{..., dubbed_path, hash}"]
    end
    
    subgraph "Stage 6: Postprocessing"
        FINAL[Final Output Files]
    end
    
    META1 --> META2
    META2 --> META3
    META3 --> META4
    META4 --> META5
    META5 --> FINAL
    
    style META1 fill:#e3f2fd
    style META2 fill:#f1f8e9
    style META3 fill:#fce4ec
    style META4 fill:#fff8e1
    style META5 fill:#f3e5f5
    style FINAL fill:#e8f5e8
```

**Purpose:** Demonstrates how the central metadata structure grows and evolves as it passes through each processing stage.

## 5. Audio Processing Workflow

This diagram details the audio processing pipeline:

```mermaid
flowchart TD
    INPUT[Input Video] --> SPLIT[Video/Audio Separation]
    SPLIT --> ORIGINAL[Original Audio Track]
    SPLIT --> VIDEO_ONLY[Video Without Audio]
    
    ORIGINAL --> DEMUCS[Demucs Source Separation]
    DEMUCS --> VOCALS[Isolated Vocals]
    DEMUCS --> BACKGROUND[Background Audio]
    
    VOCALS --> PYANNOTE[PyAnnote Speaker Diarization]
    PYANNOTE --> TIMESTAMPS[Speaker Timestamps]
    
    TIMESTAMPS --> SEGMENT[Audio Segmentation]
    ORIGINAL --> SEGMENT
    SEGMENT --> CHUNKS[Individual Audio Chunks]
    
    CHUNKS --> STT[Speech-to-Text Processing]
    STT --> TRANSCRIPTS[Text Transcriptions]
    
    TRANSCRIPTS --> TRANSLATION[Translation Processing]
    TRANSLATION --> TRANSLATED[Translated Text]
    
    TRANSLATED --> TTS[Text-to-Speech Synthesis]
    TTS --> DUBBED_CHUNKS[Dubbed Audio Chunks]
    
    DUBBED_CHUNKS --> ASSEMBLY[Timeline Assembly]
    ASSEMBLY --> DUBBED_VOCALS[Complete Dubbed Vocals]
    
    DUBBED_VOCALS --> MIXING[Audio Mixing]
    BACKGROUND --> MIXING
    MIXING --> FINAL_AUDIO[Final Dubbed Audio]
    
    FINAL_AUDIO --> COMBINE[Video/Audio Combination]
    VIDEO_ONLY --> COMBINE
    COMBINE --> OUTPUT[Final Dubbed Video]
    
    style INPUT fill:#e1f5fe
    style OUTPUT fill:#e8f5e8
    style DEMUCS fill:#fff3e0
    style PYANNOTE fill:#f3e5f5
    style TTS fill:#e8eaf6
```

**Purpose:** Shows the detailed audio processing workflow, including source separation, diarization, and final mixing.

## 6. Error Handling and Recovery Flow

This diagram illustrates the error handling mechanisms:

```mermaid
flowchart TD
    START[Process Start] --> VALIDATE[Input Validation]
    VALIDATE -->|Valid| PROCESS[Normal Processing]
    VALIDATE -->|Invalid| ERROR_INPUT[Input Error]
    
    PROCESS --> STAGE_CHECK{Stage Success?}
    STAGE_CHECK -->|Success| NEXT_STAGE[Next Stage]
    STAGE_CHECK -->|Failure| ERROR_HANDLER[Error Handler]
    
    ERROR_HANDLER --> ERROR_TYPE{Error Type}
    ERROR_TYPE -->|Recoverable| RETRY[Retry Operation]
    ERROR_TYPE -->|Fatal| CLEANUP[Cleanup Resources]
    ERROR_TYPE -->|Missing Dependency| DEP_ERROR[Dependency Error]
    
    RETRY --> RETRY_COUNT{Retry Limit?}
    RETRY_COUNT -->|Within Limit| PROCESS
    RETRY_COUNT -->|Exceeded| CLEANUP
    
    CLEANUP --> LOG_ERROR[Log Error Details]
    DEP_ERROR --> LOG_ERROR
    ERROR_INPUT --> LOG_ERROR
    
    LOG_ERROR --> EXIT_CODE[Set Exit Code]
    EXIT_CODE --> TERMINATE[Terminate Process]
    
    NEXT_STAGE --> COMPLETE{All Stages Done?}
    COMPLETE -->|No| PROCESS
    COMPLETE -->|Yes| SUCCESS[Successful Completion]
    
    style START fill:#e1f5fe
    style SUCCESS fill:#e8f5e8
    style ERROR_INPUT fill:#ffebee
    style DEP_ERROR fill:#ffebee
    style CLEANUP fill:#fff3e0
    style TERMINATE fill:#ffebee
```

**Purpose:** Demonstrates the comprehensive error handling strategy, including validation, recovery attempts, and graceful degradation.

## 7. Update Mode Workflow

This diagram shows the post-editing update process:

```mermaid
flowchart TD
    UPDATE_START[Update Mode Start] --> LOAD_META[Load Existing Metadata]
    LOAD_META --> VALIDATE_FILES[Validate Required Files]
    
    VALIDATE_FILES -->|Files Missing| UPDATE_ERROR[Update Error]
    VALIDATE_FILES -->|Files Present| COMPARE[Compare Metadata]
    
    COMPARE --> DETECT_CHANGES[Detect Modified Utterances]
    DETECT_CHANGES --> CHANGES_FOUND{Changes Found?}
    
    CHANGES_FOUND -->|No Changes| NO_UPDATE[No Update Needed]
    CHANGES_FOUND -->|Changes Found| PROCESS_CHANGES[Process Modified Utterances]
    
    PROCESS_CHANGES --> VOICE_ASSIGN[Reassign Voices if Needed]
    VOICE_ASSIGN --> TTS_REGEN[Regenerate TTS for Changes]
    TTS_REGEN --> UPDATE_TIMELINE[Update Audio Timeline]
    UPDATE_TIMELINE --> REMIX[Remix Audio]
    REMIX --> RECOMBINE[Recombine with Video]
    RECOMBINE --> SAVE_META[Save Updated Metadata]
    SAVE_META --> UPDATE_COMPLETE[Update Complete]
    
    NO_UPDATE --> UPDATE_COMPLETE
    UPDATE_ERROR --> UPDATE_FAIL[Update Failed]
    
    style UPDATE_START fill:#e1f5fe
    style UPDATE_COMPLETE fill:#e8f5e8
    style UPDATE_ERROR fill:#ffebee
    style UPDATE_FAIL fill:#ffebee
    style PROCESS_CHANGES fill:#fff3e0
```

**Purpose:** Illustrates the efficient update workflow that allows post-editing of dubbing results without full reprocessing.

## 8. Voice Assignment Logic

This diagram shows how voices are assigned to speakers:

```mermaid
flowchart TD
    A[Detected Speakers] --> B[Gender Analysis]
    B --> C[Speaker Profiles with Gender]
    
    C --> D[Available Voice Database]
    D --> E[Filter by Target Language]
    E --> F[Filter by Region Optional]
    
    F --> G[Match Voices by Gender]
    G --> H[Available Voice Pool]
    
    H --> I{Assignment Strategy}
    I -->|Round Robin| J[Distribute Evenly]
    I -->|Quality Based| K[Rank by Quality]
    I -->|Random| L[Random Selection]
    
    J --> M[Assign Voices to Speakers]
    K --> M
    L --> M
    
    M --> N[Ensure Speaker Consistency]
    N --> O[Final Voice Mapping]
    
    style A fill:#e1f5fe
    style O fill:#e8f5e8
    style B fill:#f3e5f5
    style D fill:#fff3e0
```

**Purpose:** Details the sophisticated voice assignment algorithm that matches synthetic voices to original speakers based on gender and other characteristics.

## 9. Performance Monitoring Flow

This diagram shows the performance monitoring and optimization workflow:

```mermaid
flowchart TD
    STAGE_START[Stage Start] --> START_TIMER[Start Timer]
    START_TIMER --> MEMORY_BASELINE[Record Memory Baseline]
    
    MEMORY_BASELINE --> PROCESS_STAGE[Execute Stage Processing]
    PROCESS_STAGE --> MONITOR[Monitor Resources]
    
    MONITOR --> MEMORY_CHECK{Memory Usage OK?}
    MEMORY_CHECK -->|High Usage| MEMORY_WARNING[Log Memory Warning]
    MEMORY_CHECK -->|Normal| CONTINUE[Continue Processing]
    
    MEMORY_WARNING --> CONTINUE
    CONTINUE --> STAGE_COMPLETE[Stage Complete]
    
    STAGE_COMPLETE --> END_TIMER[Stop Timer]
    END_TIMER --> CALC_DURATION[Calculate Duration]
    CALC_DURATION --> MEMORY_PEAK[Record Peak Memory]
    
    MEMORY_PEAK --> LOG_METRICS[Log Performance Metrics]
    LOG_METRICS --> OPTIMIZATION_CHECK{Optimization Needed?}
    
    OPTIMIZATION_CHECK -->|Yes| SUGGEST_OPTIMIZATION[Suggest Optimizations]
    OPTIMIZATION_CHECK -->|No| NEXT_STAGE[Proceed to Next Stage]
    
    SUGGEST_OPTIMIZATION --> NEXT_STAGE
    
    style STAGE_START fill:#e1f5fe
    style NEXT_STAGE fill:#e8f5e8
    style MEMORY_WARNING fill:#fff3e0
    style SUGGEST_OPTIMIZATION fill:#f3e5f5
```

**Purpose:** Shows how the system continuously monitors performance and provides optimization recommendations.

## 10. File Output Structure

This diagram illustrates the complete file output organization:

```mermaid
graph TD
    OUTPUT[Output Directory] --> FINAL_FILES[Final Output Files]
    OUTPUT --> METADATA[Metadata Files]
    OUTPUT --> INTERMEDIATE[Intermediate Files]
    OUTPUT --> SUBTITLES[Subtitle Files]
    
    FINAL_FILES --> DUBBED_VIDEO[dubbed_video_lang.mp4]
    FINAL_FILES --> DUBBED_AUDIO[dubbed_audio_lang.mp3]
    
    METADATA --> UTTERANCE_META[utterance_metadata_lang.json]
    METADATA --> PREPROCESSING[preprocessing_artifacts.json]
    
    INTERMEDIATE --> VIDEO_ONLY[filename_video.mp4]
    INTERMEDIATE --> AUDIO_ONLY[filename_audio.wav]
    INTERMEDIATE --> VOCALS[vocals.wav]
    INTERMEDIATE --> BACKGROUND[no_vocals.wav]
    INTERMEDIATE --> CHUNKS[chunk_*.mp3]
    INTERMEDIATE --> DUBBED_CHUNKS[dubbed_chunk_*.mp3]
    
    SUBTITLES --> SOURCE_SUBS[source_language.srt]
    SUBTITLES --> TARGET_SUBS[target_language.srt]
    
    style OUTPUT fill:#e1f5fe
    style FINAL_FILES fill:#e8f5e8
    style METADATA fill:#fff3e0
    style INTERMEDIATE fill:#f3e5f5
    style SUBTITLES fill:#e8eaf6
```

**Purpose:** Shows the comprehensive file organization structure, including final outputs, metadata for post-editing, intermediate processing files, and optional subtitle files.

## Summary

These flow diagrams provide visual representations of the key processes and data flows in the open-dubbing system:

1. **High-Level System Flow**: Complete pipeline overview
2. **Component Interaction**: System architecture and dependencies
3. **Engine Selection**: Decision-making for component selection
4. **Data Flow**: Metadata evolution through processing stages
5. **Audio Processing**: Detailed audio manipulation workflow
6. **Error Handling**: Comprehensive error management strategy
7. **Update Mode**: Post-editing and incremental updates
8. **Voice Assignment**: Speaker-to-voice matching algorithm
9. **Performance Monitoring**: Resource tracking and optimization
10. **File Output**: Complete output file organization

Each diagram serves a specific purpose in understanding different aspects of the system, from high-level architecture to detailed processing workflows. Together, they provide a comprehensive visual guide to the open-dubbing system's operation and design.
