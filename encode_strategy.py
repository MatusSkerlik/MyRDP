import io
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional, Any, Dict, Union

import cv2
from PIL import Image

from pfactory import VideoFrameDataPacketFactory


class AbstractEncoderStrategy(ABC):
    ID: int

    @abstractmethod
    def encode_frame(self, width: int, height: int, screenshot: Any):
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

    def encode_frame(self, target_width: int, target_height: int, screenshot: Any) -> bytes:
        p_image = Image.frombytes("RGB", screenshot.size, screenshot.b_array)

        if screenshot.width != target_width or screenshot.height != target_height:
            # Resize the image
            original_width, original_height = screenshot.size
            aspect_ratio = original_width / original_height

            # Calculate the new dimensions to fit the target resolution
            if original_width / target_width > original_height / target_height:
                new_width = target_width
                new_height = int(target_width / aspect_ratio)
            else:
                new_height = target_height
                new_width = int(target_height * aspect_ratio)

            p_image = p_image.resize((new_width, new_height), Image.NEAREST)

        # Convert 32-bit image to 16-bit image
        # p_image = p_image.convert("P", palette=Palette.ADAPTIVE, colors=256)

        buffer = io.BytesIO()
        p_image.save(buffer, "jpeg", quality=90)
        p_image.close()

        # Convert to jpeg for compression
        packet = VideoFrameDataPacketFactory.create_packet(DefaultEncoder.ID,
                                                           DefaultEncoder.FrameType.FULL_FRAME,
                                                           buffer.getvalue())
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
