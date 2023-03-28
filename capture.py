from abc import ABC, abstractmethod
from typing import Optional, Any, Dict

from mss import mss

from fps import FrameRateLimiter


class AbstractCaptureStrategy(ABC):
    @abstractmethod
    def capture_screen(self) -> bytes:
        pass

    @abstractmethod
    def get_monitor_width(self) -> int:
        pass

    @abstractmethod
    def get_monitor_height(self) -> int:
        pass


class MSSCaptureStrategy(AbstractCaptureStrategy):
    """
    A screen capture strategy that uses the MSS library to capture the screen of the first
    monitor.

    Attributes:
        _sct (mss.mss): The MSS object used for screen capturing.
    """

    def __init__(self, fps: int):
        self._frame_rate_limiter = FrameRateLimiter(fps)
        self._sct = mss()

    def get_monitor_width(self) -> int:
        return self._sct.monitors[1].get("width")

    def get_monitor_height(self) -> int:
        return self._sct.monitors[1].get("height")

    def capture_screen(self) -> bytes:
        # sleep for the required time to match fps
        self._frame_rate_limiter.tick()

        # Get the dimensions of the first monitor
        monitor = self._sct.monitors[1]

        # Capture the screen
        screen_shot = self._sct.grab(monitor)

        # Convert the resized image to a bytes and return
        return screen_shot.rgb


class CaptureStrategyBuilder:
    """
    A builder class for creating CaptureStrategy objects.

    This builder class allows you to easily create CaptureStrategy objects by
    specifying the strategy type and any options needed for the strategy.

    Example:
        builder = CaptureStrategyBuilder()
        capture_strategy = (builder.set_strategy_type("mss")
                                  .set_option("fps", 30)
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
            fps = self._options.get("fps", 30)
            return MSSCaptureStrategy(fps)

        # Add other strategy types here
        raise NotImplementedError
