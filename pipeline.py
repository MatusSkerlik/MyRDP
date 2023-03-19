import threading
from abc import ABC, abstractmethod
from queue import Queue

from capture import AbstractCaptureStrategy
from encode import AbstractEncoderStrategy
from lock import AutoLockingValue
from pfactory import VideoDataPacketFactory
from pwrite import SocketDataWriter


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
        self._thread.daemon = True
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
        while self.is_running():
            captured_data = self._capture_strategy.get().capture_screen()
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
        self._thread.daemon = True
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
        while self.is_running():
            captured_data = self._input_queue.get()
            encoded_data = self._encoder_strategy.get().encode_frame(captured_data)

            # If encoded_data is available, it means the encoding strategy has
            # enough data to produce an encoded frame. If not, it will wait
            # for more data before outputting an encoded frame.
            if encoded_data:
                self.output_queue.put(encoded_data)

    def stop(self):
        super().stop()
        self._thread.join()


class NetworkComponent(Component):
    def __init__(self, input_queue: Queue, socket_writer: SocketDataWriter):
        super().__init__()
        self.input_queue = input_queue
        self._running = AutoLockingValue(True)
        self._socket_writer = socket_writer
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()

    def run(self) -> None:
        """
        Continuously sends encoded data from the input queue through the network.
        """
        while self.is_running():
            encoded_data = self.input_queue.get()
            packet = VideoDataPacketFactory.create_packet(encoded_data)
            self._socket_writer.write_packet(packet)

    def stop(self):
        super().stop()
        self._thread.join()
