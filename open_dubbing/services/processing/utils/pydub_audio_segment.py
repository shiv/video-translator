# Copyright © 2011 James Robert, http://jiaaro.com

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from __future__ import division

import array
import json
import os
import re
import struct
import subprocess
import sys
import wave

from collections import namedtuple
from io import BytesIO
from math import log
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile, TemporaryFile
from warnings import warn

try:
    import audioop
except ImportError:
    import pyaudioop as audioop

ARRAY_TYPES = {
    8: "b",
    16: "h",
    32: "i",
}


def get_array_type(bit_depth, signed=True):
    t = ARRAY_TYPES[bit_depth]
    if not signed:
        t = t.upper()
    return t


def _fd_or_path_or_tempfile(fd, mode="w+b", tempfile=True):
    close_fd = False
    if fd is None and tempfile:
        fd = TemporaryFile(mode=mode)
        close_fd = True

    if isinstance(fd, str):
        fd = open(fd, mode=mode)
        close_fd = True

    try:
        if isinstance(fd, os.PathLike):
            fd = open(fd, mode=mode)
            close_fd = True
    except AttributeError:
        # module os has no attribute PathLike, so we're on python < 3.6.
        # The protocol we're trying to support doesn't exist, so just pass.
        pass

    return fd, close_fd


def db_to_float(db, using_amplitude=True):
    """
    Converts the input db to a float, which represents the equivalent
    ratio in power.
    """
    db = float(db)
    if using_amplitude:
        return 10 ** (db / 20)
    else:  # using power
        return 10 ** (db / 10)


def ratio_to_db(ratio, val2=None, using_amplitude=True):
    """
    Converts the input float to db, which represents the equivalent
    to the ratio in power represented by the multiplier passed in.
    """
    ratio = float(ratio)

    # accept 2 values and use the ratio of val1 to val2
    if val2 is not None:
        ratio = ratio / val2

    # special case for multiply-by-zero (convert to silence)
    if ratio == 0:
        return -float("inf")

    if using_amplitude:
        return 20 * log(ratio, 10)
    else:  # using power
        return 10 * log(ratio, 10)


def which(program):
    """
    Mimics behavior of UNIX which command.
    """
    # Add .exe program extension for windows support
    if os.name == "nt" and not program.endswith(".exe"):
        program += ".exe"

    envdir_list = [os.curdir] + os.environ["PATH"].split(os.pathsep)

    for envdir in envdir_list:
        program_path = os.path.join(envdir, program)
        if os.path.isfile(program_path) and os.access(program_path, os.X_OK):
            return program_path


def get_encoder_name():
    """
    Return enconder default application for system, either avconv or ffmpeg
    """
    if which("avconv"):
        return "avconv"
    elif which("ffmpeg"):
        return "ffmpeg"
    else:
        # should raise exception
        warn(
            "Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work",
            RuntimeWarning,
        )
        return "ffmpeg"


def get_prober_name():
    """
    Return probe application, either avconv or ffmpeg
    """
    if which("avprobe"):
        return "avprobe"
    elif which("ffprobe"):
        return "ffprobe"
    else:
        # should raise exception
        warn(
            "Couldn't find ffprobe or avprobe - defaulting to ffprobe, but may not work",
            RuntimeWarning,
        )
        return "ffprobe"


def fsdecode(filename):
    """Wrapper for os.fsdecode which was introduced in python 3.2 ."""

    if sys.version_info >= (3, 2):
        PathLikeTypes = (str, bytes)
        if sys.version_info >= (3, 6):
            PathLikeTypes += (os.PathLike,)
        if isinstance(filename, PathLikeTypes):
            return os.fsdecode(filename)
    else:
        if isinstance(filename, bytes):
            return filename.decode(sys.getfilesystemencoding())
        if isinstance(filename, str):
            return filename

    raise TypeError("type {0} not accepted by fsdecode".format(type(filename)))


def get_extra_info(stderr):
    """
    avprobe sometimes gives more information on stderr than
    on the json output. The information has to be extracted
    from stderr of the format of:
    '    Stream #0:0: Audio: flac, 88200 Hz, stereo, s32 (24 bit)'
    or (macOS version):
    '    Stream #0:0: Audio: vorbis'
    '      44100 Hz, stereo, fltp, 320 kb/s'

    :type stderr: str
    :rtype: list of dict
    """
    extra_info = {}

    re_stream = r"(?P<space_start> +)Stream #0[:\.](?P<stream_id>([0-9]+))(?P<content_0>.+)\n?(?! *Stream)((?P<space_end> +)(?P<content_1>.+))?"
    for i in re.finditer(re_stream, stderr):
        if i.group("space_end") is not None and len(i.group("space_start")) <= len(
            i.group("space_end")
        ):
            content_line = ",".join([i.group("content_0"), i.group("content_1")])
        else:
            content_line = i.group("content_0")
        tokens = [x.strip() for x in re.split("[:,]", content_line) if x]
        extra_info[int(i.group("stream_id"))] = tokens
    return extra_info


