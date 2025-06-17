# Execution Flow

This document traces the complete execution flow of the open-dubbing system, from input video to final dubbed output.

## High-Level Execution Overview

The dubbing process follows a sequential 7-stage pipeline orchestrated by the `Dubber` class:

```
Input Video → Preprocessing → STT → Translation → TTS Config → TTS → Postprocessing → Output
```

Each stage processes and enriches the `utterance_metadata` structure that carries information throughout the pipeline.

## Detailed Execution Flow

### Stage 1: Preprocessing (`run_preprocessing()`)

**Purpose:** Prepare audio and video for processing by separating tracks and isolating vocals.

#### Step 1.1: Video/Audio Separation
```python
video_file, audio_file = VideoProcessing.split_audio_video(
    video_file=self.input_file, 
    output_directory=self.output_directory
)
```

**Process:**
- Uses FFmpeg to extract audio track from video
- Creates separate video (without audio) and audio files
- Preserves original video quality and format

**Output Files:**
- `{filename}_video.mp4`: Video without audio track
- `{filename}_audio.wav`: Extracted audio in WAV format

#### Step 1.2: Vocal Separation with Demucs
```python
demucs = Demucs()
demucs_command = demucs.build_demucs_command(
    audio_file=audio_file,
    output_directory=self.output_directory,
    device=self.device,
)
demucs.execute_demucs_command(command=demucs_command)
```

**Process:**
- Uses Meta's Demucs AI model for source separation
- Separates vocals from background music and effects
- Runs on specified device (CPU/GPU) for optimal performance

**Output Files:**
- `vocals.wav`: Isolated vocal track
- `no_vocals.wav`: Background music and effects

#### Step 1.3: Speaker Diarization
```python
utterance_metadata = audio_processing.create_pyannote_timestamps(
    audio_file=audio_file,
    pipeline=self.pyannote_pipeline,
    device=self.device,
)
```

**Process:**
- Uses PyAnnote Audio for speaker diarization
- Identifies different speakers and their speaking segments
- Creates timestamps for each utterance with speaker IDs

**Utterance Metadata Structure:**
```json
{
    "utterances": [
        {
            "start": 7.607843750000001,
            "end": 8.687843750000003,
            "speaker_id": "SPEAKER_00",
            "path": "",
            "text": "",
            "for_dubbing": true
        }
    ]
}
```

#### Step 1.4: Audio Segmentation
```python
utterance_metadata = audio_processing.run_cut_and_save_audio(
    utterance_metadata=utterance_metadata,
    audio_file=audio_file,
    output_directory=self.output_directory,
)
```

**Process:**
- Cuts original audio into individual utterance segments
- Saves each segment as a separate audio file
- Updates metadata with file paths

**Output Files:**
- `chunk_{start}_{end}.mp3`: Individual utterance audio files

### Stage 2: Speech-to-Text (`run_speech_to_text()`)

**Purpose:** Transcribe audio segments and analyze speaker characteristics.

#### Step 2.1: Audio Transcription
```python
utterance_metadata = self.stt.transcribe_audio_chunks(
    utterance_metadata=self.utterance_metadata,
    source_language=self.source_language,
    no_dubbing_phrases=[],
)
```

**Process:**
- Uses selected Whisper model (Faster-Whisper or Transformers)
- Transcribes each audio segment individually
- Applies language-specific processing and filtering

**Data Flow:**
```
Audio Segments → Whisper Model → Text Transcriptions → Metadata Update
```

#### Step 2.2: Gender Detection
```python
speaker_info = self.stt.predict_gender(
    file=media_file,
    utterance_metadata=utterance_metadata,
)
```

**Process:**
- Uses Wav2Vec2-based gender classifier
- Analyzes voice characteristics for each speaker
- Provides gender predictions for voice assignment

#### Step 2.3: Speaker Information Integration
```python
self.utterance_metadata = self.stt.add_speaker_info(
    utterance_metadata=utterance_metadata, 
    speaker_info=speaker_info
)
```

**Process:**
- Merges gender predictions with utterance metadata
- Associates speaker IDs with gender information
- Prepares data for voice assignment in TTS stage

