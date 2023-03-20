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
        self._container = av.open(self._buffer, "r", format=self._container_format)

    def decode_packet(self, packet_data):
        self._buffer.write(packet_data)

        decoded_frames = []
        for packet in self._container.demux():
            # You can access the stream that the packet belongs to
            stream = packet.stream

            # For example, if you want to work with video packets only, you can do the following
            if stream.type == "video":
                # Decode the packet into frames
                for frame in stream.decode(packet):
                    # Process the frame (e.g., display, save, or manipulate)
                    decoded_frames.append(frame.to_ndarray(format=self._pix_fmt))
        return decoded_frames