def mediainfo_json(filepath, read_ahead_limit=-1):
    """Return json dictionary with media info(codec, duration, size, bitrate...) from filepath"""
    prober = get_prober_name()
    command_args = [
        "-v",
        "info",
        "-show_format",
        "-show_streams",
    ]
    try:
        command_args += [fsdecode(filepath)]
        stdin_parameter = None
        stdin_data = None
    except TypeError:
        if prober == "ffprobe":
            command_args += ["-read_ahead_limit", str(read_ahead_limit), "cache:pipe:0"]
        else:
            command_args += ["-"]
        stdin_parameter = PIPE
        file, close_file = _fd_or_path_or_tempfile(filepath, "rb", tempfile=False)
        file.seek(0)
        stdin_data = file.read()
        if close_file:
            file.close()

    command = [prober, "-of", "json"] + command_args
    res = Popen(command, stdin=stdin_parameter, stdout=PIPE, stderr=PIPE)
    output, stderr = res.communicate(input=stdin_data)
    output = output.decode("utf-8", "ignore")
    stderr = stderr.decode("utf-8", "ignore")

    info = json.loads(output)

    if not info:
        # If ffprobe didn't give any information, just return it
        # (for example, because the file doesn't exist)
        return info

    extra_info = get_extra_info(stderr)

    audio_streams = [x for x in info["streams"] if x["codec_type"] == "audio"]
    if len(audio_streams) == 0:
        return info

    # We just operate on the first audio stream in case there are more
    stream = audio_streams[0]

    def set_property(stream, prop, value):
        if prop not in stream or stream[prop] == 0:
            stream[prop] = value

    for token in extra_info[stream["index"]]:
        m = re.match(r"([su]([0-9]{1,2})p?) \(([0-9]{1,2}) bit\)$", token)
        m2 = re.match(r"([su]([0-9]{1,2})p?)( \(default\))?$", token)
        if m:
            set_property(stream, "sample_fmt", m.group(1))
            set_property(stream, "bits_per_sample", int(m.group(2)))
            set_property(stream, "bits_per_raw_sample", int(m.group(3)))
        elif m2:
            set_property(stream, "sample_fmt", m2.group(1))
            set_property(stream, "bits_per_sample", int(m2.group(2)))
            set_property(stream, "bits_per_raw_sample", int(m2.group(2)))
        elif re.match(r"(flt)p?( \(default\))?$", token):
            set_property(stream, "sample_fmt", token)
            set_property(stream, "bits_per_sample", 32)
            set_property(stream, "bits_per_raw_sample", 32)
        elif re.match(r"(dbl)p?( \(default\))?$", token):
            set_property(stream, "sample_fmt", token)
            set_property(stream, "bits_per_sample", 64)
            set_property(stream, "bits_per_raw_sample", 64)
    return info


class PydubException(Exception):
    """
    Base class for any Pydub exception
    """


class TooManyMissingFrames(PydubException):
    pass


class InvalidDuration(PydubException):
    pass


class InvalidTag(PydubException):
    pass


class InvalidID3TagVersion(PydubException):
    pass


class CouldntDecodeError(PydubException):
    pass


class CouldntEncodeError(PydubException):
    pass


class MissingAudioParameter(PydubException):
    pass


class ClassPropertyDescriptor(object):

    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.fget.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.fset:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.fset.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.fset = func
        return self


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassPropertyDescriptor(func)


AUDIO_FILE_EXT_ALIASES = {
    "m4a": "mp4",
    "wave": "wav",
}

WavSubChunk = namedtuple("WavSubChunk", ["id", "position", "size"])
WavData = namedtuple(
    "WavData",
    ["audio_format", "channels", "sample_rate", "bits_per_sample", "raw_data"],
)


def extract_wav_headers(data):
    # def search_subchunk(data, subchunk_id):
    pos = 12  # The size of the RIFF chunk descriptor
    subchunks = []
    while pos + 8 <= len(data) and len(subchunks) < 10:
        subchunk_id = data[pos : pos + 4]
        subchunk_size = struct.unpack_from("<I", data[pos + 4 : pos + 8])[0]
        subchunks.append(WavSubChunk(subchunk_id, pos, subchunk_size))
        if subchunk_id == b"data":
            # 'data' is the last subchunk
            break
        pos += subchunk_size + 8

    return subchunks