**Updated Metadata:**
```json
{
    "start": 7.607843750000001,
    "end": 8.687843750000003,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607843750000001_8.687843750000003.mp3",
    "text": "And I love this city.",
    "for_dubbing": true,
    "gender": "Male"
}
```

#### Step 2.4: Metadata Cleanup
```python
utterance = Utterance(self.target_language, self.output_directory)
self.utterance_metadata = utterance.get_without_empty_blocks(
    self.utterance_metadata
)
```

**Process:**
- Removes utterances with empty or invalid transcriptions
- Filters out non-speech segments
- Prepares clean data for translation

### Stage 3: Translation (`run_translation()`)

**Purpose:** Translate transcribed text from source to target language.

#### Step 3.1: Text Translation
```python
self.utterance_metadata = self.translation.translate_utterances(
    utterance_metadata=self.utterance_metadata,
    source_language=self.source_language,
    target_language=self.target_language,
)
```

**Process:**
- Uses selected translation engine (NLLB or Apertium)
- Translates text while preserving context and meaning
- Handles batch processing for efficiency

**Translation Engines:**

**NLLB (Neural):**
```
Source Text → Tokenization → Neural Model → Target Text
```

**Apertium (Rule-based):**
```
Source Text → API Request → Rule Processing → Target Text
```

**Updated Metadata:**
```json
{
    "start": 7.607843750000001,
    "end": 8.687843750000003,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607843750000001_8.687843750000003.mp3",
    "text": "And I love this city.",
    "for_dubbing": true,
    "gender": "Male",
    "translated_text": "I m'encanta aquesta ciutat."
}
```

### Stage 4: Text-to-Speech Configuration (`run_configure_text_to_speech()`)

**Purpose:** Assign appropriate voices and configure TTS parameters.

#### Step 4.1: Voice Assignment
```python
assigned_voices = self.tts.assign_voices(
    utterance_metadata=self.utterance_metadata,
    target_language=self.target_language,
    target_language_region=self.target_language_region,
)
```

**Process:**
- Matches speakers to available voices based on gender
- Considers language and regional preferences
- Ensures consistent voice assignment per speaker

**Voice Selection Logic:**
```
Speaker Gender + Target Language + Region → Voice Database → Assigned Voice
```

#### Step 4.2: Metadata Update
```python
self.utterance_metadata = self.tts.update_utterance_metadata(
    utterance_metadata=self.utterance_metadata,
    assigned_voices=assigned_voices,
)
```

**Updated Metadata:**
```json
{
    "start": 7.607843750000001,
    "end": 8.687843750000003,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607843750000001_8.687843750000003.mp3",
    "text": "And I love this city.",
    "for_dubbing": true,
    "gender": "Male",
    "translated_text": "I m'encanta aquesta ciutat.",
    "assigned_voice": "ca-ES-EnricNeural",
    "speed": 1.0
}
```

### Stage 5: Text-to-Speech Generation (`run_text_to_speech()`)

**Purpose:** Generate synthetic speech for translated text with timing synchronization.

#### Step 5.1: Speech Synthesis
```python
self.utterance_metadata = self.tts.dub_utterances(
    utterance_metadata=self.utterance_metadata,
    output_directory=self.output_directory,
    target_language=self.target_language,
    audio_file=self.preprocessing_output.audio_file,
)
```

**Process:**
- Generates speech for each translated utterance
- Calculates optimal speed for timing synchronization
- Creates dubbed audio files for each segment

**TTS Engine Processing:**

**For each utterance:**
1. **Speed Calculation:**
   ```python
   target_speed = self._calculate_target_utterance_speed(
       original_duration=utterance_duration,
       synthesized_duration=tts_duration
   )
   ```

2. **Speech Generation:**
   ```
   Translated Text + Voice + Speed → TTS Engine → Audio File
   ```

3. **Post-processing:**
   - Remove silence from beginning/end
   - Adjust speed if necessary
   - Convert to MP3 format

**Output Files:**
- `dubbed_chunk_{start}_{end}.mp3`: Dubbed audio for each utterance

