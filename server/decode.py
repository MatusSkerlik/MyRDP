from abc import ABC, abstractmethod
from typing import List, Any

import av
import numpy as np


class AbstractDecoderStrategy(ABC):
    @abstractmethod
    def decode_packet(self, packet_data) -> List[np.ndarray]:
        pass


class PyAvH264Decoder(AbstractDecoderStrategy):
    def __init__(self):
        self.pix_fmt = "yuv420p"
        self.container_format = "mp4"

        self.stream = av.open(None, "r", format=self.container_format)
        self.video_stream = self._find_video_stream()

    def _find_video_stream(self):
        for stream in self.stream.streams:
            if stream.type == 'video':
                return stream
        raise ValueError("No video stream found in the input data")

    def decode_packet(self, packet_data: bytearray) -> List[Any]:
        packet = av.Packet(packet_data)
        packet.stream = self.video_stream

        frames = []
        for frame in self.video_stream.decode(packet):
            frames.append(frame.to_ndarray(format=self.pix_fmt))

        return frames