def read_wav_audio(data, headers=None):
    if not headers:
        headers = extract_wav_headers(data)

    fmt = [x for x in headers if x.id == b"fmt "]
    if not fmt or fmt[0].size < 16:
        raise CouldntDecodeError("Couldn't find fmt header in wav data")
    fmt = fmt[0]
    pos = fmt.position + 8
    audio_format = struct.unpack_from("<H", data[pos : pos + 2])[0]
    if audio_format != 1 and audio_format != 0xFFFE:
        raise CouldntDecodeError("Unknown audio format 0x%X in wav data" % audio_format)

    channels = struct.unpack_from("<H", data[pos + 2 : pos + 4])[0]
    sample_rate = struct.unpack_from("<I", data[pos + 4 : pos + 8])[0]
    bits_per_sample = struct.unpack_from("<H", data[pos + 14 : pos + 16])[0]

    data_hdr = headers[-1]
    if data_hdr.id != b"data":
        raise CouldntDecodeError("Couldn't find data header in wav data")

    pos = data_hdr.position + 8
    return WavData(
        audio_format,
        channels,
        sample_rate,
        bits_per_sample,
        data[pos : pos + data_hdr.size],
    )


def fix_wav_headers(data):
    headers = extract_wav_headers(data)
    if not headers or headers[-1].id != b"data":
        return

    # TODO: Handle huge files in some other way
    if len(data) > 2**32:
        raise CouldntDecodeError("Unable to process >4GB files")

    # Set the file size in the RIFF chunk descriptor
    data[4:8] = struct.pack("<I", len(data) - 8)

    # Set the data size in the data subchunk
    pos = headers[-1].position
    data[pos + 4 : pos + 8] = struct.pack("<I", len(data) - pos - 8)


