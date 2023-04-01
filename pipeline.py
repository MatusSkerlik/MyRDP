import queue
import threading
import time
from abc import ABC, abstractmethod
from queue import Queue
from typing import Union, List, Tuple

import numpy as np

from capture import AbstractCaptureStrategy, CaptureStrategyBuilder
from connection import NoConnection
from dao import VideoContainerDataPacketFactory, MouseMoveData, VideoData
from decode import DecoderStrategyBuilder, AbstractDecoderStrategy
from encode import AbstractEncoderStrategy, EncoderStrategyBuilder
from enums import PacketType
from lock import AutoLockingValue
from processor import StreamPacketProcessor
from pwrite import SocketDataWriter
from thread import Task

SLEEP_TIME = 1 / 120


class Component(Task, ABC):
    pass


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
        self._capture_strategy.setv(capture_strategy)

    def run(self) -> None:
        while self.running.getv():
            if self._sync_event.is_set():
                screen_shot = self._capture_strategy.getv().capture_screen()
                if screen_shot:
                    self.output_queue.put(screen_shot)
                    self._sync_event.clear()
            time.sleep(SLEEP_TIME)


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
                 encoder_strategy: AbstractEncoderStrategy,
                 synchronization_event: threading.Event) -> None:
        super().__init__()

        self._width = width
        self._height = height

        self.output_queue = Queue(maxsize=1)
        self._input_queue = input_queue
        self._encoder_strategy = AutoLockingValue(encoder_strategy)
        self._sync_event = synchronization_event

    def __str__(self):
        return f"EncoderComponent(width={self._width}, height={self._height}, strategy={self._encoder_strategy.getv()})"

    def set_encoder_strategy(self, encoder_strategy: AbstractEncoderStrategy):
        self._encoder_strategy.setv(encoder_strategy)

    def run(self) -> None:
        while self.running.getv():
            time.sleep(SLEEP_TIME)
            try:
                frame = self._input_queue.get_nowait()
            except queue.Empty:
                continue

            encoded_data = self._encoder_strategy.getv().encode_frame(self._width, self._height, frame)
            # If encoded_data is available, it means the encoding strategy has
            # enough data to produce an encoded frame. If not, it will wait
            # for more data before outputting an encoded frame.
            if encoded_data:
                self._sync_event.set()
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
                 socket_writer: SocketDataWriter):
        super().__init__()

        self._width = width
        self._height = height

        self._input_queue = input_queue
        self._socket_writer = socket_writer

    def __str__(self):
        return f"SocketWriterComponent(width={self._width}, height={self._height})"

    def run(self) -> None:
        while self.running.getv():
            time.sleep(SLEEP_TIME)
            try:
                encoded_data = self._input_queue.get_nowait()
            except queue.Empty:
                continue

            packet = VideoContainerDataPacketFactory.create_packet(self._width, self._height, encoded_data)
            try:
                self._socket_writer.write_packet(packet)
            except NoConnection:
                # Connection lost
                # We are discarding encoded data
                time.sleep(0.25)
                continue
            except RuntimeError:
                # Application close
                # Client should be responsible to setting running to false
                continue


class AbstractPipeline(ABC):
    """
    An abstract class representing a pipeline of processing components.

    This class provides a structure for managing a sequence of connected components
    that perform various operations on data in a pipeline. Subclasses must implement
    the `get_pipeline` method, which should return an iterable of components.

    Attributes:
        _threads (Union[None, List[threading.Thread]]): A list of threads used to run the components in the pipeline.
    """

    def start(self):
        for component in self.get_pipeline():
            component.start()

    def stop(self):
        for component in self.get_pipeline():
            component.stop()

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
            CaptureEncodeSendPipeline._get_default_encoder_strategy(1),
            synchronize_pipeline_event
        )

        self._sender_component = _StreamSenderComponent(
            self._capture_width,
            self._capture_height,
            self._encoder_component.output_queue,  # join queues between
            socket_writer
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
        _stream_packet_processor (StreamPacketProcessor)
    """

    def __init__(self, stream_packet_processor: StreamPacketProcessor):
        super().__init__()

        self.output_queue = queue.Queue(maxsize=1)
        self._running = AutoLockingValue(True)
        self._stream_packet_processor = stream_packet_processor

    def __str__(self):
        return f"SocketReaderComponent()"

    def run(self) -> None:
        while self.running.getv():
            time.sleep(SLEEP_TIME)
            video_data = self._stream_packet_processor.get_packet_data(PacketType.VIDEO_DATA)
            if video_data:
                try:
                    self.output_queue.put_nowait(video_data)
                except queue.Full:
                    # We are discarding packet if encoder is slow
                    # and did not process frame before
                    continue


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
        # Output queue of decoded frame should be unlimited
        # It is on rendering to consume them, rendering FPS > decoding FPS
        self.output_queue = queue.Queue()
        self._decoder_strategy = AutoLockingValue(decoder_strategy)

    def __str__(self):
        return f"DecoderComponent(strategy={self._decoder_strategy.getv()})"

    def set_decoder_strategy(self, decoder_strategy: AbstractDecoderStrategy):
        self._decoder_strategy.setv(decoder_strategy)

    def run(self) -> None:
        while self.running.getv():
            time.sleep(SLEEP_TIME)
            try:
                video_data: MouseMoveData = self._input_queue.get_nowait()
            except queue.Empty:
                continue

            decoded_frame = self._decoder_strategy.getv().decode_packet(video_data)
            # Should never block, queue has unlimited memory
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

    def __init__(self, stream_packet_processor: StreamPacketProcessor):
        super().__init__()
        self._socket_reader_component = _StreamReaderComponent(stream_packet_processor)
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
            return self._decoder_component.output_queue.get_nowait()
        except queue.Empty:
            return None

    @staticmethod
    def _get_default_decoder_strategy():
        return DecoderStrategyBuilder() \
            .set_strategy_type("default") \
            .build()
