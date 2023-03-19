from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

import cv2
import numpy as np
from mss import mss

from client.timer import FrameTimer


class AbstractCaptureStrategy(ABC):
    @abstractmethod
    def capture_screen(self) -> bytes:
        pass


class MSSCaptureStrategy(AbstractCaptureStrategy):
    """
    A screen capture strategy that uses the MSS library to capture the screen of the first
    monitor and resizes the captured image according to the specified dimensions.

    Attributes:
        width (int): The target width of the resized image.
        height (int): The target height of the resized image.
        sct (mss.mss): The MSS object used for screen capturing.
    """

    def __init__(self, width: int, height: int, fps: int):
        self.width = width
        self.height = height

        self.fps = fps
        self.frame_timer = FrameTimer(fps)

        self.sct = mss()

    def capture_screen(self) -> bytes:
        # sleep for the required time to match fps
        self.frame_timer.tick()

        # Get the dimensions of the first monitor
        monitor = self.sct.monitors[1]

        # Capture the screen
        sct_img = self.sct.grab(monitor)

        # Convert the captured image to a numpy array
        img_np = np.array(sct_img)

        # Resize the image
        resized_img = cv2.resize(img_np, (self.width, self.height))

        # Convert the resized image to a bytearray and return
        return bytearray(resized_img)


class CaptureStrategyBuilder:
    """
    A builder class for creating CaptureStrategy objects.

    This builder class allows you to easily create CaptureStrategy objects by
    specifying the strategy type and any options needed for the strategy.

    Example:
        builder = CaptureStrategyBuilder()
        capture_strategy = (builder.set_strategy_type("mss")
                                  .set_option("width", 1280)
                                  .set_option("height", 720)
                                  .build())
    """

    def __init__(self) -> None:
        self._strategy_type: Optional[str] = None
        self._options: Dict[str, Any] = {}

    def set_strategy_type(self, strategy_type: str) -> "CaptureStrategyBuilder":
        self._strategy_type = strategy_type
        return self

    def set_option(self, key: str, value: Any) -> "CaptureStrategyBuilder":
        self._options[key] = value
        return self

    def build(self) -> Optional[AbstractCaptureStrategy]:
        if not self._strategy_type:
            return None

        if self._strategy_type.lower() == "mss":
            width = self._options.get("width", 640)
            height = self._options.get("height", 480)
            return MSSCaptureStrategy(width, height)

        # Add other strategy types here
        return None
