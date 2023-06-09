import time
from collections import deque


class BandwidthMonitor:
    """
    A class to monitor the bandwidth of a data using a moving median window.
    Attributes:
        window_size (int): The size of the moving median window in seconds.
        _bytes_received (deque): A deque to store the number of bytes received.
        _timestamps (deque): A deque to store the timestamps of received bytes.
    """

    def __init__(self, window_size: int = 60) -> None:
        self._window_size = window_size
        self._bytes_received = deque()
        self._timestamps = deque()

    def reset(self):
        self._bytes_received.clear()
        self._timestamps.clear()

    def register_received_bytes(self, received_bytes: int) -> None:
        current_time = time.time()
        self._bytes_received.append(received_bytes)
        self._timestamps.append(current_time)

        while len(self._timestamps) > 0 and current_time - self._timestamps[0] > self._window_size:
            self._timestamps.popleft()
            self._bytes_received.popleft()

    def get_bandwidth(self) -> int:
        elapsed_time = self._timestamps[-1] - self._timestamps[0] if len(self._timestamps) > 1 else 1
        total_bytes_received = sum(self._bytes_received)
        return int(total_bytes_received / elapsed_time)

    def get_bandwidth_str(self):
        return BandwidthFormatter.format(self.get_bandwidth())


class BandwidthFormatter:
    @staticmethod
    def format(bandwidth: int):
        if bandwidth < 1000:
            return f"{bandwidth} Bps"
        elif bandwidth < 1000 * 1000:
            return f"{bandwidth / 1000:.0f} Kbps"
        elif bandwidth < 1000 * 1000 * 1000:
            return f"{bandwidth / (1000 * 1000):.0f} Mbps"
        else:
            return f"{bandwidth / (1000 * 1000 * 1000):.0f} Gbps"
