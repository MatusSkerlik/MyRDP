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
from pread import SocketDataReader, InvalidPacketType
from pwrite import SocketDataWriter

SLEEP_TIME = 1 / 120


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


class _CaptureComponent(Component):
    """
    A component that captures screen data using the provided capture strategy.

    This class is a subclass of the Component class and captures screen data using
    the specified capture strategy. It waits for a synchronization event to capture
    the screen, then puts the captured data into an output queue.

    Attributes:
        output_queue (Queue): A queue for storing the captured data.
        _capture_strategy (AutoLockingValue[AbstractCaptureStrategy]): A thread-safe
            container for the current capture strategy.
        _sync_event (threading.Event): A synchronization event to control when
            to capture the screen.
    """

    def __init__(self,
                 capture_strategy: AbstractCaptureStrategy,
                 event: threading.Event):
        super().__init__()

        self.output_queue = Queue(maxsize=1)
        self._capture_strategy = AutoLockingValue(capture_strategy)
        self._sync_event = event

    def __str__(self):
        return f"CaptureComponent(event={self._sync_event.is_set()})"

    def set_capture_strategy(self, capture_strategy: AbstractCaptureStrategy):
        self._capture_strategy.set(capture_strategy)

    def run(self) -> None:
        while self.is_running():
            if self._sync_event.wait(SLEEP_TIME):
                captured_data = self._capture_strategy.get().capture_screen()
                self.output_queue.put(captured_data)
                self._sync_event.clear()

    def stop(self):
        super().stop()
        self._sync_event.set()


class _EncoderComponent(Component):
    """
    A component that encodes captured screen data using the provided encoder strategy.

    This class is a subclass of the Component class and encodes screen data using
    the specified encoder strategy. It takes the captured data from an input queue,
    encodes it, and then puts the encoded data into an output queue.

    Attributes:
        _width (int): The width of the captured screen data.
        _height (int): The height of the captured screen data.
        output_queue (Queue): A queue for storing the encoded data.
        _input_queue (Queue): A queue for receiving the captured screen data.
        _encoder_strategy (AutoLockingValue[AbstractEncoderStrategy]): A thread-safe
            container for the current encoder strategy.
    """

    def __init__(self,
                 width: int,
                 height: int,
                 input_queue: Queue,
                 encoder_strategy: AbstractEncoderStrategy) -> None:
        super().__init__()

        self._width = width
        self._height = height

        self.output_queue = Queue(maxsize=1)
        self._input_queue = input_queue
        self._encoder_strategy = AutoLockingValue(encoder_strategy)

    def __str__(self):
        return f"EncoderComponent(width={self._width}, height={self._height}, strategy={self._encoder_strategy.get()})"

    def set_encoder_strategy(self, encoder_strategy: AbstractEncoderStrategy):
        self._encoder_strategy.set(encoder_strategy)

    def run(self) -> None:
        while self.is_running():
            try:
                frame = self._input_queue.get(timeout=SLEEP_TIME)
            except queue.Empty:
                continue
            encoded_data = self._encoder_strategy.get().encode_frame(self._width, self._height, frame)

            # If encoded_data is available, it means the encoding strategy has
            # enough data to produce an encoded frame. If not, it will wait
            # for more data before outputting an encoded frame.
            if encoded_data:
                self.output_queue.put(encoded_data)


