import os

import pygame
from pygame import QUIT

from connection import AutoReconnectClient
from executor import CommandExecutor
from lock import AutoLockingValue
from pipeline import CaptureEncodeSendPipeline
from pread import SocketDataReader
from processor import StreamPacketProcessor
from pwrite import SocketDataWriter


class Client:
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
        _pipeline (CaptureEncodeSendPipeline): The pipeline object for processing the video stream.
    """

    def __init__(self,
                 host: str,
                 port: int,
                 width: int,
                 height: int,
                 fps: int,
                 title: str = "Client"):
        self._title = title
        self._width = width
        self._height = height

        self._fps = fps
        self._running = False

        self._connection = AutoReconnectClient(host, port)
        self._socket_reader = SocketDataReader(self._connection)
        self._socket_writer = SocketDataWriter(self._connection)
        self._stream_packet_processor = StreamPacketProcessor(self._socket_reader)
        self._command_executor = CommandExecutor(self._stream_packet_processor)
        self._pipeline = CaptureEncodeSendPipeline(fps, self._socket_writer)

    def run(self):
        if self._running:
            raise RuntimeError("The 'run' method can only be called once")
        self._running = True
        self._connection.start()
        self._stream_packet_processor.start()
        self._pipeline.start()
        self._command_executor.start()

        pygame.init()
        screen = pygame.display.set_mode((self._width, self._height))
        pygame.display.set_caption(self._title)
        clock = pygame.time.Clock()

        while self._running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.stop()
                    break

            screen.fill((0, 0, 0))
            pygame.display.flip()
            clock.tick(self._fps)

    pygame.quit()

    def stop(self):
        self._connection.stop()
        self._stream_packet_processor.stop()
        self._pipeline.stop()
        self._command_executor.stop()
        self._running = False


HOST = (os.getenv("RDP_SERVER_IP") or "127.0.0.1")
PORT = (os.getenv("RDP_SERVER_PORT") or 8085)
FPS = 25

if __name__ == "__main__":
    client = Client(HOST, PORT, 200, 200, FPS)
    client.run()
