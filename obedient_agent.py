import pygame
from pygame import QUIT

from connection import Connection
from constants import *
from lock import AutoLockingValue
from pipeline import CaptureEncodeSendPipeline
from pread import SocketDataReader
from processor import PacketProcessor, CommandProcessor
from pwrite import SocketDataWriter
from render import FlexboxLayout, TextLayout


class ObedientAgent:
    """
    A class representing a client in a video streaming application.

    This class is responsible for handling the client-side operations of a
    video streaming application. It captures the screen, encodes the captured
    frames, and sends the encoded frames to a server. It also handles user
    input events for stopping the streaming process.

    Attributes:
        _title (str): The title of the pygame window.
        _width (int): The width of the pygame window.
        _height (int): The height of the pygame window.
        _fps (int): The desired frame rate for capturing and displaying the video.
        _running (AutoLockingValue): A boolean flag to indicate if the client is running.
        _connection (AutoReconnectClient): The connection object for the client.
        _socket_reader (SocketDataReader): The socket data reader object.
        _socket_writer (SocketDataWriter): The socket data writer object.
        _capture_encode_send_pipeline (CaptureEncodeSendPipeline): The pipeline object for processing the video stream.
    """

    def __init__(self,
                 local_ip: str,
                 local_port: int,
                 remote_ip: str,
                 remote_port: int,
                 width: int,
                 height: int,
                 transmission_width: int,  # TODO protocol negotiated
                 transmission_height: int,  # TODO protocol negotiated
                 fps: int,
                 title: str = "Client"):
        self._title = title
        self._width = width
        self._height = height

        self._fps = fps
        self._running = False

        self._connection = Connection(local_ip, local_port, remote_ip, remote_port)
        self._socket_reader = SocketDataReader(self._connection)
        self._socket_writer = SocketDataWriter(self._connection)
        self._packet_processor = PacketProcessor(self._socket_reader)
        self._command_processor = CommandProcessor(self._packet_processor)
        self._capture_encode_send_pipeline = CaptureEncodeSendPipeline(transmission_width, transmission_height,
                                                                       self._socket_writer)

    def run(self):
        if self._running:
            raise RuntimeError("The 'run' method can only be called once")
        self._packet_processor.start()
        self._running = True

        pygame.init()
        screen = pygame.display.set_mode((self._width, self._height))
        pygame.display.set_caption(self._title)
        clock = pygame.time.Clock()

        while self._running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.stop()
                    break

            self._command_processor.process()
            self._capture_encode_send_pipeline.run()

            screen.fill((0, 0, 0))

            (FlexboxLayout()
             .set_mode("column")
             .set_align_items("start")
             .set_background((0, 0, 0))
             .add_child(TextLayout(f"FPS: {clock.get_fps():.2f}"))
             .set_text_size(24)
             .render(screen))

            pygame.display.flip()
            clock.tick(self._fps)

    pygame.quit()

    def stop(self):
        self._packet_processor.stop()
        self._running = False


if __name__ == "__main__":
    try:
        client = ObedientAgent(OBEDIENT_AGENT_IP, OBEDIENT_AGENT_PORT, CONTROL_AGENT_IP, CONTROL_AGENT_PORT,
                               200, 200, 800, 600, FPS)
        client.run()
    except KeyboardInterrupt:
        pass
