# High-Level Design: AI-Powered Video Translation Service MVP

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture Components](#architecture-components)
4. [Technology Stack](#technology-stack)
5. [Video Processing Pipeline](#video-processing-pipeline)
6. [Design Patterns & Extensibility](#design-patterns--extensibility)
7. [API Design](#api-design)
8. [Database Schema](#database-schema)
9. [AWS Deployment Architecture](#aws-deployment-architecture)
10. [Performance & Scalability](#performance--scalability)
11. [Security Considerations](#security-considerations)
12. [Monitoring & Observability](#monitoring--observability)
13. [Future Extension Points](#future-extension-points)

---

## Executive Summary

### Objective
Design and implement a **single deployable service** that enables users to upload videos (up to 200MB), processes them using AI to generate translated versions, and provides downloadable MP4 files optimized for global users.

### Key MVP Features
- ✅ Video upload with progress tracking (up to 200MB)
- ✅ AI-powered video dubbing pipeline (11 stages)
- ✅ Real-time processing status updates
- ✅ Video preview before download
- ✅ Multi-language support
- ✅ Global CDN distribution
- ✅ Basic web frontend

### Architecture Approach
**Monolithic service** with modular components following clean architecture principles, deployed as a single Docker container on AWS ECS Fargate for MVP simplicity while maintaining extensibility.

---

## System Overview

### High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Frontend]
        API_CLIENT[API Clients]
    end
    
    subgraph "CDN & Load Balancing"
        CF[CloudFront CDN]
        ALB[Application Load Balancer]
    end
    
    subgraph "Application Layer (Single Service)"
        FASTAPI[FastAPI Application]
        
        subgraph "API Handlers"
            UPLOAD[Upload Handler]
            STATUS[Status Handler]
            DOWNLOAD[Download Handler]
            PREVIEW[Preview Handler]
        end
        
        subgraph "Processing Engine"
            ORCHESTRATOR[Pipeline Orchestrator]
            QUEUE[Job Queue Manager]
            PROGRESS[Progress Tracker]
        end
        
        subgraph "AI Services (Strategy Pattern)"
            STT[Whisper STT Service]
            TRANS[NLLB Translation Service]
            TTS[MMS TTS Service]
            DIARIZE[PyAnnote Diarization]
        end
    end
    
    subgraph "Storage Layer"
        S3[AWS S3 Buckets]
        RDS[PostgreSQL RDS]
        REDIS[Redis ElastiCache]
    end
    
    subgraph "External Tools"
        FFMPEG[FFmpeg Engine]
    end
    
    WEB --> CF
    API_CLIENT --> CF
    CF --> ALB
    ALB --> FASTAPI
    
    FASTAPI --> UPLOAD
    FASTAPI --> STATUS
    FASTAPI --> DOWNLOAD
    FASTAPI --> PREVIEW
    
    UPLOAD --> ORCHESTRATOR
    ORCHESTRATOR --> QUEUE
    ORCHESTRATOR --> STT
    ORCHESTRATOR --> TRANS
    ORCHESTRATOR --> TTS
    ORCHESTRATOR --> DIARIZE
    ORCHESTRATOR --> FFMPEG
    
    FASTAPI --> S3
    FASTAPI --> RDS
    FASTAPI --> REDIS
    
    QUEUE --> REDIS
    PROGRESS --> REDIS
```

### Core Principles
1. **Single Responsibility**: Each component has a clear, focused purpose
2. **Dependency Inversion**: High-level modules depend on abstractions
3. **Strategy Pattern**: Pluggable AI services for future extensibility
4. **Async Processing**: Non-blocking operations for better performance
5. **Cloud-Native**: Designed for AWS deployment and scaling

---

## Architecture Components

### 1. API Layer Components

#### FastAPI Application
```python
# Main application structure
app/
├── main.py                 # FastAPI app initialization
├── api/
│   ├── routes/
│   │   ├── upload.py       # Video upload endpoints
│   │   ├── jobs.py         # Job management endpoints
│   │   ├── download.py     # Download endpoints
│   │   └── preview.py      # Preview endpoints
│   └── middleware/
│       ├── cors.py         # CORS handling
│       ├── auth.py         # Authentication
│       └── rate_limit.py   # Rate limiting
├── services/
│   ├── ai_services/        # AI service implementations
│   ├── processing/         # Video processing logic
│   └── storage/            # Storage abstractions
└── models/                 # Data models and schemas
```

#### Key API Endpoints
```python
# Upload API
POST /api/v1/upload
- Multipart file upload with metadata
- Returns job_id for tracking

# Job Status API
GET /api/v1/jobs/{job_id}/status
- Real-time processing status
- Progress percentage and current stage

# Download API
GET /api/v1/jobs/{job_id}/download
- Serves processed video file
- CDN-optimized delivery

# Preview API
GET /api/v1/jobs/{job_id}/preview
- Generates preview clips
- Supports time-range selection

# WebSocket for Real-time Updates
WS /api/v1/jobs/{job_id}/progress
- Live progress updates
- Error notifications
```

### 2. Processing Engine Components

#### Pipeline Orchestrator
```python
class VideoDubbingOrchestrator:
    """
    Coordinates the 11-stage video dubbing pipeline
    """
    def __init__(self):
        self.ai_factory = AIServiceFactory()
        self.progress_tracker = ProgressTracker()
        self.ffmpeg_service = FFmpegService()
    
    async def process_video(self, job_id: str, video_path: str, 
                          source_lang: str, target_lang: str):
        """
        Execute complete dubbing pipeline with progress tracking
        """
        stages = [
            ("validation", self._validate_input, 5),
            ("separation", self._separate_audio_video, 10),
            ("diarization", self._diarize_speakers, 15),
            ("segmentation", self._segment_audio, 20),
            ("transcription", self._transcribe_audio, 35),
            ("gender_detection", self._detect_gender, 40),
            ("translation", self._translate_text, 50),
            ("voice_assignment", self._assign_voices, 60),
            ("synthesis", self._synthesize_speech, 75),
            ("assembly", self._assemble_audio, 85),
            ("combination", self._combine_final, 95)
        ]
        
        for stage_name, stage_func, progress in stages:
            try:
                await self.progress_tracker.update(job_id, stage_name, progress)
                result = await stage_func(job_id, **kwargs)
                await self._save_stage_result(job_id, stage_name, result)
            except Exception as e:
                await self._handle_stage_error(job_id, stage_name, e)
                raise
        
        await self.progress_tracker.complete(job_id)
```

### 3. AI Services Layer (Strategy Pattern)

#### Abstract Service Interfaces
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class SpeechToTextService(ABC):
    """Abstract interface for STT services"""
    
    @abstractmethod
    async def transcribe_segments(self, audio_segments: List[AudioSegment], 
                                source_language: str) -> List[Transcript]:
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        pass

class TranslationService(ABC):
    """Abstract interface for translation services"""
    
    @abstractmethod
    async def translate_batch(self, texts: List[str], 
                            source_lang: str, target_lang: str) -> List[str]:
        pass
    
    @abstractmethod
    def get_supported_language_pairs(self) -> List[Tuple[str, str]]:
        pass

class TextToSpeechService(ABC):
    """Abstract interface for TTS services"""
    
    @abstractmethod
    async def synthesize_speech(self, text: str, voice_config: VoiceConfig) -> AudioSegment:
        pass
    
    @abstractmethod
    def get_available_voices(self, language: str) -> List[Voice]:
        pass
```

#### Concrete Implementations
```python
class WhisperSTTService(SpeechToTextService):
    """Whisper Transformers implementation"""
    
    def __init__(self, model_name: str = "openai/whisper-large-v3"):
        self.model = WhisperForConditionalGeneration.from_pretrained(model_name)
        self.processor = WhisperProcessor.from_pretrained(model_name)
    
    async def transcribe_segments(self, audio_segments: List[AudioSegment], 
                                source_language: str) -> List[Transcript]:
        transcripts = []
        for segment in audio_segments:
            # Process audio segment
            inputs = self.processor(segment.audio_data, 
                                  sampling_rate=16000, 
                                  return_tensors="pt")
            
            # Generate transcription
            with torch.no_grad():
                predicted_ids = self.model.generate(inputs["input_features"])
                transcription = self.processor.batch_decode(predicted_ids, 
                                                          skip_special_tokens=True)[0]
            
            transcripts.append(Transcript(
                text=transcription,
                start_time=segment.start_time,
                end_time=segment.end_time,
                speaker_id=segment.speaker_id
            ))
        
        return transcripts

class NLLBTranslationService(TranslationService):
    """NLLB-200 implementation"""
    
    def __init__(self, model_name: str = "facebook/nllb-200-3.3B"):
        self.model = M2M100ForConditionalGeneration.from_pretrained(model_name)
        self.tokenizer = M2M100Tokenizer.from_pretrained(model_name)
    
    async def translate_batch(self, texts: List[str], 
                            source_lang: str, target_lang: str) -> List[str]:
        # Set source language
        self.tokenizer.src_lang = source_lang
        
        translations = []
        for text in texts:
            # Tokenize and translate
            encoded = self.tokenizer(text, return_tensors="pt")
            generated_tokens = self.model.generate(
                **encoded,
                forced_bos_token_id=self.tokenizer.lang_code_to_id[target_lang],
                max_length=512
            )
            translation = self.tokenizer.batch_decode(generated_tokens, 
                                                    skip_special_tokens=True)[0]
            translations.append(translation)
        
        return translations

class MMSTextToSpeechService(TextToSpeechService):
    """MMS TTS implementation"""
    
    def __init__(self):
        self.model = VitsModel.from_pretrained("facebook/mms-tts-eng")
        self.tokenizer = VitsTokenizer.from_pretrained("facebook/mms-tts-eng")
    
    async def synthesize_speech(self, text: str, voice_config: VoiceConfig) -> AudioSegment:
        # Load language-specific model if needed
        if voice_config.language != "eng":
            model_name = f"facebook/mms-tts-{voice_config.language}"
            self.model = VitsModel.from_pretrained(model_name)
            self.tokenizer = VitsTokenizer.from_pretrained(model_name)
        
        # Tokenize text
        inputs = self.tokenizer(text, return_tensors="pt")
        
        # Generate speech
        with torch.no_grad():
            output = self.model(inputs["input_ids"])
        
        # Convert to audio segment
        audio_data = output.waveform.squeeze().cpu().numpy()
        return AudioSegment(
            audio_data=audio_data,
            sample_rate=self.model.config.sampling_rate,
            duration=len(audio_data) / self.model.config.sampling_rate
        )
```

### 4. Factory Pattern Implementation

```python
class AIServiceFactory:
    """Factory for creating AI service instances"""
    
    @staticmethod
    def create_stt_service(config: Dict[str, Any]) -> SpeechToTextService:
        service_type = config.get("stt_service", "whisper")
        
        if service_type == "whisper":
            model_name = config.get("whisper_model", "openai/whisper-large-v3")
            return WhisperSTTService(model_name)
        else:
            raise ValueError(f"Unsupported STT service: {service_type}")
    
    @staticmethod
    def create_translation_service(config: Dict[str, Any]) -> TranslationService:
        service_type = config.get("translation_service", "nllb")
        
        if service_type == "nllb":
            model_name = config.get("nllb_model", "facebook/nllb-200-3.3B")
            return NLLBTranslationService(model_name)
        else:
            raise ValueError(f"Unsupported translation service: {service_type}")
    
    @staticmethod
    def create_tts_service(config: Dict[str, Any]) -> TextToSpeechService:
        service_type = config.get("tts_service", "mms")
        
        if service_type == "mms":
            return MMSTextToSpeechService()
        else:
            raise ValueError(f"Unsupported TTS service: {service_type}")
```

---

## Technology Stack

### Backend Framework
- **FastAPI (Python 3.10+)**
  - High-performance async framework
  - Built-in OpenAPI documentation
  - Excellent WebSocket support for real-time updates
  - Type hints and automatic validation

### AI/ML Stack
- **Whisper Transformers**: Speech-to-text transcription
  - Model: `openai/whisper-large-v3`
  - Supports 80+ languages
  - High accuracy for diverse audio conditions

- **NLLB-200**: Neural machine translation
  - Model: `facebook/nllb-200-3.3B`
  - Supports 200+ languages
  - State-of-the-art translation quality

- **MMS (Meta)**: Massively multilingual speech synthesis
  - Model: `facebook/mms-tts-*`
  - Supports 1000+ languages
  - Natural-sounding voice synthesis

- **PyAnnote Audio**: Speaker diarization
  - Model: `pyannote/speaker-diarization`
  - Accurate speaker identification
  - Voice activity detection

### Infrastructure & Storage
- **AWS S3**: Object storage for videos
  - Input videos bucket
  - Output videos bucket
  - Temporary processing files

- **PostgreSQL (RDS)**: Relational database
  - Job metadata and status
  - User information
  - Processing history

- **Redis (ElastiCache)**: Caching and job queue
  - Session management
  - Job queue for async processing
  - Real-time progress tracking

### Media Processing
- **FFmpeg**: Video/audio processing
  - Audio extraction from video
  - Video/audio recombination
  - Format conversion and optimization

### Deployment
- **Docker**: Containerization
- **AWS ECS Fargate**: Serverless container deployment
- **Application Load Balancer**: Traffic distribution
- **CloudFront**: Global CDN for fast delivery

---

## Video Processing Pipeline

### Pipeline Overview (11 Stages)

Following the assignment's specified video dubbing process:

```mermaid
flowchart TD
    A[Input Video Upload] --> B[Initialization & Validation]
    B --> C[Video/Audio Separation]
    C --> D[Speaker Diarization]
    D --> E[Audio Segmentation]
    E --> F[Speech-to-Text Transcription]
    F --> G[Gender Detection]
    G --> H[Text Translation]
    H --> I[Voice Assignment]
    I --> J[Text-to-Speech Synthesis]
    J --> K[Audio Timeline Assembly]
    K --> L[Video/Audio Combination]
    L --> M[Final Output & Storage]
    
    style A fill:#e1f5fe
    style M fill:#e8f5e8
    style F fill:#fff3e0
    style H fill:#f3e5f5
    style J fill:#e8eaf6
```

### Detailed Stage Implementation

#### Stage 1: Initialization & Validation (5% Progress)
```python
async def _validate_input(self, job_id: str, video_path: str) -> ValidationResult:
    """
    Validate uploaded video file
    """
    # File format validation
    supported_formats = ['.mp4', '.avi', '.mov', '.mkv']
    file_ext = Path(video_path).suffix.lower()
    if file_ext not in supported_formats:
        raise ValidationError(f"Unsupported format: {file_ext}")
    
    # File size validation (200MB limit)
    file_size = os.path.getsize(video_path)
    if file_size > 200 * 1024 * 1024:  # 200MB
        raise ValidationError(f"File too large: {file_size / (1024*1024):.1f}MB")
    
    # Video metadata extraction
    probe = ffmpeg.probe(video_path)
    video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    audio_info = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    
    return ValidationResult(
        duration=float(probe['format']['duration']),
        video_codec=video_info['codec_name'],
        audio_codec=audio_info['codec_name'],
        resolution=(video_info['width'], video_info['height']),
        frame_rate=eval(video_info['r_frame_rate'])
    )
```

#### Stage 2: Video/Audio Separation (10% Progress)
```python
async def _separate_audio_video(self, job_id: str, video_path: str) -> SeparationResult:
    """
    Extract audio track from video using FFmpeg
    """
    audio_path = f"/tmp/{job_id}_audio.wav"
    video_only_path = f"/tmp/{job_id}_video_only.mp4"
    
    # Extract audio
    (
        ffmpeg
        .input(video_path)
        .output(audio_path, acodec='pcm_s16le', ac=1, ar='16000')
        .overwrite_output()
        .run(quiet=True)
    )
    
    # Extract video without audio
    (
        ffmpeg
        .input(video_path)
        .output(video_only_path, vcodec='copy')
        .overwrite_output()
        .run(quiet=True)
    )
    
    return SeparationResult(
        audio_path=audio_path,
        video_only_path=video_only_path
    )
```

#### Stage 3: Speaker Diarization (15% Progress)
```python
async def _diarize_speakers(self, job_id: str, audio_path: str) -> DiarizationResult:
    """
    Identify different speakers using PyAnnote
    """
    # Load PyAnnote pipeline
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
    
    # Perform diarization
    diarization = pipeline(audio_path)
    
    # Extract speaker segments
    speaker_segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        speaker_segments.append(SpeakerSegment(
            speaker_id=speaker,
            start_time=turn.start,
            end_time=turn.end,
            duration=turn.end - turn.start
        ))
    
    return DiarizationResult(
        speaker_segments=speaker_segments,
        num_speakers=len(set(seg.speaker_id for seg in speaker_segments))
    )
```

#### Stage 4: Audio Segmentation (20% Progress)
```python
async def _segment_audio(self, job_id: str, audio_path: str, 
                        speaker_segments: List[SpeakerSegment]) -> SegmentationResult:
    """
    Split audio into individual speaker segments
    """
    audio_segments = []
    audio = AudioSegment.from_wav(audio_path)
    
    for i, segment in enumerate(speaker_segments):
        start_ms = int(segment.start_time * 1000)
        end_ms = int(segment.end_time * 1000)
        
        # Extract segment
        segment_audio = audio[start_ms:end_ms]
        
        # Save segment
        segment_path = f"/tmp/{job_id}_segment_{i}.wav"
        segment_audio.export(segment_path, format="wav")
        
        audio_segments.append(AudioSegmentData(
            path=segment_path,
            speaker_id=segment.speaker_id,
            start_time=segment.start_time,
            end_time=segment.end_time,
            duration=segment.duration
        ))
    
    return SegmentationResult(audio_segments=audio_segments)
```

#### Stage 5: Speech-to-Text Transcription (35% Progress)
```python
async def _transcribe_audio(self, job_id: str, audio_segments: List[AudioSegmentData], 
                           source_language: str) -> TranscriptionResult:
    """
    Transcribe audio segments using Whisper
    """
    stt_service = self.ai_factory.create_stt_service({
        "stt_service": "whisper",
        "whisper_model": "openai/whisper-large-v3"
    })
    
    transcripts = await stt_service.transcribe_segments(audio_segments, source_language)
    
    return TranscriptionResult(
        transcripts=transcripts,
        total_segments=len(transcripts),
        source_language=source_language
    )
```

#### Stage 6: Gender Detection (40% Progress)
```python
async def _detect_gender(self, job_id: str, audio_segments: List[AudioSegmentData]) -> GenderResult:
    """
    Detect speaker gender for voice assignment
    """
    gender_classifier = VoiceGenderClassifier()
    
    speaker_genders = {}
    for segment in audio_segments:
        if segment.speaker_id not in speaker_genders:
            # Analyze voice characteristics
            gender = await gender_classifier.predict_gender(segment.path)
            speaker_genders[segment.speaker_id] = gender
    
    return GenderResult(speaker_genders=speaker_genders)
```

#### Stage 7: Text Translation (50% Progress)
```python
async def _translate_text(self, job_id: str, transcripts: List[Transcript], 
                         source_lang: str, target_lang: str) -> TranslationResult:
    """
    Translate transcribed text using NLLB
    """
    translation_service = self.ai_factory.create_translation_service({
        "translation_service": "nllb",
        "nllb_model": "facebook/nllb-200-3.3B"
    })
    
    texts = [transcript.text for transcript in transcripts]
    translations = await translation_service.translate_batch(texts, source_lang, target_lang)
    
    # Combine with original transcript metadata
    translated_transcripts = []
    for transcript, translation in zip(transcripts, translations):
        translated_transcripts.append(TranslatedTranscript(
            original_text=transcript.text,
            translated_text=translation,
            start_time=transcript.start_time,
            end_time=transcript.end_time,
            speaker_id=transcript.speaker_id
        ))
    
    return TranslationResult(
        translated_transcripts=translated_transcripts,
        source_language=source_lang,
        target_language=target_lang
    )
```

#### Stage 8: Voice Assignment (60% Progress)
```python
async def _assign_voices(self, job_id: str, speaker_genders: Dict[str, str], 
                        target_language: str) -> VoiceAssignmentResult:
    """
    Assign target language voices to speakers based on gender
    """
    tts_service = self.ai_factory.create_tts_service({"tts_service": "mms"})
    available_voices = tts_service.get_available_voices(target_language)
    
    # Group voices by gender
    male_voices = [v for v in available_voices if v.gender == "male"]
    female_voices = [v for v in available_voices if v.gender == "female"]
    
    voice_assignments = {}
    male_idx, female_idx = 0, 0
    
    for speaker_id, gender in speaker_genders.items():
        if gender == "male" and male_voices:
            voice_assignments[speaker_id] = male_voices[male_idx % len(male_voices)]
            male_idx += 1
        elif gender == "female" and female_voices:
            voice_assignments[speaker_id] = female_voices[female_idx % len(female_voices)]
            female_idx += 1
        else:
            # Fallback to first available voice
            voice_assignments[speaker_id] = available_voices[0]
    
    return VoiceAssignmentResult(voice_assignments=voice_assignments)
```

#### Stage 9: Text-to-Speech Synthesis (75% Progress)
```python
async def _synthesize_speech(self, job_id: str, translated_transcripts: List[TranslatedTranscript], 
                           voice_assignments: Dict[str, Voice]) -> SynthesisResult:
    """
    Generate synthetic speech using MMS
    """
    tts_service = self.ai_factory.create_tts_service({"tts_service": "mms"})
    
    dubbed_segments = []
    for transcript in translated_transcripts:
        voice = voice_assignments[transcript.speaker_id]
        voice_config = VoiceConfig(
            language=voice.language,
            voice_id=voice.voice_id,
            gender=voice.gender
        )
        
        # Synthesize speech
        audio_segment = await tts_service.synthesize_speech(
            transcript.translated_text, 
            voice_config
        )
        
        # Calculate speed adjustment for timing synchronization
        original_duration = transcript.end_time - transcript.start_time
        synthesized_duration = audio_segment.duration
        speed_factor = synthesized_duration / original_duration
        
        # Adjust speed if necessary
        if speed_factor > 1.2 or speed_factor < 0.8:
            audio_segment = self._adjust_audio_speed(audio_segment, 1/speed_factor)
        
        dubbed_segments.append(DubbedSegment(
            audio_segment=audio_segment,
            start_time=transcript.start_time,
            end_time=transcript.end_time,
            speaker_id=transcript.speaker_id,
            text=transcript.translated_text
        ))
    
    return SynthesisResult(dubbed_segments=dubbed_segments)
```

#### Stage 10: Audio Timeline Assembly (85% Progress)
```python
async def _assemble_audio(self, job_id: str, dubbed_segments: List[DubbedSegment], 
                         total_duration: float) -> AssemblyResult:
    """
    Reconstruct complete audio timeline with dubbed segments
    """
    # Create silent audio track of full duration
    silence = AudioSegment.silent(duration=int(total_duration * 1000))
    
    # Overlay dubbed segments at their original timestamps
    final_audio = silence
    for segment in dubbed_segments:
        start_ms = int(segment.start_time * 1000)
        segment_audio = AudioSegment(
            segment.audio_segment.audio_data.tobytes(),
            frame_rate=segment.audio_segment.sample_rate,
            sample_width=2,
            channels=1
        )
        
        # Overlay at correct position
        final_audio = final_audio.overlay(segment_audio, position=start_ms)
    
    # Export final dubbed audio
    dubbed_audio_path = f"/tmp/{job_id}_dubbed_audio.wav"
    final_audio.export(dubbed_audio_path, format="wav")
    
    return AssemblyResult(dubbed_audio_path=dubbed_audio_path)
```

#### Stage 11: Video/Audio Combination (95% Progress)
```python
async def _combine_final(self, job_id: str, video_only_path: str, 
                        dubbed_audio_path: str) -> CombinationResult:
    """
    Combine dubbed audio with original video
    """
    output_path = f"/tmp/{job_id}_final_output.mp4"
    
    # Combine video and dubbed audio
    (
        ffmpeg
        .input(video_only_path)
        .input(dubbed_audio_path)
        .output(
            output_path,
            vcodec='copy',
            acodec='aac',
            audio_bitrate='128k'
        )
        .overwrite_output()
        .run(quiet=True)
    )
    
    # Upload to S3
    s3_key = f"outputs/{job_id}/dubbed_video.mp4"
    await self.s3_service.upload_file(output_path, s3_key)
    
    return CombinationResult(
        output_path=output_path,
        s3_key=s3_key,
        file_size=os.path.getsize(output_path)
    )
```

---

## Design Patterns & Extensibility

### Strategy Pattern Implementation

The AI services layer uses the Strategy pattern to enable easy swapping of different AI models and services:

```python
# Strategy interface
class AIServiceStrategy(ABC):
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        pass

# Concrete strategies
class WhisperStrategy(AIServiceStrategy):
    async def process(self, audio_data: AudioData) -> TranscriptionResult:
        # Whisper-specific implementation
        pass

class NLLBStrategy(AIServiceStrategy):
    async def process(self, text_data: TextData) -> TranslationResult:
        # NLLB-specific implementation
        pass

# Context class
class AIServiceContext:
    def __init__(self, strategy: AIServiceStrategy):
        self._strategy = strategy
    
    def set_strategy(self, strategy: AIServiceStrategy):
        self._strategy = strategy
    
    async def execute(self, input_data: Any) -> Any:
        return await self._strategy.process(input_data)
```

### Factory Pattern for Service Creation

```python
class ServiceFactory:
    """
    Factory for creating various service instances
    """
    
    @staticmethod
    def create_ai_service(service_type: str, config: Dict) -> AIServiceStrategy:
        """Create AI service based on type and configuration"""
        
        if service_type == "stt":
            model_type = config.get("model", "whisper")
            if model_type == "whisper":
                return WhisperSTTService(config)
            # Future: Add support for other STT services
            # elif model_type == "wav2vec2":
            #     return Wav2Vec2STTService(config)
            
        elif service_type == "translation":
            model_type = config.get("model", "nllb")
            if model_type == "nllb":
                return NLLBTranslationService(config)
            # Future: Add support for other translation services
            # elif model_type == "google_translate":
            #     return GoogleTranslateService(config)
            
        elif service_type == "tts":
            model_type = config.get("model", "mms")
            if model_type == "mms":
                return MMSTextToSpeechService(config)
            # Future: Add support for other TTS services
            # elif model_type == "elevenlabs":
            #     return ElevenLabsTTSService(config)
        
        raise ValueError(f"Unsupported service type: {service_type}")
```

### Observer Pattern for Progress Tracking

```python
class ProgressObserver(ABC):
    @abstractmethod
    async def update(self, job_id: str, stage: str, progress: int, data: Dict):
        pass

class WebSocketProgressObserver(ProgressObserver):
    async def update(self, job_id: str, stage: str, progress: int, data: Dict):
        # Send progress update via WebSocket
        await self.websocket_manager.send_progress_update(job_id, {
            "stage": stage,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        })

class DatabaseProgressObserver(ProgressObserver):
    async def update(self, job_id: str, stage: str, progress: int, data: Dict):
        # Update database with progress
        await self.db_service.update_job_progress(job_id, stage, progress, data)
```

---

## API Design

### RESTful API Endpoints

#### Upload API
```python
@router.post("/api/v1/upload")
async def upload_video(
    file: UploadFile = File(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    user_id: Optional[str] = Form(None)
):
    """
    Upload video file for processing
    """
    # Validate file
    if file.size > 200 * 1024 * 1024:  # 200MB limit
        raise HTTPException(400, "File too large")
    
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(400, "Unsupported file format")
    
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save file to S3
    s3_key = f"inputs/{job_id}/{file.filename}"
    await s3_service.upload_file(file.file, s3_key)
    
    # Create job record
    job = await job_service.create_job(
        job_id=job_id,
        filename=file.filename,
        source_language=source_language,
        target_language=target_language,
        user_id=user_id,
        s3_input_key=s3_key
    )
    
    # Queue for processing
    await job_queue.enqueue(job_id)
    
    return {
        "job_id": job_id,
        "status": "uploaded",
        "message": "Video uploaded successfully"
    }
```

#### Job Status API
```python
@router.get("/api/v1/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Get current job processing status
    """
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    return {
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress_percentage,
        "current_stage": job.current_stage,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "estimated_completion": job.estimated_completion,
        "error_message": job.error_message
    }
```

#### Download API
```python
@router.get("/api/v1/jobs/{job_id}/download")
async def download_video(job_id: str):
    """
    Download processed video
    """
    job = await job_service.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job.status != "completed":
        raise HTTPException(400, "Job not completed")
    
    # Generate presigned URL for S3 download
    download_url = await s3_service.generate_presigned_url(
        job.s3_output_key,
        expiration=3600  # 1 hour
    )
    
    return {
        "download_url": download_url,
        "filename": f"dubbed_{job.original_filename}",
        "file_size": job.output_file_size,
        "expires_at": datetime.utcnow() + timedelta(hours=1)
    }
```

#### Preview API
```python
@router.get("/api/v1/jobs/{job_id}/preview")
async def get_video_preview(
    job_id: str,
    start_time: float = Query(0),
    duration: float = Query(30)
):
    """
    Generate video preview clip
    """
    job = await job_service.get_job(job_id)
    if not job or job.status != "completed":
        raise HTTPException(400, "Job not available for preview")
    
    # Generate preview clip
    preview_url = await video_service.generate_preview(
        job.s3_output_key,
        start_time=start_time,
        duration=duration
    )
    
    return {
        "preview_url": preview_url,
        "start_time": start_time,
        "duration": duration
    }
```

#### WebSocket for Real-time Updates
```python
@router.websocket("/api/v1/jobs/{job_id}/progress")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates
    """
    await websocket.accept()
    
    # Subscribe to job progress updates
    await progress_tracker.subscribe(job_id, websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await progress_tracker.unsubscribe(job_id, websocket)
```

---

## Database Schema

### PostgreSQL Schema Design

#### Jobs Table
```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    original_filename VARCHAR(255) NOT NULL,
    source_language VARCHAR(10) NOT NULL,
    target_language VARCHAR(10) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    progress_percentage INTEGER DEFAULT 0,
    current_stage VARCHAR(50),
    s3_input_key VARCHAR(500) NOT NULL,
    s3_output_key VARCHAR(500),
    input_file_size BIGINT,
    output_file_size BIGINT,
    processing_time_seconds INTEGER,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT valid_status CHECK (status IN (
        'uploaded', 'processing', 'completed', 'failed', 'cancelled'
    ))
);

-- Indexes for performance
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_updated_at ON jobs(updated_at);
```

#### Processing Stages Table
```sql
CREATE TABLE processing_stages (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    stage_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress_percentage INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    processing_time_seconds INTEGER,
    stage_data JSONB,
    error_message TEXT,
    
    CONSTRAINT valid_stage_status CHECK (status IN (
        'pending', 'running', 'completed', 'failed'
    ))
);

CREATE INDEX idx_processing_stages_job_id ON processing_stages(job_id);
CREATE INDEX idx_processing_stages_status ON processing_stages(status);
```

#### Language Support Table
```sql
CREATE TABLE supported_languages (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    native_name VARCHAR(100),
    stt_supported BOOLEAN DEFAULT FALSE,
    translation_supported BOOLEAN DEFAULT FALSE,
    tts_supported BOOLEAN DEFAULT FALSE,
    voice_count INTEGER DEFAULT 0
);

-- Insert supported languages
INSERT INTO supported_languages (code, name, native_name, stt_supported, translation_supported, tts_supported, voice_count) VALUES
('en', 'English', 'English', TRUE, TRUE, TRUE, 10),
('es', 'Spanish', 'Español', TRUE, TRUE, TRUE, 8),
('fr', 'French', 'Français', TRUE, TRUE, TRUE, 6),
('de', 'German', 'Deutsch', TRUE, TRUE, TRUE, 5),
('it', 'Italian', 'Italiano', TRUE, TRUE, TRUE, 4),
('pt', 'Portuguese', 'Português', TRUE, TRUE, TRUE, 4),
('ru', 'Russian', 'Русский', TRUE, TRUE, TRUE, 3),
('ja', 'Japanese', '日本語', TRUE, TRUE, TRUE, 3),
('ko', 'Korean', '한국어', TRUE, TRUE, TRUE, 2),
('zh', 'Chinese', '中文', TRUE, TRUE, TRUE, 3);
```

### Data Models (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobCreate(BaseModel):
    user_id: Optional[str] = None
    original_filename: str
    source_language: str = Field(..., min_length=2, max_length=10)
    target_language: str = Field(..., min_length=2, max_length=10)
    s3_input_key: str

class JobResponse(BaseModel):
    id: str
    user_id: Optional[str]
    original_filename: str
    source_language: str
    target_language: str
    status: JobStatus
    progress_percentage: int
    current_stage: Optional[str]
    s3_output_key: Optional[str]
    input_file_size: Optional[int]
    output_file_size: Optional[int]
    processing_time_seconds: Optional[int]
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

class ProcessingStageResponse(BaseModel):
    stage_name: str
    status: str
    progress_percentage: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    processing_time_seconds: Optional[int]
    error_message: Optional[str]
```

---

## AWS Deployment Architecture

### Infrastructure Components

```mermaid
graph TB
    subgraph "Global Edge"
        CF[CloudFront CDN]
        R53[Route 53 DNS]
    end
    
    subgraph "AWS Region (us-east-1)"
        subgraph "Availability Zone A"
            ALB[Application Load Balancer]
            ECS_A[ECS Fargate Service A]
            RDS_A[RDS Primary]
        end
        
        subgraph "Availability Zone B"
            ECS_B[ECS Fargate Service B]
            RDS_B[RDS Standby]
        end
        
        subgraph "Storage & Cache"
            S3_INPUT[S3 Input Bucket]
            S3_OUTPUT[S3 Output Bucket]
            REDIS[ElastiCache Redis]
        end
        
        subgraph "Monitoring & Logs"
            CW[CloudWatch]
            CWL[CloudWatch Logs]
        end
    end
    
    CF --> ALB
    R53 --> CF
    ALB --> ECS_A
    ALB --> ECS_B
    ECS_A --> RDS_A
    ECS_B --> RDS_A
    ECS_A --> S3_INPUT
    ECS_A --> S3_OUTPUT
    ECS_B --> S3_INPUT
    ECS_B --> S3_OUTPUT
    ECS_A --> REDIS
    ECS_B --> REDIS
    RDS_A --> RDS_B
    ECS_A --> CW
    ECS_B --> CW
    ECS_A --> CWL
    ECS_B --> CWL
```

### ECS Service Configuration

#### Dockerfile
```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### ECS Task Definition
```json
{
  "family": "video-translation-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/videoTranslationTaskRole",
  "containerDefinitions": [
    {
      "name": "video-translation-app",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/video-translation:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://user:pass@rds-endpoint:5432/videodb"},
        {"name": "REDIS_URL", "value": "redis://elasticache-endpoint:6379"},
        {"name": "S3_INPUT_BUCKET", "value": "video-translation-input"},
        {"name": "S3_OUTPUT_BUCKET", "value": "video-translation-output"},
        {"name": "AWS_DEFAULT_REGION", "value": "us-east-1"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/video-translation-service",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

#### Auto Scaling Configuration
```yaml
# ECS Service Auto Scaling
AutoScalingTarget:
  Type: AWS::ApplicationAutoScaling::ScalableTarget
  Properties:
    MaxCapacity: 10
    MinCapacity: 2
    ResourceId: service/video-translation-cluster/video-translation-service
    RoleARN: arn:aws:iam::ACCOUNT:role/application-autoscaling-ecs-service
    ScalableDimension: ecs:service:DesiredCount
    ServiceNamespace: ecs

AutoScalingPolicy:
  Type: AWS::ApplicationAutoScaling::ScalingPolicy
  Properties:
    PolicyName: video-translation-scaling-policy
    PolicyType: TargetTrackingScaling
    ScalingTargetId: !Ref AutoScalingTarget
    TargetTrackingScalingPolicyConfiguration:
      PredefinedMetricSpecification:
        PredefinedMetricType: ECSServiceAverageCPUUtilization
      TargetValue: 70.0
      ScaleOutCooldown: 300
      ScaleInCooldown: 300
```

### S3 Bucket Configuration

#### Input Bucket Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowApplicationAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/videoTranslationTaskRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::video-translation-input/*"
    },
    {
      "Sid": "AllowCrossOriginUploads",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::video-translation-input/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-acl": "bucket-owner-full-control"
        }
      }
    }
  ]
}
```

---

## Performance & Scalability

### Performance Optimization Strategies

#### 1. Async Processing Architecture
```python
class AsyncJobProcessor:
    """
    Asynchronous job processing with concurrent execution
    """
    def __init__(self, max_concurrent_jobs: int = 5):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.job_queue = asyncio.Queue()
    
    async def process_jobs(self):
        """Process jobs concurrently with rate limiting"""
        while True:
            job_id = await self.job_queue.get()
            async with self.semaphore:
                await self._process_single_job(job_id)
    
    async def _process_single_job(self, job_id: str):
        """Process individual job with error handling"""
        try:
            orchestrator = VideoDubbingOrchestrator()
            await orchestrator.process_video(job_id)
        except Exception as e:
            await self._handle_job_error(job_id, e)
```

#### 2. Model Caching and Optimization
```python
class ModelCache:
    """
    Singleton cache for AI models to avoid repeated loading
    """
    _instance = None
    _models = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_model(self, model_type: str, model_name: str):
        """Get cached model or load if not cached"""
        cache_key = f"{model_type}:{model_name}"
        
        if cache_key not in self._models:
            self._models[cache_key] = await self._load_model(model_type, model_name)
        
        return self._models[cache_key]
    
    async def _load_model(self, model_type: str, model_name: str):
        """Load model with optimization"""
        if model_type == "whisper":
            model = WhisperForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch.float16,  # Use half precision for speed
                device_map="auto"  # Automatic device placement
            )
        elif model_type == "nllb":
            model = M2M100ForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype=torch.float16
            )
        return model
```

#### 3. Database Connection Pooling
```python
class DatabasePool:
    """
    Connection pool for PostgreSQL database
    """
    def __init__(self):
        self.pool = None
    
    async def initialize(self):
        """Initialize connection pool"""
        self.pool = await asyncpg.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
    
    async def execute_query(self, query: str, *args):
        """Execute query using connection pool"""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)
```

### Scalability Considerations

#### 1. Horizontal Scaling
- **ECS Auto Scaling**: Automatic scaling based on CPU/memory utilization
- **Load Balancing**: Application Load Balancer distributes traffic
- **Database Read Replicas**: Scale read operations across multiple instances

#### 2. Vertical Scaling
- **GPU Instances**: Use GPU-enabled ECS tasks for AI model inference
- **Memory Optimization**: Efficient memory usage for large models
- **CPU Optimization**: Multi-threading for CPU-intensive operations

#### 3. Caching Strategy
```python
class CacheManager:
    """
    Multi-level caching strategy
    """
    def __init__(self):
        self.redis_client = redis.Redis(host=settings.REDIS_HOST)
        self.local_cache = {}
    
    async def get_cached_result(self, cache_key: str):
        """Get result from cache (local -> Redis)"""
        # Check local cache first
        if cache_key in self.local_cache:
            return self.local_cache[cache_key]
        
        # Check Redis cache
        cached_data = await self.redis_client.get(cache_key)
        if cached_data:
            result = json.loads(cached_data)
            self.local_cache[cache_key] = result  # Cache locally
            return result
        
        return None
    
    async def cache_result(self, cache_key: str, data: Any, ttl: int = 3600):
        """Cache result in both local and Redis"""
        self.local_cache[cache_key] = data
        await self.redis_client.setex(
            cache_key, 
            ttl, 
            json.dumps(data, default=str)
        )
```

---

## Security Considerations

### 1. Authentication & Authorization

#### API Key Authentication
```python
class APIKeyAuth:
    """
    API key-based authentication
    """
    async def authenticate(self, api_key: str) -> Optional[User]:
        """Validate API key and return user"""
        # Hash the API key for comparison
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Check against database
        user = await self.db.fetch_one(
            "SELECT * FROM api_keys WHERE key_hash = $1 AND active = true",
            key_hash
        )
        
        if user:
            # Update last used timestamp
            await self.db.execute(
                "UPDATE api_keys SET last_used = NOW() WHERE id = $1",
                user['id']
            )
            return user
        
        return None

# FastAPI dependency
async def get_current_user(api_key: str = Header(..., alias="X-API-Key")):
    auth = APIKeyAuth()
    user = await auth.authenticate(api_key)
    if not user:
        raise HTTPException(401, "Invalid API key")
    return user
```

#### Rate Limiting
```python
class RateLimiter:
    """
    Redis-based rate limiting
    """
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def check_rate_limit(self, user_id: str, limit: int = 10, window: int = 3600):
        """Check if user has exceeded rate limit"""
        key = f"rate_limit:{user_id}:{int(time.time() // window)}"
        
        current_count = await self.redis.get(key)
        if current_count and int(current_count) >= limit:
            raise HTTPException(429, "Rate limit exceeded")
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        await pipe.execute()
```

### 2. Data Security

#### File Upload Validation
```python
class FileValidator:
    """
    Comprehensive file validation
    """
    ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}
    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
    
    async def validate_upload(self, file: UploadFile) -> bool:
        """Validate uploaded file"""
        # Check file extension
        if not self._check_extension(file.filename):
            raise ValidationError("Unsupported file format")
        
        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError("File too large")
        
        # Check file content (magic bytes)
        if not await self._check_file_content(file):
            raise ValidationError("Invalid file content")
        
        return True
    
    async def _check_file_content(self, file: UploadFile) -> bool:
        """Verify file content matches extension"""
        # Read first few bytes to check magic numbers
        file.file.seek(0)
        header = await file.read(32)
        file.file.seek(0)
        
        # Check for video file signatures
        video_signatures = [
            b'\x00\x00\x00\x18ftypmp4',  # MP4
            b'\x00\x00\x00\x20ftypM4V',  # M4V
            b'RIFF',  # AVI
        ]
        
        return any(header.startswith(sig) for sig in video_signatures)
```

#### S3 Security Configuration
```python
class S3SecurityManager:
    """
    Secure S3 operations with encryption
    """
    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    async def upload_secure(self, file_data: bytes, bucket: str, key: str):
        """Upload file with server-side encryption"""
        await self.s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_data,
            ServerSideEncryption='AES256',
            Metadata={
                'uploaded-by': 'video-translation-service',
                'upload-time': datetime.utcnow().isoformat()
            }
        )
    
    async def generate_presigned_url(self, bucket: str, key: str, expiration: int = 3600):
        """Generate secure presigned URL for download"""
        return await self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
```

### 3. Network Security

#### CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)
```

#### Input Sanitization
```python
class InputSanitizer:
    """
    Sanitize and validate all inputs
    """
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path separators and dangerous characters
        safe_chars = re.sub(r'[^\w\-_\.]', '', filename)
        return safe_chars[:255]  # Limit length
    
    @staticmethod
    def validate_language_code(lang_code: str) -> bool:
        """Validate language code format"""
        return re.match(r'^[a-z]{2,3}(-[A-Z]{2})?$', lang_code) is not None
```

---

## Monitoring & Observability

### 1. Application Metrics

#### Custom Metrics Collection
```python
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
job_counter = Counter('video_jobs_total', 'Total video processing jobs', ['status', 'language_pair'])
processing_time = Histogram('video_processing_duration_seconds', 'Time spent processing videos', ['stage'])
active_jobs = Gauge('video_jobs_active', 'Currently active video processing jobs')
error_counter = Counter('video_processing_errors_total', 'Total processing errors', ['stage', 'error_type'])

class MetricsCollector:
    """
    Collect and expose application metrics
    """
    def __init__(self):
        self.job_counter = job_counter
        self.processing_time = processing_time
        self.active_jobs = active_jobs
        self.error_counter = error_counter
    
    def record_job_started(self, source_lang: str, target_lang: str):
        """Record when a job starts"""
        self.job_counter.labels(status='started', language_pair=f"{source_lang}-{target_lang}").inc()
        self.active_jobs.inc()
    
    def record_job_completed(self, source_lang: str, target_lang: str):
        """Record when a job completes"""
        self.job_counter.labels(status='completed', language_pair=f"{source_lang}-{target_lang}").inc()
        self.active_jobs.dec()
    
    def record_stage_time(self, stage: str, duration: float):
        """Record processing time for a stage"""
        self.processing_time.labels(stage=stage).observe(duration)
    
    def record_error(self, stage: str, error_type: str):
        """Record processing error"""
        self.error_counter.labels(stage=stage, error_type=error_type).inc()
```

#### 2. Health Checks and Monitoring

```python
class HealthChecker:
    """
    Comprehensive health checking for all system components
    """
    def __init__(self):
        self.db_pool = DatabasePool()
        self.redis_client = redis.Redis()
        self.s3_client = boto3.client('s3')
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Database health
        try:
            await self.db_pool.execute_query("SELECT 1")
            health_status["checks"]["database"] = {"status": "healthy"}
        except Exception as e:
            health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"
        
        # Redis health
        try:
            await self.redis_client.ping()
            health_status["checks"]["redis"] = {"status": "healthy"}
        except Exception as e:
            health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"
        
        # S3 health
        try:
            await self.s3_client.head_bucket(Bucket=settings.S3_INPUT_BUCKET)
            health_status["checks"]["s3"] = {"status": "healthy"}
        except Exception as e:
            health_status["checks"]["s3"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"
        
        # AI Models health
        try:
            model_cache = ModelCache()
            # Quick model availability check
            health_status["checks"]["ai_models"] = {"status": "healthy"}
        except Exception as e:
            health_status["checks"]["ai_models"] = {"status": "unhealthy", "error": str(e)}
            health_status["status"] = "unhealthy"
        
        return health_status

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    checker = HealthChecker()
    return await checker.check_health()
```

#### 3. Logging Configuration

```python
import structlog
from pythonjsonlogger import jsonlogger

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

class CorrelationIDMiddleware:
    """
    Add correlation ID to all requests for tracing
    """
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            correlation_id = str(uuid.uuid4())
            scope["correlation_id"] = correlation_id
            
            # Add to response headers
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers[b"x-correlation-id"] = correlation_id.encode()
                    message["headers"] = list(headers.items())
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)
```

---

## Future Extension Points

### 1. AI Service Extensions

#### Plugin Architecture for New AI Services
```python
class AIServicePlugin(ABC):
    """
    Plugin interface for new AI services
    """
    @abstractmethod
    def get_service_type(self) -> str:
        pass
    
    @abstractmethod
    def create_service(self, config: Dict[str, Any]) -> AIServiceStrategy:
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        pass

class PluginManager:
    """
    Manage AI service plugins
    """
    def __init__(self):
        self.plugins = {}
    
    def register_plugin(self, plugin: AIServicePlugin):
        """Register a new AI service plugin"""
        service_type = plugin.get_service_type()
        self.plugins[service_type] = plugin
    
    def create_service(self, service_type: str, config: Dict[str, Any]):
        """Create service using registered plugin"""
        if service_type in self.plugins:
            return self.plugins[service_type].create_service(config)
        raise ValueError(f"Unknown service type: {service_type}")

# Example: Adding Google Cloud STT
class GoogleCloudSTTPlugin(AIServicePlugin):
    def get_service_type(self) -> str:
        return "google_stt"
    
    def create_service(self, config: Dict[str, Any]) -> AIServiceStrategy:
        return GoogleCloudSTTService(config)
    
    def get_supported_languages(self) -> List[str]:
        return ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]
```

### 2. Microservices Migration Path

#### Service Decomposition Strategy
```python
# Future microservices architecture
class ServiceRegistry:
    """
    Service registry for microservices communication
    """
    def __init__(self):
        self.services = {
            "stt_service": "http://stt-service:8001",
            "translation_service": "http://translation-service:8002",
            "tts_service": "http://tts-service:8003",
            "video_processing_service": "http://video-service:8004"
        }
    
    async def call_service(self, service_name: str, endpoint: str, data: Dict):
        """Call external microservice"""
        base_url = self.services.get(service_name)
        if not base_url:
            raise ValueError(f"Unknown service: {service_name}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{base_url}{endpoint}", json=data)
            return response.json()

# Gradual migration approach
class HybridOrchestrator(VideoDubbingOrchestrator):
    """
    Orchestrator that can use both local and remote services
    """
    def __init__(self, use_microservices: bool = False):
        super().__init__()
        self.use_microservices = use_microservices
        self.service_registry = ServiceRegistry()
    
    async def _transcribe_audio(self, job_id: str, audio_segments: List[AudioSegmentData], 
                               source_language: str) -> TranscriptionResult:
        if self.use_microservices:
            # Call external STT service
            data = {
                "audio_segments": [seg.to_dict() for seg in audio_segments],
                "source_language": source_language
            }
            result = await self.service_registry.call_service(
                "stt_service", "/transcribe", data
            )
            return TranscriptionResult.from_dict(result)
        else:
            # Use local implementation
            return await super()._transcribe_audio(job_id, audio_segments, source_language)
```

### 3. Advanced Features

#### Real-time Streaming Translation
```python
class StreamingTranslationService:
    """
    Real-time video translation for live streams
    """
    def __init__(self):
        self.websocket_connections = {}
        self.processing_pipelines = {}
    
    async def start_streaming_translation(self, stream_id: str, websocket: WebSocket):
        """Start real-time translation for a stream"""
        await websocket.accept()
        self.websocket_connections[stream_id] = websocket
        
        # Create streaming pipeline
        pipeline = StreamingPipeline(
            stt_service=self.ai_factory.create_stt_service({"streaming": True}),
            translation_service=self.ai_factory.create_translation_service({}),
            tts_service=self.ai_factory.create_tts_service({"streaming": True})
        )
        
        self.processing_pipelines[stream_id] = pipeline
        
        try:
            async for audio_chunk in self._receive_audio_chunks(websocket):
                translated_audio = await pipeline.process_chunk(audio_chunk)
                await websocket.send_bytes(translated_audio)
        except WebSocketDisconnect:
            await self._cleanup_stream(stream_id)
```

#### Voice Cloning Integration
```python
class VoiceCloningService:
    """
    Advanced voice cloning for personalized dubbing
    """
    def __init__(self):
        self.voice_models = {}
    
    async def create_voice_model(self, user_id: str, voice_samples: List[AudioSegment]):
        """Create personalized voice model from samples"""
        # Train voice cloning model
        model = await self._train_voice_model(voice_samples)
        self.voice_models[user_id] = model
        return model
    
    async def synthesize_with_cloned_voice(self, text: str, user_id: str) -> AudioSegment:
        """Synthesize speech using cloned voice"""
        if user_id not in self.voice_models:
            raise ValueError("Voice model not found")
        
        model = self.voice_models[user_id]
        return await model.synthesize(text)
```

#### Batch Processing Support
```python
class BatchProcessor:
    """
    Process multiple videos in batch
    """
    def __init__(self):
        self.batch_queue = asyncio.Queue()
        self.batch_results = {}
    
    async def submit_batch(self, batch_id: str, video_files: List[str], 
                          source_lang: str, target_lang: str):
        """Submit batch of videos for processing"""
        batch_job = BatchJob(
            batch_id=batch_id,
            video_files=video_files,
            source_lang=source_lang,
            target_lang=target_lang
        )
        
        await self.batch_queue.put(batch_job)
        return batch_id
    
    async def process_batch(self, batch_job: BatchJob):
        """Process batch of videos concurrently"""
        tasks = []
        for video_file in batch_job.video_files:
            task = asyncio.create_task(
                self._process_single_video(video_file, batch_job.source_lang, batch_job.target_lang)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.batch_results[batch_job.batch_id] = results
```

### 4. Performance Enhancements

#### GPU Acceleration Support
```python
class GPUAcceleratedService:
    """
    GPU-accelerated AI service implementation
    """
    def __init__(self, device: str = "cuda:0"):
        self.device = device
        self.model = None
    
    async def load_model_on_gpu(self, model_name: str):
        """Load model on GPU with optimization"""
        self.model = AutoModel.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map=self.device
        )
        
        # Enable optimizations
        if hasattr(self.model, 'half'):
            self.model = self.model.half()
        
        # Compile model for faster inference (PyTorch 2.0+)
        if hasattr(torch, 'compile'):
            self.model = torch.compile(self.model)
```

#### Caching and CDN Integration
```python
class AdvancedCacheManager:
    """
    Advanced caching with CDN integration
    """
    def __init__(self):
        self.redis_client = redis.Redis()
        self.cdn_client = boto3.client('cloudfront')
    
    async def cache_processed_video(self, job_id: str, video_data: bytes):
        """Cache processed video with CDN invalidation"""
        # Store in Redis for quick access
        await self.redis_client.setex(
            f"video:{job_id}", 
            3600,  # 1 hour TTL
            video_data
        )
        
        # Upload to CDN
        s3_key = f"cached/{job_id}.mp4"
        await self.s3_service.upload_file(video_data, s3_key)
        
        # Create CDN distribution
        cdn_url = await self._create_cdn_distribution(s3_key)
        return cdn_url
```

---

## Conclusion

This High-Level Design document presents a comprehensive architecture for an AI-powered video translation service MVP that meets all the assignment requirements while maintaining extensibility for future enhancements.

### Key Architectural Decisions

1. **Monolithic MVP Approach**: Single deployable service for simplicity while maintaining modular internal architecture
2. **Strategy and Factory Patterns**: Enable easy swapping of AI services (Whisper, NLLB, MMS)
3. **Async Processing**: Non-blocking operations for better performance and scalability
4. **Cloud-Native Design**: Optimized for AWS deployment with auto-scaling capabilities
5. **Comprehensive Monitoring**: Full observability with metrics, logging, and health checks

### MVP Implementation Priority

**Phase 1 (Core MVP - 4-6 weeks)**:
- Basic upload/download API
- 11-stage processing pipeline
- Single language pair support (English to Spanish)
- Basic progress tracking
- Simple web frontend

**Phase 2 (Enhanced MVP - 2-3 weeks)**:
- Multiple language support (10+ languages)
- Video preview functionality
- Enhanced error handling and recovery
- Performance optimizations
- Advanced monitoring and alerting

**Phase 3 (Production Ready - 2-3 weeks)**:
- Auto-scaling implementation
- Security hardening
- Load testing and optimization
- Documentation and deployment automation

### Technical Benefits

1. **Scalability**: Architecture supports horizontal scaling from day one
2. **Maintainability**: Clean separation of concerns and modular design
3. **Extensibility**: Strategy and Factory patterns enable easy AI service swapping
4. **Reliability**: Comprehensive error handling and monitoring
5. **Performance**: Async processing and caching strategies
6. **Security**: Multi-layered security approach with authentication, validation, and encryption

### Business Benefits

1. **Fast Time-to-Market**: MVP can be deployed in 4-6 weeks
2. **Cost-Effective**: Single service deployment reduces operational complexity
3. **Global Reach**: CDN integration ensures worldwide performance
4. **Future-Proof**: Architecture supports migration to microservices when needed
5. **Competitive Advantage**: State-of-the-art AI models provide high-quality results

This architecture provides a solid foundation for building a production-ready AI-powered video translation service that can scale from MVP to enterprise-level deployment while maintaining code quality, performance, and security standards.
