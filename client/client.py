from network import SocketFactory
from .capture import CaptureStrategyBuilder, AbstractCaptureStrategy
from .encode import EncoderStrategyBuilder, AbstractEncoderStrategy
from .pipeline import EncoderComponent, CaptureComponent, NetworkComponent


class Client:
    def __init__(self, host: str, port: int, width: int, height: int, fps: int):
        """
        The Client class sets up the capture, encoding, and networking pipeline for streaming
        screen captures to a remote server.

        Attributes:
            width (int): The width of the captured screen.
            height (int): The height of the captured screen.
            fps (int): The desired frame rate of the captured screen.
            socket (socket.socket): The TCP socket used for communication with the server.
            pipeline_running (bool): Flag indicating if the pipeline is running.
            capture_component (CaptureComponent): The screen capture component of the pipeline.
            encoder_component (EncoderComponent): The video encoder component of the pipeline.
            network_component (NetworkComponent): The networking component of the pipeline.
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.socket = SocketFactory.connect(host, port)

        # pipeline creation
        self.pipeline_running = False
        self.capture_component = CaptureComponent(
            self._get_default_capture_strategy()
        )
        self.encoder_component = EncoderComponent(
            self.capture_component.output_queue,  # join queues between
            self._get_default_encoder_strategy()
        )
        self.network_component = NetworkComponent(
            self.encoder_component.output_queue,  # join queues between
            self.socket
        )

    def _get_default_capture_strategy(self) -> AbstractCaptureStrategy:
        return CaptureStrategyBuilder \
            .set_strategy_type("mss") \
            .set_option("widht", self.width) \
            .set_option("height", self.height) \
            .set_option("fps", self.fps) \
            .build()

    def _get_default_encoder_strategy(self) -> AbstractEncoderStrategy:
        return EncoderStrategyBuilder \
            .set_strategy_type("av") \
            .set_option("width", self.width) \
            .set_option("height", self.height) \
            .set_option("fps", self.fps) \
            .build()

    def run(self):
        pass
