from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

import av


class AbstractEncoderStrategy(ABC):
    @abstractmethod
    def encode_frame(self, frame):
        pass


class PyAvH264Encoder(AbstractEncoderStrategy):
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.codec_name = "libx264"
        self.container_format = "mp4"
        self.output_frame_rate = 30
        self.pix_fmt = "yuv420p"

        self.stream = av.open(None, "w", format=self.container_format)
        self.video_stream = self.stream.add_stream(self.codec_name, self.output_frame_rate)
        self.video_stream.width = self.width
        self.video_stream.height = self.height
        self.video_stream.pix_fmt = self.pix_fmt

    def encode_frame(self, frame_data) -> bytes:
        frame = av.VideoFrame.from_ndarray(frame_data, format=self.pix_fmt)
        return self.video_stream.encode(frame)


class EncoderStrategyBuilder:
    """
    A builder class for creating EncoderStrategy objects.

    This builder class allows you to easily create EncoderStrategy objects by
    specifying the strategy type and any options needed for the strategy.

    Example:
        builder = EncoderStrategyBuilder()
        encoder_strategy = (builder.set_strategy_type("av")
                                  .set_option("width", 1280)
                                  .set_option("height", 720)
                                  .build())
    """

    def __init__(self) -> None:
        self._strategy_type: Optional[str] = None
        self._options: Dict[str, Any] = {}

    def set_strategy_type(self, strategy_type: str) -> "EncoderStrategyBuilder":
        self._strategy_type = strategy_type
        return self

    def set_option(self, key: str, value: Any) -> "EncoderStrategyBuilder":
        self._options[key] = value
        return self

    def build(self) -> Optional[AbstractEncoderStrategy]:
        if not self._strategy_type:
            return None

        if self._strategy_type.lower() == "av":
            width = self._options.get("width", 640)
            height = self._options.get("height", 480)
            return PyAvH264Encoder(width, height)

        # Add other strategy types here
        return None