**Final Metadata:**
```json
{
    "start": 7.607843750000001,
    "end": 8.687843750000003,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607843750000001_8.687843750000003.mp3",
    "text": "And I love this city.",
    "for_dubbing": true,
    "gender": "Male",
    "translated_text": "I m'encanta aquesta ciutat.",
    "assigned_voice": "ca-ES-EnricNeural",
    "speed": 1.3,
    "dubbed_path": "dubbed_chunk_7.607843750000001_8.687843750000003.mp3",
    "hash": "b11d7f0e2aa5475e652937469d89ef0a178fecea726f076095942d552944089f"
}
```

### Stage 6: Postprocessing (`run_postprocessing()`)

**Purpose:** Combine dubbed audio segments with background audio and video.

#### Step 6.1: Dubbed Vocal Track Assembly
```python
dubbed_audio_vocals_file = audio_processing.insert_audio_at_timestamps(
    utterance_metadata=self.utterance_metadata,
    background_audio_file=self.preprocessing_output.audio_background_file,
    output_directory=self.output_directory,
)
```

**Process:**
- Creates timeline of dubbed vocal segments
- Inserts dubbed audio at original timestamps
- Maintains silence for non-speech segments

**Timeline Assembly:**
```
[Silence] → [Dubbed Segment 1] → [Silence] → [Dubbed Segment 2] → ...
```

#### Step 6.2: Background and Vocal Mixing
```python
dubbed_audio_file = audio_processing.merge_background_and_vocals(
    background_audio_file=self.preprocessing_output.audio_background_file,
    dubbed_vocals_audio_file=dubbed_audio_vocals_file,
    output_directory=self.output_directory,
    target_language=self.target_language,
    vocals_volume_adjustment=5.0,
    background_volume_adjustment=0.0,
)
```

**Process:**
- Combines dubbed vocals with original background audio
- Applies volume adjustments for optimal balance
- Creates final dubbed audio track

**Audio Mixing:**
```
Dubbed Vocals (adjusted) + Background Audio (adjusted) = Final Audio
```

#### Step 6.3: Video and Audio Combination
```python
dubbed_video_file = VideoProcessing.combine_audio_video(
    video_file=self.preprocessing_output.video_file,
    dubbed_audio_file=dubbed_audio_file,
    output_directory=self.output_directory,
    target_language=self.target_language,
)
```

**Process:**
- Combines original video with dubbed audio track
- Uses FFmpeg for precise synchronization
- Maintains original video quality and format

**Final Output:**
- `dubbed_video_{target_language}.mp4`: Complete dubbed video

### Stage 7: Subtitle Generation and Cleanup

#### Step 7.1: Subtitle Generation (Optional)
```python
self.run_generate_subtitles()
```

**Process:**
- Generates SRT subtitle files if requested
- Creates subtitles for source and/or target language
- Embeds subtitles into video file

**Subtitle Files:**
- `{source_language}.srt`: Original language subtitles
- `{target_language}.srt`: Translated subtitles

#### Step 7.2: Metadata Persistence
```python
self._save_utterances()
```

**Process:**
- Saves complete utterance metadata to JSON file
- Enables post-editing and update operations
- Preserves all processing information

**Metadata File:**
- `utterance_metadata_{target_language}.json`: Complete processing metadata

#### Step 7.3: Cleanup (Optional)
```python
self.run_cleaning()
```

**Process:**
- Removes intermediate files if requested
- Keeps only final output and metadata
- Reduces storage usage

## Data Flow Through Pipeline

### Utterance Metadata Evolution

The central data structure evolves through each stage:

**Stage 1 (Preprocessing):**
```json
{
    "start": 7.607,
    "end": 8.687,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607_8.687.mp3"
}
```

**Stage 2 (STT):**
```json
{
    "start": 7.607,
    "end": 8.687,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607_8.687.mp3",
    "text": "And I love this city.",
    "gender": "Male"
}
```

**Stage 3 (Translation):**
```json
{
    "start": 7.607,
    "end": 8.687,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607_8.687.mp3",
    "text": "And I love this city.",
    "gender": "Male",
    "translated_text": "I m'encanta aquesta ciutat."
}
```

