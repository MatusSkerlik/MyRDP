from typing import Tuple

import pygame

from bandwidth import BandwidthMonitor, BandwidthStateMachine, BandwidthFormatter
from command import MouseMoveCommand, MouseClickCommand, KeyboardEventCommand
from connection import AutoReconnectServer
from enums import MouseButton, ButtonState, ASCIIEnum
from fps import FrameRateCalculator
from lock import AutoLockingValue
from pipeline import ReadDecodePipeline
from pread import SocketDataReader
from pwrite import SocketDataWriter
from render import FlexboxLayout, TextLayout


class Server:
    """
    A class representing a server in a video streaming application.

    This class is responsible for handling server-side operations of a
    video streaming application. It receives encoded frames from a client,
    decodes the frames, and displays the video. It also handles user input events
    for stopping the streaming process, as well as mouse and keyboard events.

    Attributes:
        _host (str): The server's host address.
        _port (int): The server's port number.
        _width (int): The width of the pygame window.
        _height (int): The height of the pygame window.
        _fps (int): The desired frame rate for receiving and displaying the video.
        _caption (str): The caption of the pygame window.
        _running (AutoLockingValue): A boolean flag to indicate if the server is running.
        _connection (AutoReconnectServer): The connection object for the server.
        _socket_reader (SocketDataReader): The socket data reader object.
        _socket_writer (SocketDataWriter): The socket data writer object.
        _bandwidth_monitor (BandwidthMonitor): A bandwidth monitor object to track bandwidth usage.
        _bandwidth_state_machine (BandwidthStateMachine): A state machine to manage bandwidth states.
        _read_decode_pipeline (ReadDecodePipeline): The pipeline object for processing the video stream.
    """

    def __init__(self,
                 host: str,
                 port: int,
                 width: int,
                 height: int,
                 fps: int,
                 caption: str = "Server") -> None:
        self._host = host
        self._port = port

        self._width = width
        self._height = height
        self._fps = fps
        self._caption = caption

        self._running = AutoLockingValue(False)
        self._connection = AutoReconnectServer(host, port)
        self._socket_reader = SocketDataReader(self._connection)
        self._socket_writer = SocketDataWriter(self._connection)
        self._bandwidth_monitor = BandwidthMonitor()
        self._bandwidth_state_machine = BandwidthStateMachine()
        self._read_decode_pipeline = ReadDecodePipeline(self._socket_reader)

    def is_running(self):
        return self._running.get()

    def run(self) -> None:
        if self._running.get():
            raise RuntimeError("The 'run' method can only be called once")
        self._running.set(True)
        self._connection.start()
        self._read_decode_pipeline.start()

        pygame.init()
        screen = pygame.display.set_mode((self._width, self._height), pygame.RESIZABLE)
        pygame.display.set_caption(self._caption)
        clock = pygame.time.Clock()
        pipe_frame_rate = FrameRateCalculator(1)

        while self._running.get():
            clock.tick(self._fps)

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.MOUSEMOTION:
                    x, y = event.pos
                    cmd = MouseMoveCommand(self._socket_writer)
                    cmd.execute(x, y)

                elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP:
                    x, y = event.pos
                    button = MouseButton(event.button)
                    state = ButtonState.PRESS if event.type == pygame.MOUSEBUTTONDOWN else ButtonState.RELEASE
                    cmd = MouseClickCommand(self._socket_writer)
                    cmd.execute(x, y, button, state)

                elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                    key_code = ASCIIEnum(event.key)
                    state = ButtonState.PRESS if event.type == pygame.KEYDOWN else ButtonState.RELEASE
                    cmd = KeyboardEventCommand(self._socket_writer)
                    cmd.execute(key_code, state)

                elif event.type == pygame.VIDEORESIZE:
                    self._width, self._height = event.w, event.h

                elif event.type == pygame.QUIT:
                    self.stop()

            # Receive data object
            data = self._read_decode_pipeline.get()

            # If data from pipeline are available
            if data is not None:
                screen.fill((0, 0, 0))

                # Track fps of pipeline
                pipe_frame_rate.tick()

                # Handle video data
                video_data, frames = data
                width = video_data.get_width()
                height = video_data.get_height()
                data = video_data.get_data()

                # Update minute bandwidth statistics
                self._bandwidth_monitor.register_received_bytes(len(data))

                # Update bandwidth state machine
                self._bandwidth_state_machine.update_state(self._bandwidth_monitor.get_bandwidth())

                # Render only last frame
                frame = frames[-1]
                img = pygame.image.frombuffer(frame, (width, height), "RGB")

                # Calculate new width and height while preserving aspect ratio
                x_offset, y_offset, new_width, new_height = self._calculate_ratio(width, height)

                # Rescale frame
                img_scaled = pygame.transform.scale(img, (new_width, new_height))

                # Render frame
                screen.blit(img_scaled, (x_offset, y_offset))

                # Render FPS, Pipeline FPS and bandwidth
                bandwidth = self._bandwidth_monitor.get_bandwidth()
                layout = FlexboxLayout(mode="column", align_items="start")
                layout.add_child(TextLayout(f"FPS: {clock.get_fps():.2f}", font_size=20))
                layout.add_child(TextLayout(f"Pipeline FPS: {pipe_frame_rate.get_fps():.2f}", font_size=20))
                layout.add_child(TextLayout(f"Bandwidth: {BandwidthFormatter.format(bandwidth)}", font_size=20))
                layout.render(screen)

                # Render apply
                pygame.display.flip()

        pygame.quit()

    def stop(self) -> None:
        self._connection.stop()
        self._read_decode_pipeline.stop()
        self._running.set(False)

    def _calculate_ratio(self, width: int, height: int) -> Tuple[int, int, int, int]:
        aspect_ratio = float(width) / float(height)

        new_height = self._height
        new_width = int(aspect_ratio * new_height)

        if new_width > self._width:
            new_width = self._width
            new_height = int(new_width / aspect_ratio)

        x_offset = (self._width - new_width) // 2
        y_offset = (self._height - new_height) // 2

        return x_offset, y_offset, new_width, new_height


HOST = "127.0.0.1"
PORT = 8085
FPS = 45

if __name__ == "__main__":
    server = Server(HOST, PORT, 1366, 720, FPS)
    server.run()
