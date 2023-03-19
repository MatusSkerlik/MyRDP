import time


class FrameTimer:
    """
    A simple class to sleep the thread based on the provided frames per second (FPS) value.

    Attributes:
        fps (float): The desired frames per second.
        last_tick_time (float): The time at which the last tick occurred.
        sleep_duration (float): The duration to sleep between ticks.
    """

    def __init__(self, fps: float) -> None:
        self.fps = fps
        self.last_tick_time = time.perf_counter()
        self.sleep_duration = 1 / self.fps

    def set_fps(self, fps: float) -> None:
        self.fps = fps
        self.sleep_duration = 1 / self.fps

    def tick(self) -> None:
        current_time = time.perf_counter()
        elapsed_time = current_time - self.last_tick_time

        if elapsed_time < self.sleep_duration:
            time.sleep(self.sleep_duration - elapsed_time)

        self.last_tick_time = time.perf_counter()
