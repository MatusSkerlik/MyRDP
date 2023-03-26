import time
from collections import deque


class FramesPerSecond:
    def __init__(self, interval=1):
        self.frames = deque()
        self.last_tick = None
        self._interval = interval

    def tick(self):
        current_time = time.time()
        if self.last_tick is not None:
            frame_duration = current_time - self.last_tick
            self.frames.append((current_time, frame_duration))
            self._remove_old_frames(current_time)
        self.last_tick = current_time

    def _remove_old_frames(self, current_time):
        one_minute_ago = current_time - self._interval
        while self.frames and self.frames[0][0] < one_minute_ago:
            self.frames.popleft()

    def get_fps(self):
        if not self.frames:
            return 0
        total_frames = len(self.frames)
        total_time = sum(frame[1] for frame in self.frames)
        mean_fps = total_frames / total_time
        return mean_fps
