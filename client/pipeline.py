import threading
from abc import ABC, abstractmethod
from queue import Queue
from socket import socket
from typing import Any

from capture import AbstractCaptureStrategy
from endoding import AbstractEncoderStrategy
from lock import AutoLockingValue
from packet import Packet
from pfactory import VideoDataPacketFactory


class Component(ABC):
    def __init__(self):
        self._running = AutoLockingValue(True)

    def is_running(self):
        return self._running.get()

    @abstractmethod
    def run(self) -> None:
        pass

    def stop(self):
        self._running.set(False)


class CaptureComponent(Component):
    def __init__(self, capture_strategy: AbstractCaptureStrategy):
        super().__init__()
        self.output_queue = Queue()
        self._capture_strategy = AutoLockingValue(capture_strategy)
        self._thread = threading.Thread(target=self.run)
        self._thread.start()

    def set_capture_strategy(self, capture_strategy: AbstractCaptureStrategy):
        """
        Set a new capture strategy for the ScreenCapture component.
        """
        self._capture_strategy.set(capture_strategy)

    def run(self) -> None:
        """
        Continuously captures screen images and puts it in the output queue.
        """
        while True:
            captured_data: Any = self._capture_strategy.get().capture_screen()
            self.output_queue.put(captured_data)

    def stop(self):
        super().stop()
        self._thread.join()


class EncoderComponent(Component):
    def __init__(self, input_queue: Queue, encoder_strategy: AbstractEncoderStrategy) -> None:
        super().__init__()
        self.output_queue = Queue()
        self._input_queue = input_queue
        self._encoder_strategy = AutoLockingValue(encoder_strategy)
        self._thread = threading.Thread(target=self.run)
        self._thread.start()

    def set_encoder_strategy(self, encoder_strategy: AbstractEncoderStrategy):
        """
        Set a new encoder strategy for the VideoEncoder component.
        """
        self._encoder_strategy.set(encoder_strategy)

    def run(self) -> None:
        """
        Continuously encodes data from the input queue and puts the encoded data
        in the output queue.
        """
        while True:
            captured_data: Any = self._input_queue.get()
            encoded_data: Any = self._encoder_strategy.get().encode_frame(captured_data)

            # If encoded_data is available, it means the encoding strategy has
            # enough data to produce an encoded frame. If not, it will wait
            # for more data before outputting an encoded frame.
            if encoded_data:
                self.output_queue.put(encoded_data)

    def stop(self):
        super().stop()
        self._thread.join()


class NetworkComponent(Component):
    def __init__(self, input_queue: Queue, tcp_socket: socket):
        super().__init__()
        self.input_queue = input_queue
        self._running = AutoLockingValue(True)
        self._thread = threading.Thread(target=self.run)
        self._socket = tcp_socket
        self._thread.start()

    def run(self) -> None:
        """
        Continuously sends encoded data from the input queue through the network.
        """
        while self.is_running():
            encoded_data: Any = self.input_queue.get()
            packet: Packet = VideoDataPacketFactory.create_packet(encoded_data)
            self._socket.sendall(packet.get_bytes())

    def stop(self):
        super().stop()
        self._thread.join()
