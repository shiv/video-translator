import dataclasses


@dataclasses.dataclass
class PreprocessingArtifacts:
    """Instance with preprocessing outputs.

    Attributes:
        video_file: A path to a video ad with no audio.
        audio_file: A path to an audio track from the ad.
    """

    video_file: str | None
    audio_file: str
