from abc import ABC, abstractmethod
from typing import List


class AbstractDecoderStrategy(ABC):
    @abstractmethod
    def decode_packet(self, packet_data) -> List[bytes]:
        pass


class DefaultDecoder(AbstractDecoderStrategy):
    def decode_packet(self, packet_data: bytes) -> List[bytes]:
        return [packet_data]
