import cv2
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional, Any, Dict, Union

from pfactory import VideoFrameDataPacketFactory


class AbstractEncoderStrategy(ABC):
    ID: int

    @abstractmethod
    def encode_frame(self, width: int, height: int, frame: bytes):
        pass


class DefaultEncoder(AbstractEncoderStrategy):
    ID = 0x01

    class FrameType(IntEnum):
        FULL_FRAME = 0x01
        DIFF_FRAME = 0x02

    def __init__(self) -> None:
        self._last_frame: Union[None, cv2.UMat] = None
        self._frame_count = 0

    def __str__(self):
        return f"DefaultEncoder()"

    def encode_frame(self, width: int, height: int, frame: bytes) -> bytes:
        packet = VideoFrameDataPacketFactory.create_packet(DefaultEncoder.ID,
                                                           DefaultEncoder.FrameType.FULL_FRAME,
                                                           frame)
        return packet.get_bytes()


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

        if self._strategy_type.lower() == "default":
            return DefaultEncoder()

        # Add other strategy types here
        return None
