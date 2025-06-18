# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import dataclasses
import functools
import logging
import os
import re
import shutil
import sys
import time

from typing import Final

import psutil
import torch

from pyannote.audio import Pipeline

from open_dubbing import audio_processing, logger
from open_dubbing.exit_code import ExitCode
from open_dubbing.ffmpeg import FFmpeg
from open_dubbing.preprocessing import PreprocessingArtifacts
from open_dubbing.speech_to_text import SpeechToText
from open_dubbing.text_to_speech import TextToSpeech
from open_dubbing.translation import Translation
from open_dubbing.utterance import Utterance
from open_dubbing.video_processing import VideoProcessing

_DEFAULT_PYANNOTE_MODEL: Final[str] = "pyannote/speaker-diarization-3.1"
_NUMBER_OF_STEPS: Final[int] = 7


@dataclasses.dataclass
class PostprocessingArtifacts:
    """Instance with postprocessing outputs.

    Attributes:
        audio_file: A path to a dubbed audio file.
        video_file: A path to a dubbed video file. The video is optional.
    """

    audio_file: str
    video_file: str | None


class PyAnnoteAccessError(Exception):
    """Error when establishing access to PyAnnore from Hugging Face."""

    pass


def rename_input_file(original_input_file: str) -> str:
    """Converts a filename to lowercase letters and numbers only, preserving the file extension.

    Args:
        original_filename: The filename to normalize.

    Returns:
        The normalized filename.
    """
    directory, filename = os.path.split(original_input_file)
    base_name, extension = os.path.splitext(filename)
    normalized_name = re.sub(r"[^a-z0-9]", "", base_name.lower())
    return os.path.join(directory, normalized_name + extension)


def overwrite_input_file(input_file: str, updated_input_file: str) -> None:
    """Renames a file in place to lowercase letters and numbers only, preserving the file extension."""

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"File '{input_file}' not found.")

    shutil.move(input_file, updated_input_file)


