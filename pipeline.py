import threading
from abc import ABC, abstractmethod
from queue import Queue
from typing import Union, List

from capture import AbstractCaptureStrategy, CaptureStrategyBuilder
from dao import VideoContainerDataPacketFactory
from encode import AbstractEncoderStrategy, EncoderStrategyBuilder
from lock import AutoLockingValue
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


class EncoderComponent(Component):
    def __init__(self, width: int, height: int, input_queue: Queue, encoder_strategy: AbstractEncoderStrategy) -> None:
        super().__init__()
        self._width = width
        self._height = height

        self.output_queue = Queue()
        self._input_queue = input_queue
        self._encoder_strategy = AutoLockingValue(encoder_strategy)

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
            encoded_data = self._encoder_strategy.get().encode_frame(self._width, self._height, captured_data)

            # If encoded_data is available, it means the encoding strategy has
            # enough data to produce an encoded frame. If not, it will wait
            # for more data before outputting an encoded frame.
            if encoded_data:
                self.output_queue.put(encoded_data)


class NetworkComponent(Component):
    def __init__(self, width: int, height: int, input_queue: Queue, socket_writer: SocketDataWriter):
        super().__init__()
        self._width = width
        self._height = height

        self._input_queue = input_queue
        self._running = AutoLockingValue(True)
        self._socket_writer = socket_writer

    def run(self) -> None:
        """
        Continuously sends encoded data from the input queue through the network.
        """
        while self.is_running():
            encoded_data = self._input_queue.get()
            packet = VideoContainerDataPacketFactory.create_packet(self._width, self._height, encoded_data)
            self._socket_writer.write_packet(packet)


class CaptureEncodeNetworkPipeline:
    def __init__(self, socket_writer: SocketDataWriter, fps: int):
        self._capture_width = None
        self._capture_height = None

        # pipeline initialization
        self._threads: Union[None, List[threading.Thread]] = None
        capture_strategy = CaptureEncodeNetworkPipeline._get_default_capture_strategy(fps)
        self._capture_component = CaptureComponent(
            capture_strategy
        )
        self._capture_width = capture_strategy.get_monitor_width()
        self._capture_height = capture_strategy.get_monitor_height()
        self._encoder_component = EncoderComponent(
            self._capture_width,
            self._capture_height,
            self._capture_component.output_queue,  # join queues between
            CaptureEncodeNetworkPipeline._get_default_encoder_strategy(5)
        )
        self._network_component = NetworkComponent(
            self._capture_width,
            self._capture_height,
            self._encoder_component.output_queue,  # join queues between
            socket_writer
        )

    def start(self):
        if self._threads is None:
            self._threads = []
            for component in self._get_pipeline():
                thread = threading.Thread(target=component.run)
                thread.daemon = True
                thread.start()
                self._threads.append(thread)
        else:
            raise RuntimeError("Pipeline already started.")

    def stop(self):
        if len(self._threads) > 0:
            for component in self._get_pipeline():
                component.stop()
            for thread in self._threads:
                thread.join()
            self._threads = []
        else:
            raise RuntimeError("Pipeline did not started")

    def get_capture_component(self):
        return self._capture_component

    def get_encoder_component(self):
        return self._encoder_component

    def get_network_component(self):
        return self._network_component

    def get_capture_width(self):
        return self._capture_width

    def get_capture_height(self):
        return self._capture_height

    def _get_pipeline(self):
        return [self._capture_component, self._encoder_component, self._network_component]

    @staticmethod
    def _get_default_capture_strategy(fps: int) -> AbstractCaptureStrategy:
        return CaptureStrategyBuilder() \
            .set_strategy_type("mss") \
            .set_option("fps", fps) \
            .build()

    @staticmethod
    def _get_default_encoder_strategy(fps: int) -> AbstractEncoderStrategy:
        return EncoderStrategyBuilder() \
            .set_strategy_type("default") \
            .set_option("fps", fps) \
            .build()
