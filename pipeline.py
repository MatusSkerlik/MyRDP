import queue
import threading
import time
from abc import ABC, abstractmethod
from queue import Queue
from typing import Union, List, Tuple

import numpy as np

from capture import AbstractCaptureStrategy, CaptureStrategyBuilder
from dao import VideoContainerDataPacketFactory, VideoData
from decode import DecoderStrategyBuilder, AbstractDecoderStrategy
from encode import AbstractEncoderStrategy, EncoderStrategyBuilder
from lock import AutoLockingValue
from pread import SocketDataReader
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
    def __init__(self, capture_strategy: AbstractCaptureStrategy, event: threading.Event):
        super().__init__()
        self.output_queue = Queue(maxsize=1)
        self._capture_strategy = AutoLockingValue(capture_strategy)
        self._sync_event = event

    def __str__(self):
        return f"CaptureComponent(event={self._sync_event.is_set()})"

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
            self._sync_event.wait()
            captured_data = self._capture_strategy.get().capture_screen()
            self.output_queue.put(captured_data)
            self._sync_event.clear()

    def stop(self):
        super().stop()
        self._sync_event.set()


class EncoderComponent(Component):
    def __init__(self, width: int, height: int, input_queue: Queue, encoder_strategy: AbstractEncoderStrategy) -> None:
        super().__init__()
        self._width = width
        self._height = height

        self.output_queue = Queue(maxsize=1)
        self._input_queue = input_queue
        self._encoder_strategy = AutoLockingValue(encoder_strategy)

    def __str__(self):
        return f"EncoderComponent(width={self._width}, height={self._height}, strategy={self._encoder_strategy.get()})"

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
            try:
                captured_data = self._input_queue.get(block=False)
            except queue.Empty:
                time.sleep(0.001)
                continue
            encoded_data = self._encoder_strategy.get().encode_frame(self._width, self._height, captured_data)

            # If encoded_data is available, it means the encoding strategy has
            # enough data to produce an encoded frame. If not, it will wait
            # for more data before outputting an encoded frame.
            if encoded_data:
                self.output_queue.put(encoded_data)


class SocketWriterComponent(Component):
    def __init__(self, width: int, height: int, input_queue: Queue, socket_writer: SocketDataWriter,
                 synchronization_event: threading.Event):
        super().__init__()
        self._width = width
        self._height = height

        self._input_queue = input_queue
        self._socket_writer = socket_writer
        self._sync_event = synchronization_event

    def __str__(self):
        return f"SocketWriterComponent(width={self._width}, height={self._height}, event={self._sync_event.is_set()})"

    def run(self) -> None:
        """
        Continuously sends encoded data from the input queue through the network.
        """
        while self.is_running():
            try:
                encoded_data = self._input_queue.get(block=False)
            except queue.Empty:
                time.sleep(0.001)
                continue
            self._sync_event.set()
            packet = VideoContainerDataPacketFactory.create_packet(self._width, self._height, encoded_data)
            try:
                self._socket_writer.write_packet(packet)
            except ConnectionError:
                pass

    def stop(self):
        super().stop()
        # Free waiters
        self._sync_event.set()


class AbstractPipeline(ABC):
    def __init__(self):
        self._threads: Union[None, List[threading.Thread]] = None

    def start(self):
        if self._threads is None:
            self._threads = []
            for component in self.get_pipeline():
                thread = threading.Thread(target=component.run)
                print(f"Starting thread for: {component}")
                thread.daemon = True
                thread.start()
                self._threads.append(thread)
        else:
            raise RuntimeError("Pipeline already started.")

    def stop(self):
        if len(self._threads) > 0:
            for component in self.get_pipeline():
                print(f"Stopping component '{component}'")
                component.stop()
            for component, thread in zip(self.get_pipeline(), self._threads):
                print(f"Joining thread for '{component}'")
                thread.join()
                print(f"Joined thread for '{component}'")
            self._threads = []
        else:
            raise RuntimeError("Pipeline did not started")

    @abstractmethod
    def get_pipeline(self):
        pass


class CaptureEncodeNetworkPipeline(AbstractPipeline):
    def __init__(self, socket_writer: SocketDataWriter, fps: int):
        super().__init__()
        self._capture_width = None
        self._capture_height = None

        # pipeline initialization
        block_until_sent_event = threading.Event()
        block_until_sent_event.set()
        capture_strategy = CaptureEncodeNetworkPipeline._get_default_capture_strategy(fps)
        self._capture_component = CaptureComponent(
            capture_strategy,
            block_until_sent_event
        )
        self._capture_width = capture_strategy.get_monitor_width()
        self._capture_height = capture_strategy.get_monitor_height()
        self._encoder_component = EncoderComponent(
            self._capture_width,
            self._capture_height,
            self._capture_component.output_queue,  # join queues between
            CaptureEncodeNetworkPipeline._get_default_encoder_strategy(1)
        )
        self._network_component = SocketWriterComponent(
            self._capture_width,
            self._capture_height,
            self._encoder_component.output_queue,  # join queues between
            socket_writer,
            block_until_sent_event
        )

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

    def get_pipeline(self):
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


class SocketReaderComponent(Component):
    def __init__(self, socket_reader: SocketDataReader):
        super().__init__()
        self.output_queue = queue.Queue(maxsize=1)
        self._running = AutoLockingValue(True)
        self._socket_reader = socket_reader

    def __str__(self):
        return f"SocketReaderComponent()"

    def run(self) -> None:
        """
        Continuously sends encoded data from the input queue through the network.
        """
        while self.is_running():
            object_data = self._socket_reader.read_packet()

            if object_data is None:
                continue

            if isinstance(object_data, VideoData):
                self.output_queue.put(object_data)


class DecoderComponent(Component):
    def __init__(self, input_queue: Queue, decoder_strategy: AbstractDecoderStrategy):
        super().__init__()
        self._input_queue = input_queue
        self.output_queue = queue.Queue(maxsize=1)
        self._decoder_strategy = AutoLockingValue(decoder_strategy)

    def __str__(self):
        return f"DecoderComponent(strategy={self._decoder_strategy.get()})"

    def set_decoder_strategy(self, decoder_strategy: AbstractDecoderStrategy):
        self._decoder_strategy.set(decoder_strategy)

    def run(self) -> None:
        while self.is_running():
            try:
                video_data: VideoData = self._input_queue.get(block=False)
            except queue.Empty:
                time.sleep(0.025)
                continue
            decoded_frame = self._decoder_strategy.get().decode_packet(video_data)
            self.output_queue.put((video_data, decoded_frame))


class ReadDecodePipeline(AbstractPipeline):
    def __init__(self, socket_reader: SocketDataReader):
        super().__init__()
        self._socket_reader_component = SocketReaderComponent(socket_reader)
        self._decoder_component = DecoderComponent(
            self._socket_reader_component.output_queue,
            self._get_default_decoder_strategy()
        )

    def get_socket_reader_component(self):
        return self._socket_reader_component

    def get_decoder_component(self):
        return self._decoder_component

    def get_pipeline(self):
        return [self._socket_reader_component, self._decoder_component]

    def get(self) -> Union[None, Tuple[VideoData, List[np.ndarray]]]:
        try:
            return self._decoder_component.output_queue.get(block=False)
        except queue.Empty:
            return None

    @staticmethod
    def _get_default_decoder_strategy():
        return DecoderStrategyBuilder() \
            .set_strategy_type("default") \
            .build()