class Dubber:
    """A class to manage the entire ad dubbing process."""

    def __init__(
        self,
        *,
        input_file: str,
        output_directory: str,
        source_language: str,
        target_language: str,
        hugging_face_token: str | None = None,
        tts: TextToSpeech,
        translation: Translation,
        stt: SpeechToText,
        device: str,
        cpu_threads: int = 0,
        clean_intermediate_files: bool = False,
    ) -> None:
        self._input_file = input_file
        self.output_directory = output_directory
        self.source_language = source_language
        self.target_language = target_language
        self.pyannote_model = _DEFAULT_PYANNOTE_MODEL
        self.hugging_face_token = hugging_face_token
        self.utterance_metadata = None
        self._number_of_steps = _NUMBER_OF_STEPS
        self.tts = tts
        self.translation = translation
        self.stt = stt
        self.device = device
        self.cpu_threads = cpu_threads
        self.clean_intermediate_files = clean_intermediate_files
        self.preprocessing_output = None

        if cpu_threads > 0:
            torch.set_num_threads(cpu_threads)

    @functools.cached_property
    def input_file(self):
        renamed_input_file = rename_input_file(self._input_file)
        if renamed_input_file != self._input_file:
            logger().warning(
                "The input file was renamed because the original name contained"
                " spaces, hyphens, or other incompatible characters. The updated"
                f" input file is: {renamed_input_file}"
            )
            overwrite_input_file(
                input_file=self._input_file, updated_input_file=renamed_input_file
            )
        return renamed_input_file

    def log_maxrss_memory(self):
        if sys.platform == "win32" or sys.platform == "win64":
            return

        import resource

        max_rss_self = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        if sys.platform == "darwin":
            return max_rss_self / 1024

        logger().info(f"Maximum memory used: {max_rss_self:.0f} MB")

    def log_debug_task_and_getime(self, text, start_time):
        process = psutil.Process(os.getpid())
        current_rss = process.memory_info().rss / 1024**2
        _time = time.time() - start_time
        logger().info(
            f"Completed task '{text}': current_rss {current_rss:.2f} MB, time {_time:.2f}s"
        )
        return _time

    @functools.cached_property
    def pyannote_pipeline(self) -> Pipeline:
        """Loads the PyAnnote diarization pipeline."""
        return Pipeline.from_pretrained(
            self.pyannote_model, use_auth_token=self.hugging_face_token
        )

    def _verify_api_access(self) -> None:
        """Verifies access to all the required APIs."""
        logger().debug("Verifying access to PyAnnote from HuggingFace.")
        if not self.pyannote_pipeline:
            raise PyAnnoteAccessError(
                "No access to HuggingFace. Make sure you passed the correct API token"
                " either as 'hugging_face_token' or through the"
                " environmental variable. Also, please make sure you accepted the"
                " user agreement for the segmentation model"
                " (https://huggingface.co/pyannote/segmentation-3.0) and the speaker"
                " diarization model"
                " (https://huggingface.co/pyannote/speaker-diarization-3.1)."
            )
        logger().debug("Access to PyAnnote from HuggingFace verified.")

    def run_preprocessing(self) -> None:
        """Splits audio/video, applies DEMUCS, and segments audio into utterances with PyAnnote."""
        video_file, audio_file = VideoProcessing.split_audio_video(
            video_file=self.input_file, output_directory=self.output_directory
        )
        utterance_metadata = audio_processing.create_pyannote_timestamps(
            audio_file=audio_file,
            pipeline=self.pyannote_pipeline,
            device=self.device,
        )
        utterance_metadata = audio_processing.run_cut_and_save_audio(
            utterance_metadata=utterance_metadata,
            audio_file=audio_file,
            output_directory=self.output_directory,
        )
        self.utterance_metadata = utterance_metadata
        self.preprocessing_output = PreprocessingArtifacts(
            video_file=video_file,
            audio_file=audio_file,
        )

    def run_speech_to_text(self) -> None:
        """Transcribes audio, applies speaker diarization, and updates metadata with Gemini.

        Returns:
            Updated utterance metadata with speaker information and transcriptions.
        """

        media_file = (
            self.preprocessing_output.video_file
            if self.preprocessing_output.video_file
            else self.preprocessing_output.audio_file
        )
        utterance_metadata = self.stt.transcribe_audio_chunks(
            utterance_metadata=self.utterance_metadata,
            source_language=self.source_language,
            no_dubbing_phrases=[],
        )
        speaker_info = self.stt.predict_gender(
            file=media_file,
            utterance_metadata=utterance_metadata,
        )
        self.utterance_metadata = self.stt.add_speaker_info(
            utterance_metadata=utterance_metadata, speaker_info=speaker_info
        )

        utterance = Utterance(self.target_language, self.output_directory)
        self.utterance_metadata = utterance.get_without_empty_blocks(
            self.utterance_metadata
        )

    def run_translation(self) -> None:
        """Translates transcribed text and potentially merges utterances"""

        self.utterance_metadata = self.translation.translate_utterances(
            utterance_metadata=self.utterance_metadata,
            source_language=self.source_language,
            target_language=self.target_language,
        )

    def run_configure_text_to_speech(self) -> None:
        """Configures the Text-To-Speech process.

        Returns:
            Updated utterance metadata with assigned voices
            and Text-To-Speech settings.
        """
        assigned_voices = self.tts.assign_voices(
            utterance_metadata=self.utterance_metadata,
            target_language=self.target_language,
        )
        self.utterance_metadata = self.tts.update_utterance_metadata(
            utterance_metadata=self.utterance_metadata,
            assigned_voices=assigned_voices,
        )

    def run_text_to_speech(self) -> None:
        """Converts translated text to speech and dubs utterance"""
        self.utterance_metadata = self.tts.dub_utterances(
            utterance_metadata=self.utterance_metadata,
            output_directory=self.output_directory,
            target_language=self.target_language,
            audio_file=self.preprocessing_output.audio_file,
        )

    def run_cleaning(self) -> None:
        if not self.clean_intermediate_files:
            return

        output_directory = None
        paths, dubbed_paths = Utterance(
            self.target_language, self.output_directory
        ).get_files_paths(self.utterance_metadata)
        for path in paths + dubbed_paths:
            if os.path.exists(path):
                os.remove(path)
            if not output_directory:
                output_directory = os.path.dirname(path)

        if output_directory:
            for path in [
                f"dubbed_audio_{self.target_language}.mp3",
            ]:
                full_path = os.path.join(output_directory, path)
                if os.path.exists(full_path):
                    os.remove(full_path)

    def run_postprocessing(self) -> None:
        """Creates dubbed audio track and combines it with video.

        Returns:
            Path to the final dubbed output file.
        """
        dubbed_audio_file = audio_processing.create_dubbed_audio_track(
            utterance_metadata=self.utterance_metadata,
            original_audio_file=self.preprocessing_output.audio_file,
            output_directory=self.output_directory,
            target_language=self.target_language,
        )
        if not self.preprocessing_output.video_file:
            raise ValueError(
                "A video file must be provided if the input file is a video."
            )
        dubbed_video_file = VideoProcessing.combine_audio_video(
            video_file=self.preprocessing_output.video_file,
            dubbed_audio_file=dubbed_audio_file,
            output_directory=self.output_directory,
            target_language=self.target_language,
        )
        self.postprocessing_output = PostprocessingArtifacts(
            audio_file=dubbed_audio_file,
            video_file=dubbed_video_file,
        )

    def _save_utterances(self):
        metadata = {
            "source_language": self.source_language,
        }
        Utterance(self.target_language, self.output_directory).save_utterances(
            utterance_metadata=self.utterance_metadata,
            preprocessing_output=self.preprocessing_output,
            metadata=metadata,
        )

    def dub(self) -> PostprocessingArtifacts:
        """Orchestrates the entire dubbing process."""
        self._verify_api_access()
        logger().info("Dubbing process starting...")
        times = {}
        start_time = time.time()

        task_start_time = time.time()
        self.run_preprocessing()
        times["preprocessing"] = self.log_debug_task_and_getime(
            "Preprocessing completed", task_start_time
        )
        logger().info("Speech to text...")
        task_start_time = time.time()
        self.run_speech_to_text()
        times["stt"] = self.log_debug_task_and_getime(
            "Speech to text completed", task_start_time
        )
        task_start_time = time.time()

        self.run_translation()
        times["translation"] = self.log_debug_task_and_getime(
            "Translation completed", task_start_time
        )

        task_start_time = time.time()
        self.run_configure_text_to_speech()
        self.run_text_to_speech()
        times["tts"] = self.log_debug_task_and_getime(
            "Text to speech completed", task_start_time
        )

        task_start_time = time.time()

        self.run_postprocessing()
        self._save_utterances()
        self.run_cleaning()
        times["postprocessing"] = self.log_debug_task_and_getime(
            "Post processing completed", task_start_time
        )
        logger().info("Dubbing process finished.")
        total_time = time.time() - start_time
        logger().info(f"Total execution time: {total_time:.2f} secs")
        for task in times:
            _time = times[task]
            per = _time * 100 / total_time
            logger().info(f" Task '{task}' in {_time:.2f} secs ({per:.2f}%)")

        self.log_maxrss_memory()
        if logger().getEffectiveLevel() == logging.getLevelName("DEBUG"):
            self.stt.dump_transcriptions(
                output_directory=self.output_directory,
                utterance_metadata=self.utterance_metadata,
            )

        logger().info("Output files saved in: %s.", self.output_directory)

        return self.postprocessing_output
