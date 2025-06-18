# Copyright 2024 Jordi Mas i Hernàndez <jmas@softcatala.org>
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

import argparse

WHISPER_MODEL_NAMES = [
    "medium",
    "large-v2",
    "large-v3",
]


class NewlinePreservingHelpFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        # Split the text by explicit newlines first
        lines = text.splitlines()
        # Then apply the default behavior for line wrapping
        wrapped_lines = []
        for line in lines:
            wrapped_lines.extend(argparse.HelpFormatter._split_lines(self, line, width))
        return wrapped_lines


class CommandLine:

    @staticmethod
    def read_parameters():
        """Parses command-line arguments and runs the dubbing process."""
        parser = argparse.ArgumentParser(
            description="AI dubbing system which uses machine learning models to automatically translate and synchronize audio dialogue into different languages",
            formatter_class=NewlinePreservingHelpFormatter,
        )
        parser.add_argument(
            "--input_file",
            required=True,
            help="Path to the input video file.",
        )
        parser.add_argument(
            "--source_language",
            help="Source language (ISO 639-3)",
        )
        parser.add_argument(
            "--target_language",
            required=True,
            help="Target language for dubbing (ISO 639-3).",
        )
        parser.add_argument(
            "--tts",
            type=str,
            default="mms",
            choices=["mms", "openai", "api"],
            help=(
                "Text to Speech engine to use. Choices are:\n"
                "'mms': Meta Multilingual Speech engine, supports +1100 languages.\n"
                "'openai': OpenAI TTS.\n"
                "'api': Implements a user defined TTS API contract to enable non supported TTS.\n"
            ),
        )
        parser.add_argument(
            "--stt",
            type=str,
            default="auto",
            choices=["auto", "faster-whisper", "transformers"],
            help=(
                "Speech to text. Choices are:\n"
                "'auto': Autoselect best implementation.\n"
                "'faster-whisper': Faster-whisper's OpenAI whisper implementation.\n"
                "'transformers': Transformers OpenAI whisper implementation.\n"
            ),
        )

        parser.add_argument(
            "--translator",
            type=str,
            default="nllb",
            choices=["nllb"],
            help=(
                "Translation engine to use. Choices are:\n"
                "'nllb': Meta's no Language Left Behind (NLLB).\n"
            ),
        )

        parser.add_argument(
            "--nllb_model",
            type=str,
            default="nllb-200-3.3B",
            choices=["nllb-200-1.3B", "nllb-200-3.3B"],
            help="Meta NLLB translation model size. Choices are:\n"
            "'nllb-200-3.3B': gives best translation quality.\n"
            "'nllb-200-1.3B': is the fastest.\n",
        )

        parser.add_argument(
            "--whisper_model",
            default="large-v3",
            choices=WHISPER_MODEL_NAMES,
            help="name of the OpenAI Whisper speech to text model size to use",
        )

        return parser.parse_args()
