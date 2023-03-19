import io
from abc import ABC, abstractmethod
from typing import List

import av
import numpy as np


class AbstractDecoderStrategy(ABC):
    @abstractmethod
    def decode_packet(self, packet_data) -> List[np.ndarray]:
        pass


class MPEGTS_H264Decoder(AbstractDecoderStrategy):
    def __init__(self):
        self._buffer = io.BytesIO()
        self._container_format = "mpegts"
        self._pix_fmt = "yuv420p"
        self._stream = None
        self._video_stream = None

    def decode_packet(self, packet_data):
        self._buffer.write(packet_data)

        if not self._stream:
            self._stream = av.open(self._buffer, "r", format=self._container_format)

        if not self._video_stream:
            self._video_stream = next((s for s in self._stream.streams if s.type == "video"), None)

        decoded_frames = []
        if self._video_stream:
            packet = av.Packet.from_bytes(packet_data)
            packet._stream = self._video_stream

            for frame in self._video_stream.decode(packet):
                decoded_frames.append(frame.to_ndarray(format=self._pix_fmt))

        return decoded_frames