class _StreamSenderComponent(Component):
    """
    A component that sends encoded video data to a socket.

    This class is a subclass of the Component class and sends encoded video data
    to a socket using the specified socket writer. It takes the encoded data from
    an input queue, wraps it into a packet using a factory, and then sends it
    using the socket writer. The component's execution is synchronized with a
    threading event.

    Attributes:
        _width (int): The width of the encoded video data.
        _height (int): The height of the encoded video data.
        _input_queue (Queue): A queue for receiving the encoded video data.
        _socket_writer (SocketDataWriter): A socket writer instance for sending data.
        _sync_event (threading.Event): A threading event for synchronization.
    """

    def __init__(self,
                 width: int,
                 height: int,
                 input_queue: Queue,
                 socket_writer: SocketDataWriter,
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
        while self.is_running():
            try:
                encoded_data = self._input_queue.get(timeout=SLEEP_TIME)
            except queue.Empty:
                continue
            self._sync_event.set()
            packet = VideoContainerDataPacketFactory.create_packet(self._width, self._height, encoded_data)
            try:
                self._socket_writer.write_packet(packet)
            except ConnectionError:
                pass

    def stop(self):
        super().stop()
        # Free all waiting threads
        self._sync_event.set()


class AbstractPipeline(ABC):
    """
    An abstract class representing a pipeline of processing components.

    This class provides a structure for managing a sequence of connected components
    that perform various operations on data in a pipeline. Subclasses must implement
    the `get_pipeline` method, which should return an iterable of components.

    Attributes:
        _threads (Union[None, List[threading.Thread]]): A list of threads used to run the components in the pipeline.
    """

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


class CaptureEncodeSendPipeline(AbstractPipeline):
    """
    A pipeline for capturing, encoding, and sending video data.

    This class is a concrete implementation of the AbstractPipeline that
    captures video data from the screen, encodes it, and sends it over
    a socket connection. It uses CaptureComponent, EncoderComponent, and
    StreamSenderComponent to perform these operations.

    Attributes:
        _capture_width (int): The width of the captured video.
        _capture_height (int): The height of the captured video.
        _capture_component (_CaptureComponent): The component responsible for capturing video data.
        _encoder_component (_EncoderComponent): The component responsible for encoding the video data.
        _sender_component (_StreamSenderComponent): The component responsible for sending the encoded video data.
    """

    def __init__(self,
                 fps: int,
                 socket_writer: SocketDataWriter):
        super().__init__()

        self._capture_width = None
        self._capture_height = None

        # pipeline initialization
        synchronize_pipeline_event = threading.Event()
        synchronize_pipeline_event.set()
        capture_strategy = CaptureEncodeSendPipeline._get_default_capture_strategy(fps)
        self._capture_component = _CaptureComponent(
            capture_strategy,
            synchronize_pipeline_event
        )
        self._capture_width = capture_strategy.get_monitor_width()
        self._capture_height = capture_strategy.get_monitor_height()

        self._encoder_component = _EncoderComponent(
            self._capture_width,
            self._capture_height,
            self._capture_component.output_queue,  # join queues between
            CaptureEncodeSendPipeline._get_default_encoder_strategy(1)
        )

        self._sender_component = _StreamSenderComponent(
            self._capture_width,
            self._capture_height,
            self._encoder_component.output_queue,  # join queues between
            socket_writer,
            synchronize_pipeline_event
        )

    def get_capture_component(self):
        return self._capture_component

    def get_encoder_component(self):
        return self._encoder_component

    def get_sender_component(self):
        return self._sender_component

    def get_capture_width(self):
        return self._capture_width

    def get_capture_height(self):
        return self._capture_height

    def get_pipeline(self):
        return [self._capture_component, self._encoder_component, self._sender_component]

    @staticmethod
    def _get_default_capture_strategy(fps: int) -> AbstractCaptureStrategy:
        return (CaptureStrategyBuilder()
                .set_strategy_type("mss")
                .set_option("fps", fps)
                .build())

    @staticmethod
    def _get_default_encoder_strategy(fps: int) -> AbstractEncoderStrategy:
        return (EncoderStrategyBuilder()
                .set_strategy_type("default")
                .set_option("fps", fps)
                .build())


class _StreamReaderComponent(Component):
    """
    Component class for reading video data from a socket connection.

    This class is a Component responsible for reading video data from a
    socket connection using a SocketDataReader. The received video data is
    added to the output queue for further processing.

    Attributes:
        output_queue (queue.Queue): The queue to store the received video data.
        _running (AutoLockingValue): A thread-safe boolean flag indicating the running state of the component.
        _socket_reader (SocketDataReader): The socket data reader used for reading video data from a socket.
    """

    def __init__(self, socket_reader: SocketDataReader):
        super().__init__()

        self.output_queue = queue.Queue(maxsize=1)
        self._running = AutoLockingValue(True)
        self._socket_reader = socket_reader

    def __str__(self):
        return f"SocketReaderComponent()"

    def run(self) -> None:
        while self.is_running():
            try:
                object_data = self._socket_reader.read_packet()

                if object_data is None:
                    continue

                if isinstance(object_data, VideoData):
                    self.output_queue.put(object_data)

            except InvalidPacketType as e:
                print(f"Invalid packet type: {e}")


class _DecoderComponent(Component):
    """
    Component class for decoding video data.

    This class is a Component responsible for decoding video data using a
    provided decoding strategy. The input video data is retrieved from an
    input queue, decoded, and the decoded frame is added to the output queue
    for further processing.

    Attributes:
        _input_queue (Queue): The queue from which the component retrieves video data for decoding.
        output_queue (queue.Queue): The queue to store the decoded video frames.
        _decoder_strategy (AutoLockingValue): The thread-safe decoding strategy used for decoding video data.
    """

    def __init__(self,
                 input_queue: Queue,
                 decoder_strategy: AbstractDecoderStrategy):
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
                time.sleep(0.01)
                continue
            decoded_frame = self._decoder_strategy.get().decode_packet(video_data)
            self.output_queue.put((video_data, decoded_frame))


class ReadDecodePipeline(AbstractPipeline):
    """
    A pipeline for reading and decoding video data from a socket connection.

    This class is a concrete implementation of the AbstractPipeline that
    reads video data from a socket connection and decodes it. It uses
    _StreamReaderComponent and _DecoderComponent to perform these operations.

    Attributes:
        _socket_reader_component (_StreamReaderComponent): The component responsible for reading video data from a socket.
        _decoder_component (_DecoderComponent): The component responsible for decoding the video data.
    """

    def __init__(self, socket_reader: SocketDataReader):
        super().__init__()
        self._socket_reader_component = _StreamReaderComponent(socket_reader)
        self._decoder_component = _DecoderComponent(
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
