import queue
import threading
from abc import ABC, abstractmethod
from queue import Queue
from typing import Union, List, Any

from capture import AbstractCaptureStrategy, CaptureStrategyBuilder
from connection import NoConnection
from dao import VideoContainerDataPacketFactory
from decode import DecoderStrategyBuilder, AbstractDecoderStrategy
from encode import AbstractEncoderStrategy, EncoderStrategyBuilder
from enums import PacketType
from fps import FrameRateLimiter
from lock import AutoLockingValue
from processor import PacketProcessor
from pwrite import SocketDataWriter
from thread import Task

SLEEP_TIME = 1 / 120


class Component(ABC):
    @abstractmethod
    def run(self, *args) -> Union[None, bytes]:
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

    def __init__(self, capture_strategy: AbstractCaptureStrategy, ):
        super().__init__()
        self._capture_strategy = capture_strategy

    def __str__(self):
        return f"CaptureComponent()"

    def set_capture_strategy(self, capture_strategy: AbstractCaptureStrategy):
        self._capture_strategy = capture_strategy

    def run(self, *args):
        return self._capture_strategy.capture_screen()


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
                 encoder_strategy: AbstractEncoderStrategy) -> None:
        super().__init__()

        self._width = width
        self._height = height

        self._encoder_strategy = encoder_strategy

    def __str__(self):
        return f"EncoderComponent(width={self._width}, height={self._height}, strategy={self._encoder_strategy})"

    def set_encoder_strategy(self, encoder_strategy: AbstractEncoderStrategy):
        self._encoder_strategy = encoder_strategy

    def run(self, frame):
        if frame:
            return self._encoder_strategy.encode_frame(self._width, self._height, frame)
        return None


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
                 socket_writer: SocketDataWriter):
        super().__init__()

        self._width = width
        self._height = height
        self._socket_writer = socket_writer

    def __str__(self):
        return f"SocketWriterComponent(width={self._width}, height={self._height})"

    def run(self, encoded_frame) -> None:
        packet = VideoContainerDataPacketFactory.create_packet(self._width, self._height, encoded_frame)
        try:
            self._socket_writer.write_packet(packet)
        except NoConnection:
            # Connection lost
            # We are discarding encoded data
            pass
        except RuntimeError:
            # Application close
            # Client should be responsible to setting running to false
            pass


class AbstractPipeline(Task, ABC):
    """
    An abstract class representing a pipeline of processing components.

    This class provides a structure for managing a sequence of connected components
    that perform various operations on data in a pipeline. Subclasses must implement
    the `get_pipeline` method, which should return an iterable of components.

    Attributes:
        _threads (Union[None, List[threading.Thread]]): A list of threads used to run the components in the pipeline.
    """

    def __init__(self, fps: int):
        super().__init__()
        self._queue_of_results = queue.Queue()
        self._frame_limiter = FrameRateLimiter(fps)

    @abstractmethod
    def get_components(self):
        pass

    def pop_result(self) -> Any:
        try:
            return self._queue_of_results.get_nowait()
        except queue.Empty:
            return None

    def run(self):
        while self.running.getv():
            last_result = None
            pipe_passed = True
            for component in self.get_components():
                component_result = component.run(last_result)
                if component_result is None:
                    pipe_passed = False
                    break
                else:
                    last_result = component_result
            if pipe_passed:
                self._queue_of_results.put(last_result)

            # Limit pipeline throughput to fps
            self._frame_limiter.tick()


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

    def __init__(self, fps: int, socket_writer: SocketDataWriter):
        super().__init__(fps)

        self._capture_width = None
        self._capture_height = None

        # pipeline initialization
        capture_strategy = CaptureEncodeSendPipeline._get_default_capture_strategy(fps)
        self._capture_component = _CaptureComponent(
            capture_strategy,
        )
        self._capture_width = capture_strategy.get_monitor_width()
        self._capture_height = capture_strategy.get_monitor_height()

        self._encoder_component = _EncoderComponent(
            self._capture_width,
            self._capture_height,
            CaptureEncodeSendPipeline._get_default_encoder_strategy(1),
        )

        self._sender_component = _StreamSenderComponent(
            self._capture_width,
            self._capture_height,
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

    def get_components(self):
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
        _stream_packet_processor (PacketProcessor)
    """

    def __init__(self, packet_processor: PacketProcessor):
        super().__init__()
        self._stream_packet_processor = packet_processor

    def __str__(self):
        return f"SocketReaderComponent()"

    def run(self, *args):
        return self._stream_packet_processor.get_packet_data(PacketType.VIDEO_DATA)


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

    def __init__(self, decoder_strategy: AbstractDecoderStrategy):
        super().__init__()

        self._decoder_strategy = decoder_strategy

    def __str__(self):
        return f"DecoderComponent(strategy={self._decoder_strategy.getv()})"

    def set_decoder_strategy(self, decoder_strategy: AbstractDecoderStrategy):
        self._decoder_strategy = decoder_strategy

    def run(self, video_data):
        if video_data:
            return video_data, self._decoder_strategy.decode_packet(video_data)
        return None


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

    def __init__(self, fps: int, stream_packet_processor: PacketProcessor):
        super().__init__(fps)

        self._socket_reader_component = _StreamReaderComponent(stream_packet_processor)
        self._decoder_component = _DecoderComponent(self._get_default_decoder_strategy())

    def get_socket_reader_component(self):
        return self._socket_reader_component

    def get_decoder_component(self):
        return self._decoder_component

    def get_components(self):
        return [self._socket_reader_component, self._decoder_component]

    @staticmethod
    def _get_default_decoder_strategy():
        return DecoderStrategyBuilder() \
            .set_strategy_type("default") \
            .build()