class AudioSegment(object):
    """
    AudioSegments are *immutable* objects representing segments of audio
    that can be manipulated using python code.

    AudioSegments are slicable using milliseconds.
    for example:
        a = AudioSegment.from_mp3(mp3file)
        first_second = a[:1000] # get the first second of an mp3
        slice = a[5000:10000] # get a slice from 5 to 10 seconds of an mp3
    """

    converter = get_encoder_name()  # either ffmpeg or avconv

    # TODO: remove in 1.0 release
    # maintain backwards compatibility for ffmpeg attr (now called converter)
    @classproperty
    def ffmpeg(cls):
        return cls.converter

    @ffmpeg.setter
    def ffmpeg(cls, val):
        cls.converter = val

    DEFAULT_CODECS = {"ogg": "libvorbis"}

    def __init__(self, data=None, *args, **kwargs):
        self.sample_width = kwargs.pop("sample_width", None)
        self.frame_rate = kwargs.pop("frame_rate", None)
        self.channels = kwargs.pop("channels", None)

        audio_params = (self.sample_width, self.frame_rate, self.channels)

        if isinstance(data, array.array):
            try:
                data = data.tobytes()
            except:  # noqa: E722
                data = data.tostring()

        # prevent partial specification of arguments
        if any(audio_params) and None in audio_params:
            raise MissingAudioParameter(
                "Either all audio parameters or no parameter must be specified"
            )

        # all arguments are given
        elif self.sample_width is not None:
            if len(data) % (self.sample_width * self.channels) != 0:
                raise ValueError(
                    "data length must be a multiple of '(sample_width * channels)'"
                )

            self.frame_width = self.channels * self.sample_width
            self._data = data

        # keep support for 'metadata' until audio params are used everywhere
        elif kwargs.get("metadata", False):
            # internal use only
            self._data = data
            for attr, val in kwargs.pop("metadata").items():
                setattr(self, attr, val)
        else:
            # normal construction
            try:
                data = data if isinstance(data, (str, bytes)) else data.read()
            except OSError:
                d = b""
                reader = data.read(2**31 - 1)
                while reader:
                    d += reader
                    reader = data.read(2**31 - 1)
                data = d

            wav_data = read_wav_audio(data)
            if not wav_data:
                raise CouldntDecodeError("Couldn't read wav audio from data")

            self.channels = wav_data.channels
            self.sample_width = wav_data.bits_per_sample // 8
            self.frame_rate = wav_data.sample_rate
            self.frame_width = self.channels * self.sample_width
            self._data = wav_data.raw_data
            if self.sample_width == 1:
                # convert from unsigned integers in wav
                self._data = audioop.bias(self._data, 1, -128)

        # Convert 24-bit audio to 32-bit audio.
        # (stdlib audioop and array modules do not support 24-bit data)
        if self.sample_width == 3:
            byte_buffer = BytesIO()

            # Workaround for python 2 vs python 3. _data in 2.x are length-1 strings,
            # And in 3.x are ints.
            pack_fmt = "BBB" if isinstance(self._data[0], int) else "ccc"

            # This conversion maintains the 24 bit values.  The values are
            # not scaled up to the 32 bit range.  Other conversions could be
            # implemented.
            i = iter(self._data)
            padding = {False: b"\x00", True: b"\xFF"}
            for b0, b1, b2 in zip(i, i, i):
                byte_buffer.write(padding[b2 > b"\x7f"[0]])
                old_bytes = struct.pack(pack_fmt, b0, b1, b2)
                byte_buffer.write(old_bytes)

            self._data = byte_buffer.getvalue()
            self.sample_width = 4
            self.frame_width = self.channels * self.sample_width

        super(AudioSegment, self).__init__(*args, **kwargs)

    @property
    def raw_data(self):
        """
        public access to the raw audio data as a bytestring
        """
        return self._data

    def get_array_of_samples(self, array_type_override=None):
        """
        returns the raw_data as an array of samples
        """
        if array_type_override is None:
            array_type_override = self.array_type
        return array.array(array_type_override, self._data)

    @property
    def array_type(self):
        return get_array_type(self.sample_width * 8)

    def __len__(self):
        """
        returns the length of this audio segment in milliseconds
        """
        return round(1000 * (self.frame_count() / self.frame_rate))

    def __eq__(self, other):
        try:
            return self._data == other._data
        except:  # noqa: E722
            return False

    def __hash__(self):
        return hash(AudioSegment) ^ hash(
            (self.channels, self.frame_rate, self.sample_width, self._data)
        )

    def __ne__(self, other):
        return not (self == other)

    def __iter__(self):
        return (self[i] for i in range(len(self)))

    def __getitem__(self, millisecond):
        if isinstance(millisecond, slice):
            if millisecond.step:
                return (
                    self[i : i + millisecond.step]
                    for i in range(*millisecond.indices(len(self)))
                )

            start = millisecond.start if millisecond.start is not None else 0
            end = millisecond.stop if millisecond.stop is not None else len(self)

            start = min(start, len(self))
            end = min(end, len(self))
        else:
            start = millisecond
            end = millisecond + 1

        start = self._parse_position(start) * self.frame_width
        end = self._parse_position(end) * self.frame_width
        data = self._data[start:end]

        # ensure the output is as long as the requester is expecting
        expected_length = end - start
        missing_frames = (expected_length - len(data)) // self.frame_width
        if missing_frames:
            if missing_frames > self.frame_count(ms=2):
                raise TooManyMissingFrames(
                    "You should never be filling in "
                    "   more than 2 ms with silence here, "
                    "missing frames: %s" % missing_frames
                )
            silence = audioop.mul(data[: self.frame_width], self.sample_width, 0)
            data += silence * missing_frames

        return self._spawn(data)

    def __add__(self, arg):
        if isinstance(arg, AudioSegment):
            return self.append(arg, crossfade=0)
        else:
            return self.apply_gain(arg)

    def __sub__(self, arg):
        if isinstance(arg, AudioSegment):
            raise TypeError(
                "AudioSegment objects can't be subtracted from " "each other"
            )
        else:
            return self.apply_gain(-arg)

    def _spawn(self, data, overrides={}):
        """
        Creates a new audio segment using the metadata from the current one
        and the data passed in. Should be used whenever an AudioSegment is
        being returned by an operation that would alters the current one,
        since AudioSegment objects are immutable.
        """
        # accept lists of data chunks
        if isinstance(data, list):
            data = b"".join(data)

        if isinstance(data, array.array):
            try:
                data = data.tobytes()
            except:  # noqa: E722
                data = data.tostring()

        # accept file-like objects
        if hasattr(data, "read"):
            if hasattr(data, "seek"):
                data.seek(0)
            data = data.read()

        metadata = {
            "sample_width": self.sample_width,
            "frame_rate": self.frame_rate,
            "frame_width": self.frame_width,
            "channels": self.channels,
        }
        metadata.update(overrides)
        return self.__class__(data=data, metadata=metadata)

    @classmethod
    def _sync(cls, *segs):
        channels = max(seg.channels for seg in segs)
        frame_rate = max(seg.frame_rate for seg in segs)
        sample_width = max(seg.sample_width for seg in segs)

        return tuple(
            seg.set_channels(channels)
            .set_frame_rate(frame_rate)
            .set_sample_width(sample_width)
            for seg in segs
        )

    def _parse_position(self, val):
        if val < 0:
            val = len(self) - abs(val)
        val = (
            self.frame_count(ms=len(self))
            if val == float("inf")
            else self.frame_count(ms=val)
        )
        return int(val)

    @classmethod
    def silent(cls, duration=1000, frame_rate=11025):
        """
        Generate a silent audio segment.
        duration specified in milliseconds (default duration: 1000ms, default frame_rate: 11025).
        """
        frames = int(frame_rate * (duration / 1000.0))
        data = b"\0\0" * frames
        return cls(
            data,
            metadata={
                "channels": 1,
                "sample_width": 2,
                "frame_rate": frame_rate,
                "frame_width": 2,
            },
        )

    @classmethod
    def from_mono_audiosegments(cls, *mono_segments):
        if not len(mono_segments):
            raise ValueError("At least one AudioSegment instance is required")

        segs = cls._sync(*mono_segments)

        if segs[0].channels != 1:
            raise ValueError(
                "AudioSegment.from_mono_audiosegments requires all arguments are mono AudioSegment instances"
            )

        channels = len(segs)
        sample_width = segs[0].sample_width
        frame_rate = segs[0].frame_rate

        frame_count = max(int(seg.frame_count()) for seg in segs)
        data = array.array(
            segs[0].array_type, b"\0" * (frame_count * sample_width * channels)
        )

        for i, seg in enumerate(segs):
            data[i::channels] = seg.get_array_of_samples()

        return cls(
            data,
            channels=channels,
            sample_width=sample_width,
            frame_rate=frame_rate,
        )

    @classmethod
    def from_file(
        cls,
        file,
        format=None,
        codec=None,
        parameters=None,
        start_second=None,
        duration=None,
        **kwargs
    ):
        orig_file = file
        try:
            filename = fsdecode(file)
        except TypeError:
            filename = None
        file, close_file = _fd_or_path_or_tempfile(file, "rb", tempfile=False)

        if format:
            format = format.lower()
            format = AUDIO_FILE_EXT_ALIASES.get(format, format)

        def is_format(f):
            f = f.lower()
            if format == f:
                return True

            if filename:
                return filename.lower().endswith(".{0}".format(f))

            return False

        if is_format("wav"):
            try:
                if start_second is None and duration is None:
                    return cls._from_safe_wav(file)
                elif start_second is not None and duration is None:
                    return cls._from_safe_wav(file)[start_second * 1000 :]
                elif start_second is None and duration is not None:
                    return cls._from_safe_wav(file)[: duration * 1000]
                else:
                    return cls._from_safe_wav(file)[
                        start_second * 1000 : (start_second + duration) * 1000
                    ]
            except:  # noqa: E722
                file.seek(0)
        elif is_format("raw") or is_format("pcm"):
            sample_width = kwargs["sample_width"]
            frame_rate = kwargs["frame_rate"]
            channels = kwargs["channels"]
            metadata = {
                "sample_width": sample_width,
                "frame_rate": frame_rate,
                "channels": channels,
                "frame_width": channels * sample_width,
            }
            if start_second is None and duration is None:
                return cls(data=file.read(), metadata=metadata)
            elif start_second is not None and duration is None:
                return cls(data=file.read(), metadata=metadata)[start_second * 1000 :]
            elif start_second is None and duration is not None:
                return cls(data=file.read(), metadata=metadata)[: duration * 1000]
            else:
                return cls(data=file.read(), metadata=metadata)[
                    start_second * 1000 : (start_second + duration) * 1000
                ]

        conversion_command = [
            cls.converter,
            "-y",  # always overwrite existing files
        ]

        # If format is not defined
        # ffmpeg/avconv will detect it automatically
        if format:
            conversion_command += ["-f", format]

        if codec:
            # force audio decoder
            conversion_command += ["-acodec", codec]

        read_ahead_limit = kwargs.get("read_ahead_limit", -1)
        if filename:
            conversion_command += ["-i", filename]
            stdin_parameter = None
            stdin_data = None
        else:
            if cls.converter == "ffmpeg":
                conversion_command += [
                    "-read_ahead_limit",
                    str(read_ahead_limit),
                    "-i",
                    "cache:pipe:0",
                ]
            else:
                conversion_command += ["-i", "-"]
            stdin_parameter = subprocess.PIPE
            stdin_data = file.read()

        if codec:
            info = None
        else:
            info = mediainfo_json(orig_file, read_ahead_limit=read_ahead_limit)
        if info:
            audio_streams = [x for x in info["streams"] if x["codec_type"] == "audio"]
            # This is a workaround for some ffprobe versions that always say
            # that mp3/mp4/aac/webm/ogg files contain fltp samples
            audio_codec = audio_streams[0].get("codec_name")
            if audio_streams[0].get("sample_fmt") == "fltp" and audio_codec in [
                "mp3",
                "mp4",
                "aac",
                "webm",
                "ogg",
            ]:
                bits_per_sample = 16
            else:
                bits_per_sample = audio_streams[0]["bits_per_sample"]
            if bits_per_sample == 8:
                acodec = "pcm_u8"
            else:
                acodec = "pcm_s%dle" % bits_per_sample

            conversion_command += ["-acodec", acodec]

        conversion_command += [
            "-vn",  # Drop any video streams if there are any
            "-f",
            "wav",  # output options (filename last)
        ]

        if start_second is not None:
            conversion_command += ["-ss", str(start_second)]

        if duration is not None:
            conversion_command += ["-t", str(duration)]

        conversion_command += ["-"]

        if parameters is not None:
            # extend arguments with arbitrary set
            conversion_command.extend(parameters)

        #        log_conversion(conversion_command)

        p = subprocess.Popen(
            conversion_command,
            stdin=stdin_parameter,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p_out, p_err = p.communicate(input=stdin_data)

        if p.returncode != 0 or len(p_out) == 0:
            if close_file:
                file.close()
            raise CouldntDecodeError(
                "Decoding failed. ffmpeg returned error code: {0}\n\nOutput from ffmpeg/avlib:\n\n{1}".format(
                    p.returncode, p_err.decode(errors="ignore")
                )
            )

        p_out = bytearray(p_out)
        fix_wav_headers(p_out)
        p_out = bytes(p_out)
        obj = cls(p_out)

        if close_file:
            file.close()

        if start_second is None and duration is None:
            return obj
        elif start_second is not None and duration is None:
            return obj[0:]
        elif start_second is None and duration is not None:
            return obj[: duration * 1000]
        else:
            return obj[0 : duration * 1000]

    @classmethod
    def from_mp3(cls, file, parameters=None):
        return cls.from_file(file, "mp3", parameters=parameters)

    def export(
        self,
        out_f=None,
        format="mp3",
        codec=None,
        bitrate=None,
        parameters=None,
        tags=None,
        id3v2_version="4",
        cover=None,
    ):
        """
        Export an AudioSegment to a file with given options

        out_f (string):
            Path to destination audio file. Also accepts os.PathLike objects on
            python >= 3.6

        format (string)
            Format for destination audio file.
            ('mp3', 'wav', 'raw', 'ogg' or other ffmpeg/avconv supported files)

        codec (string)
            Codec used to encode the destination file.

        bitrate (string)
            Bitrate used when encoding destination file. (64, 92, 128, 256, 312k...)
            Each codec accepts different bitrate arguments so take a look at the
            ffmpeg documentation for details (bitrate usually shown as -b, -ba or
            -a:b).

        parameters (list of strings)
            Aditional ffmpeg/avconv parameters

        tags (dict)
            Set metadata information to destination files
            usually used as tags. ({title='Song Title', artist='Song Artist'})

        id3v2_version (string)
            Set ID3v2 version for tags. (default: '4')

        cover (file)
            Set cover for audio file from image file. (png or jpg)
        """
        id3v2_allowed_versions = ["3", "4"]

        if format == "raw" and (codec is not None or parameters is not None):
            raise AttributeError(
                'Can not invoke ffmpeg when export format is "raw"; '
                'specify an ffmpeg raw format like format="s16le" instead '
                'or call export(format="raw") with no codec or parameters'
            )

        out_f, _ = _fd_or_path_or_tempfile(out_f, "wb+")
        out_f.seek(0)

        if format == "raw":
            out_f.write(self._data)
            out_f.seek(0)
            return out_f

        # wav with no ffmpeg parameters can just be written directly to out_f
        easy_wav = format == "wav" and codec is None and parameters is None

        if easy_wav:
            data = out_f
        else:
            data = NamedTemporaryFile(mode="wb", delete=False)

        pcm_for_wav = self._data
        if self.sample_width == 1:
            # convert to unsigned integers for wav
            pcm_for_wav = audioop.bias(self._data, 1, 128)

        wave_data = wave.open(data, "wb")
        wave_data.setnchannels(self.channels)
        wave_data.setsampwidth(self.sample_width)
        wave_data.setframerate(self.frame_rate)
        # For some reason packing the wave header struct with
        # a float in python 2 doesn't throw an exception
        wave_data.setnframes(int(self.frame_count()))
        wave_data.writeframesraw(pcm_for_wav)
        wave_data.close()

        # for easy wav files, we're done (wav data is written directly to out_f)
        if easy_wav:
            out_f.seek(0)
            return out_f

        output = NamedTemporaryFile(mode="w+b", delete=False)

        # build converter command to export
        conversion_command = [
            self.converter,
            "-y",  # always overwrite existing files
            "-f",
            "wav",
            "-i",
            data.name,  # input options (filename last)
        ]

        if codec is None:
            codec = self.DEFAULT_CODECS.get(format, None)

        if cover is not None:
            if (
                cover.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
                )
                and format == "mp3"
            ):
                conversion_command.extend(
                    ["-i", cover, "-map", "0", "-map", "1", "-c:v", "mjpeg"]
                )
            else:
                raise AttributeError(
                    "Currently cover images are only supported by MP3 files. The allowed image formats are: .tif, .jpg, .bmp, .jpeg and .png."
                )

        if codec is not None:
            # force audio encoder
            conversion_command.extend(["-acodec", codec])

        if bitrate is not None:
            conversion_command.extend(["-b:a", bitrate])

        if parameters is not None:
            # extend arguments with arbitrary set
            conversion_command.extend(parameters)

        if tags is not None:
            if not isinstance(tags, dict):
                raise InvalidTag("Tags must be a dictionary.")
            else:
                # Extend converter command with tags
                # print(tags)
                for key, value in tags.items():
                    conversion_command.extend(
                        ["-metadata", "{0}={1}".format(key, value)]
                    )

                if format == "mp3":
                    # set id3v2 tag version
                    if id3v2_version not in id3v2_allowed_versions:
                        raise InvalidID3TagVersion(
                            "id3v2_version not allowed, allowed versions: %s"
                            % id3v2_allowed_versions
                        )
                    conversion_command.extend(["-id3v2_version", id3v2_version])

        if sys.platform == "darwin" and codec == "mp3":
            conversion_command.extend(["-write_xing", "0"])

        conversion_command.extend(
            [
                "-f",
                format,
                output.name,  # output options (filename last)
            ]
        )

        # read stdin / write stdout
        with open(os.devnull, "rb") as devnull:
            p = subprocess.Popen(
                conversion_command,
                stdin=devnull,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        p_out, p_err = p.communicate()

        if p.returncode != 0:
            raise CouldntEncodeError(
                "Encoding failed. ffmpeg/avlib returned error code: {0}\n\nCommand:{1}\n\nOutput from ffmpeg/avlib:\n\n{2}".format(
                    p.returncode, conversion_command, p_err.decode(errors="ignore")
                )
            )

        output.seek(0)
        out_f.write(output.read())

        data.close()
        output.close()

        os.unlink(data.name)
        os.unlink(output.name)

        out_f.seek(0)
        return out_f

    def frame_count(self, ms=None):
        """
        returns the number of frames for the given number of milliseconds, or
            if not specified, the number of frames in the whole AudioSegment
        """
        if ms is not None:
            return ms * (self.frame_rate / 1000.0)
        else:
            return float(len(self._data) // self.frame_width)

    def set_sample_width(self, sample_width):
        if sample_width == self.sample_width:
            return self

        frame_width = self.channels * sample_width

        return self._spawn(
            audioop.lin2lin(self._data, self.sample_width, sample_width),
            overrides={"sample_width": sample_width, "frame_width": frame_width},
        )

    def set_frame_rate(self, frame_rate):
        if frame_rate == self.frame_rate:
            return self

        if self._data:
            converted, _ = audioop.ratecv(
                self._data,
                self.sample_width,
                self.channels,
                self.frame_rate,
                frame_rate,
                None,
            )
        else:
            converted = self._data

        return self._spawn(data=converted, overrides={"frame_rate": frame_rate})

    def set_channels(self, channels):
        if channels == self.channels:
            return self

        if channels == 2 and self.channels == 1:
            fn = audioop.tostereo
            frame_width = self.frame_width * 2
            fac = 1
            converted = fn(self._data, self.sample_width, fac, fac)
        elif channels == 1 and self.channels == 2:
            fn = audioop.tomono
            frame_width = self.frame_width // 2
            fac = 0.5
            converted = fn(self._data, self.sample_width, fac, fac)
        elif channels == 1:
            channels_data = [seg.get_array_of_samples() for seg in self.split_to_mono()]
            frame_count = int(self.frame_count())
            converted = array.array(
                channels_data[0].typecode, b"\0" * (frame_count * self.sample_width)
            )
            for raw_channel_data in channels_data:
                for i in range(frame_count):
                    converted[i] += raw_channel_data[i] // self.channels
            frame_width = self.frame_width // self.channels
        elif self.channels == 1:
            dup_channels = [self for iChannel in range(channels)]
            return AudioSegment.from_mono_audiosegments(*dup_channels)
        else:
            raise ValueError(
                "AudioSegment.set_channels only supports mono-to-multi channel and multi-to-mono channel conversion"
            )

        return self._spawn(
            data=converted, overrides={"channels": channels, "frame_width": frame_width}
        )

    def split_to_mono(self):
        if self.channels == 1:
            return [self]

        samples = self.get_array_of_samples()

        mono_channels = []
        for i in range(self.channels):
            samples_for_current_channel = samples[i :: self.channels]

            try:
                mono_data = samples_for_current_channel.tobytes()
            except AttributeError:
                mono_data = samples_for_current_channel.tostring()

            mono_channels.append(
                self._spawn(
                    mono_data,
                    overrides={"channels": 1, "frame_width": self.sample_width},
                )
            )

        return mono_channels

    @property
    def max(self):
        return audioop.max(self._data, self.sample_width)

    @property
    def max_possible_amplitude(self):
        bits = self.sample_width * 8
        max_possible_val = 2**bits
        # since half is above 0 and half is below the max amplitude is divided
        return max_possible_val / 2

    @property
    def duration_seconds(self):
        return self.frame_rate and self.frame_count() / self.frame_rate or 0.0

    def remove_dc_offset(self, channel=None, offset=None):
        """
        Removes DC offset of given channel. Calculates offset if it's not given.
        Offset values must be in range -1.0 to 1.0. If channel is None, removes
        DC offset from all available channels.
        """
        if channel and not 1 <= channel <= 2:
            raise ValueError("channel value must be None, 1 (left) or 2 (right)")

        if offset and not -1.0 <= offset <= 1.0:
            raise ValueError("offset value must be in range -1.0 to 1.0")

        if offset:
            offset = int(round(offset * self.max_possible_amplitude))

        def remove_data_dc(data, off):
            if not off:
                off = audioop.avg(data, self.sample_width)
            return audioop.bias(data, self.sample_width, -off)

        if self.channels == 1:
            return self._spawn(data=remove_data_dc(self._data, offset))

        left_channel = audioop.tomono(self._data, self.sample_width, 1, 0)
        right_channel = audioop.tomono(self._data, self.sample_width, 0, 1)

        if not channel or channel == 1:
            left_channel = remove_data_dc(left_channel, offset)

        if not channel or channel == 2:
            right_channel = remove_data_dc(right_channel, offset)

        left_channel = audioop.tostereo(left_channel, self.sample_width, 1, 0)
        right_channel = audioop.tostereo(right_channel, self.sample_width, 0, 1)

        return self._spawn(
            data=audioop.add(left_channel, right_channel, self.sample_width)
        )

    def apply_gain(self, volume_change):
        return self._spawn(
            data=audioop.mul(
                self._data, self.sample_width, db_to_float(float(volume_change))
            )
        )

    def overlay(
        self, seg, position=0, loop=False, times=None, gain_during_overlay=None
    ):
        """
        Overlay the provided segment on to this segment starting at the
        specificed position and using the specfied looping beahvior.

        seg (AudioSegment):
            The audio segment to overlay on to this one.

        position (optional int):
            The position to start overlaying the provided segment in to this
            one.

        loop (optional bool):
            Loop seg as many times as necessary to match this segment's length.
            Overrides loops param.

        times (optional int):
            Loop seg the specified number of times or until it matches this
            segment's length. 1 means once, 2 means twice, ... 0 would make the
            call a no-op
        gain_during_overlay (optional int):
            Changes this segment's volume by the specified amount during the
            duration of time that seg is overlaid on top of it. When negative,
            this has the effect of 'ducking' the audio under the overlay.
        """

        if loop:
            # match loop=True's behavior with new times (count) mechinism.
            times = -1
        elif times is None:
            # no times specified, just once through
            times = 1
        elif times == 0:
            # it's a no-op, make a copy since we never mutate
            return self._spawn(self._data)

        output = BytesIO()

        seg1, seg2 = AudioSegment._sync(self, seg)
        sample_width = seg1.sample_width
        spawn = seg1._spawn

        output.write(seg1[:position]._data)

        # drop down to the raw data
        seg1 = seg1[position:]._data
        seg2 = seg2._data
        pos = 0
        seg1_len = len(seg1)
        seg2_len = len(seg2)
        while times:
            remaining = max(0, seg1_len - pos)
            if seg2_len >= remaining:
                seg2 = seg2[:remaining]
                seg2_len = remaining
                # we've hit the end, we're done looping (if we were) and this
                # is our last go-around
                times = 1

            if gain_during_overlay:
                seg1_overlaid = seg1[pos : pos + seg2_len]
                seg1_adjusted_gain = audioop.mul(
                    seg1_overlaid,
                    self.sample_width,
                    db_to_float(float(gain_during_overlay)),
                )
                output.write(audioop.add(seg1_adjusted_gain, seg2, sample_width))
            else:
                output.write(
                    audioop.add(seg1[pos : pos + seg2_len], seg2, sample_width)
                )
            pos += seg2_len

            # dec times to break our while loop (eventually)
            times -= 1

        output.write(seg1[pos:])

        return spawn(data=output)

    def normalize(seg, headroom=0.1):
        """
        headroom is how close to the maximum volume to boost the signal up to (specified in dB)
        """
        peak_sample_val = seg.max

        # if the max is 0, this audio segment is silent, and can't be normalized
        if peak_sample_val == 0:
            return seg

        target_peak = seg.max_possible_amplitude * db_to_float(-headroom)

        needed_boost = ratio_to_db(target_peak / peak_sample_val)
        return seg.apply_gain(needed_boost)
