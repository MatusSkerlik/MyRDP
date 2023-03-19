from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

import av


class AbstractEncoderStrategy(ABC):
    @abstractmethod
    def encode_frame(self, frame):
        pass


class MPEGTS_H264Encoder(AbstractEncoderStrategy):
    def __init__(self, width: int, height: int, fps: int) -> None:
        self._width = width
        self._height = height

        self._codec_name = "libx264"
        self._container_format = "mpegts"
        self._pix_fmt = "yuv420p"
        self._output_frame_rate = fps

        self._stream = av.open("tmp.mpegts", mode="w", format=self._container_format)
        self._video_stream = self._stream.add_stream(self._codec_name, self._output_frame_rate)
        self._video_stream.width = self._width
        self._video_stream.height = self._height
        self._video_stream.pix_fmt = self._pix_fmt

    def encode_frame(self, frame_data) -> bytes:
        print(self._video_stream)
        frame = av.VideoFrame.from_ndarray(frame_data, format="rgba")
        packets = []

        for packet in self._video_stream.encode(frame):
            packets.append(packet.to_bytes())

        return b''.join(packets)


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
            fps = self._options.get("fps", 30)
            return MPEGTS_H264Encoder(width, height, fps)

        # Add other strategy types here
        return None