**Stage 4 (TTS Config):**
```json
{
    "start": 7.607,
    "end": 8.687,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607_8.687.mp3",
    "text": "And I love this city.",
    "gender": "Male",
    "translated_text": "I m'encanta aquesta ciutat.",
    "assigned_voice": "ca-ES-EnricNeural",
    "speed": 1.0
}
```

**Stage 5 (TTS):**
```json
{
    "start": 7.607,
    "end": 8.687,
    "speaker_id": "SPEAKER_00",
    "path": "chunk_7.607_8.687.mp3",
    "text": "And I love this city.",
    "gender": "Male",
    "translated_text": "I m'encanta aquesta ciutat.",
    "assigned_voice": "ca-ES-EnricNeural",
    "speed": 1.3,
    "dubbed_path": "dubbed_chunk_7.607_8.687.mp3",
    "hash": "b11d7f0e2aa5475e..."
}
```

## Error Handling and Recovery

### Stage-Level Error Handling

Each stage includes error handling mechanisms:

1. **Validation**: Input validation before processing
2. **Graceful Degradation**: Fallback options when possible
3. **Error Propagation**: Clear error messages with exit codes
4. **Resource Cleanup**: Proper cleanup on failure

### Update Mode Execution Flow

The system supports an update mode for post-editing workflows:

#### Update Mode Process (`dubber.update()`)

1. **Load Existing Metadata:**
   ```python
   self.utterance_metadata, self.preprocessing_output, _ = utterance.load_utterances()
   ```

2. **Identify Modified Utterances:**
   ```python
   modified_utterances = utterance.get_modified_utterances(self.utterance_metadata)
   ```

3. **Regenerate Only Changed Parts:**
   - Voice assignment for modified utterances
   - TTS generation for changed text/voices
   - Postprocessing with updated audio

4. **Preserve Unchanged Elements:**
   - Original preprocessing artifacts
   - Unmodified dubbed audio segments
   - Existing metadata structure

## Performance Monitoring

### Execution Timing

The system tracks execution time for each stage:

```python
def log_debug_task_and_getime(self, text, start_time):
    process = psutil.Process(os.getpid())
    current_rss = process.memory_info().rss / 1024**2
    _time = time.time() - start_time
    logger().info(f"Completed task '{text}': current_rss {current_rss:.2f} MB, time {_time:.2f}s")
    return _time
```

### Memory Monitoring

- Real-time memory usage tracking
- Maximum memory usage reporting
- Resource optimization recommendations

### Progress Reporting

Each stage provides progress updates:
- Stage completion notifications
- Processing time measurements
- Memory usage statistics
- Overall pipeline progress

## File Output Structure

### Final Output Files

```
output_directory/
├── dubbed_video_{target_language}.mp4     # Final dubbed video
├── dubbed_audio_{target_language}.mp3     # Final dubbed audio
├── utterance_metadata_{target_language}.json  # Complete metadata
├── {source_language}.srt                  # Source subtitles (optional)
├── {target_language}.srt                  # Target subtitles (optional)
└── intermediate_files/                    # Temporary processing files
    ├── {filename}_video.mp4               # Video without audio
    ├── {filename}_audio.wav               # Original audio
    ├── vocals.wav                         # Separated vocals
    ├── no_vocals.wav                      # Background audio
    ├── chunk_*.mp3                        # Original utterance segments
    └── dubbed_chunk_*.mp3                 # Dubbed utterance segments
```

### Metadata Persistence

The complete processing state is saved to enable:
- Post-editing workflows
- Incremental updates
- Quality analysis
- Debugging and troubleshooting

## Summary

The execution flow demonstrates a sophisticated pipeline that:

1. **Preserves Quality**: Each stage maintains high-quality processing
2. **Enables Flexibility**: Multiple engine options for different use cases
3. **Supports Iteration**: Update mode allows refinement of results
4. **Provides Transparency**: Complete metadata tracking for all operations
5. **Optimizes Performance**: Efficient processing with resource monitoring

The modular design allows for easy extension and modification while maintaining a clear, predictable execution path from input video to final dubbed output.
