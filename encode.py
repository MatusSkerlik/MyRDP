from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, Union

import numpy as np


class AbstractEncoderStrategy(ABC):
    @abstractmethod
    def encode_frame(self, width: int, height: int, frame: bytes):
        pass


class DefaultEncoder(AbstractEncoderStrategy):
    def __init__(self, fps: int) -> None:
        self._fps = fps

        self._last_frame: Union[None, np.ndarray] = None

    def encode_frame(self, width: int, height: int, frame: bytes) -> bytes:
        nframe = np.frombuffer(frame, dtype=np.uint8)
        nframe.reshape((width, height, 3))
        return nframe.tobytes()


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
            fps = self._options.get("fps", 30)
            return DefaultEncoder(fps)

        # Add other strategy types here
        return None
