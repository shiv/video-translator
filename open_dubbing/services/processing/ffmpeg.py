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

import os
import shutil
import subprocess
import tempfile

from typing import List

from open_dubbing import logger


class FFmpeg:

    def _run(self, *, command: List[str], fail: bool = True):
        with open(os.devnull, "wb") as devnull:
            try:
                result = subprocess.run(command, stdout=devnull, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    raise subprocess.CalledProcessError(result.returncode, command)
            except subprocess.CalledProcessError as e:
                logger().error(
                    f"Error running command: {command} failed with exit code {e.returncode} and output '{result.stderr}'"
                )
                if fail:
                    raise

    def convert_to_format(self, *, source: str, target: str):
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            source,
            target,
        ]
        FFmpeg()._run(command=cmd)

    def remove_silence(self, *, filename: str):
        tmp_filename = ""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            tmp_filename = temp_file.name
            shutil.copyfile(filename, tmp_filename)
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                tmp_filename,
                "-af",
                "silenceremove=stop_periods=-1:stop_duration=0.1:stop_threshold=-50dB",
                filename,
            ]
            FFmpeg()._run(command=cmd, fail=False)

        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)

    def adjust_audio_speed(self, *, filename: str, speed: float):
        tmp_filename = ""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            tmp_filename = temp_file.name
            shutil.copyfile(filename, tmp_filename)
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                tmp_filename,
                "-filter:a",
                f"atempo={speed}",
                filename,
            ]
            FFmpeg()._run(command=cmd, fail=False)

        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)

    @staticmethod
    def is_ffmpeg_installed():
        cmd = ["ffprobe", "-version"]
        try:
            if (
                subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                ).returncode
                == 0
            ):
                return True
        except FileNotFoundError:
            return False
        return False
