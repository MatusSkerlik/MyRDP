import time
from collections import deque


class FrameRateLimiter:
    """
    A simple class to sleep the thread based on the provided frames per second (FPS) value.

    Attributes:
        fps (float): The desired frames per second.
        _last_tick (float): The time at which the last tick occurred.
        _sleep_duration (float): The duration to sleep between ticks.
    """

    def __init__(self, fps: float) -> None:
        self._fps = fps
        self._last_tick = time.perf_counter()
        self._sleep_duration = 1 / self._fps

    def set_fps(self, fps: float) -> None:
        self._fps = fps
        self._sleep_duration = 1 / self._fps

    def tick(self) -> None:
        current_time = time.perf_counter()
        elapsed_time = current_time - self._last_tick

        if elapsed_time < self._sleep_duration:
            time.sleep(self._sleep_duration - elapsed_time)

        self._last_tick = time.perf_counter()


class FrameRateCalculator:
    """
    A class to calculate the frames per second (FPS) over a given time interval.

    Attributes:
        _frames (deque): A deque of tuples containing the timestamp and frame duration.
        _last_tick (float): The timestamp of the last tick.
        _interval (int): The time interval in seconds to calculate the FPS.
    """

    def __init__(self, interval=1):
        self._frames = deque()
        self._last_tick = None
        self._interval = interval

    def tick(self):
        current_time = time.time()
        if self._last_tick is not None:
            frame_duration = current_time - self._last_tick
            self._frames.append((current_time, frame_duration))
            self._remove_old_frames(current_time)
        self._last_tick = current_time

    def _remove_old_frames(self, current_time):
        interval_ago = current_time - self._interval
        while self._frames and self._frames[0][0] < interval_ago:
            self._frames.popleft()

    def get_fps(self):
        if not self._frames:
            return 0
        total_frames = len(self._frames)
        total_time = sum(frame[1] for frame in self._frames)
        mean_fps = total_frames / total_time
        return mean_fps
