from typing import Tuple

import pygame

from bandwidth import BandwidthMonitor
from command import MouseMoveNetworkCommand, MouseClickNetworkCommand, KeyboardEventNetworkCommand
from connection import AutoReconnectServer
from constants import HOST, PORT, FPS
from enums import MouseButton, ButtonState
from fps import FrameRateCalculator
from keyboard import KEY_MAPPING
from lock import AutoLockingValue
from pipeline import ReadDecodePipeline
from pread import SocketDataReader
from processor import PacketProcessor
from pwrite import SocketDataWriter
from render import FlexboxLayout, TextLayout, ThreeDotsTextLayout


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
        _window_width (int): The width of the pygame window.
        _window_height (int): The height of the pygame window.
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

        self._window_width = width
        self._window_height = height
        self._client_width = None
        self._client_height = None
        self._scaled_width = None
        self._scaled_height = None
        self._x_offset = None
        self._y_offset = None
        self._fps = fps
        self._caption = caption
        self._last_image = None

        self._running = False
        self._connection = AutoReconnectServer(host, port)
        self._socket_reader = SocketDataReader(self._connection, buffer_size=4096)
        self._socket_writer = SocketDataWriter(self._connection)
        self._packet_processor = PacketProcessor(self._socket_reader)
        self._read_decode_pipeline = ReadDecodePipeline(fps, self._packet_processor)
        self._bandwidth_monitor = BandwidthMonitor()

    def run(self) -> None:
        if self._running:
            raise RuntimeError("The 'run' method can only be called once")
        self._running = True
        self._connection.start()
        self._read_decode_pipeline.start()
        self._packet_processor.start()

        pygame.init()
        screen = pygame.display.set_mode((self._window_width, self._window_height + 20), pygame.RESIZABLE)
        pygame.display.set_caption(self._caption)
        clock = pygame.time.Clock()
        pipe_frame_rate = FrameRateCalculator(1)

        while self._running:
            clock.tick(self._fps)

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.MOUSEMOTION:
                    _x, _y = event.pos
                    if self._if_event_sent_is_possible() and self._if_cords_domain_in_range(_x, _y):
                        x, y = self._recalculate_cords(_x, _y)
                        cmd = MouseMoveNetworkCommand(self._socket_writer, x, y)
                        # cmd.execute()

                elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP:
                    _x, _y = event.pos
                    if self._if_event_sent_is_possible() and self._if_cords_domain_in_range(_x, _y):
                        x, y = self._recalculate_cords(_x, _y)

                        if event.button == pygame.BUTTON_LEFT:
                            button = MouseButton.LEFT
                        elif event.button == pygame.BUTTON_RIGHT:
                            button = MouseButton.RIGHT
                        elif event.button == pygame.BUTTON_WHEELUP:
                            button = MouseButton.MIDDLE_WHEEL_UP
                        elif event.button == pygame.BUTTON_WHEELDOWN:
                            button = MouseButton.MIDDLE_WHEEL_DOWN
                        else:
                            continue

                        state = ButtonState.PRESS if event.type == pygame.MOUSEBUTTONDOWN else ButtonState.RELEASE
                        cmd = MouseClickNetworkCommand(self._socket_writer, x, y, button, state)
                        cmd.execute()

                elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                    try:
                        key_code = KEY_MAPPING[event.key]
                    except KeyError:
                        # TODO we are skipping not supported keys
                        continue
                    state = ButtonState.PRESS if event.type == pygame.KEYDOWN else ButtonState.RELEASE
                    cmd = KeyboardEventNetworkCommand(self._socket_writer, key_code, state)
                    cmd.execute()

                elif event.type == pygame.VIDEORESIZE:
                    self._window_width, self._window_height = event.w, event.h

                elif event.type == pygame.QUIT:
                    self.stop()

            screen.fill((0, 0, 0))

            # Receive data object
            data = self._read_decode_pipeline.pop_result()

            # If data from pipeline are available
            if data and len(data) > 0:
                # Track fps of pipeline
                pipe_frame_rate.tick()

                # Handle video data
                video_data, frames = data
                width = video_data.get_width()
                height = video_data.get_height()
                data = video_data.get_data()

                # Update client width and height
                self._client_width = width
                self._client_height = height

                # Update minute bandwidth statistics
                self._bandwidth_monitor.register_received_bytes(len(data))

                # Render only last frame
                frame = frames[-1]
                img = pygame.image.frombuffer(frame, (width, height), "RGB")

                # Calculate new width and height while preserving aspect ratio
                x_offset, y_offset, new_width, new_height = self._calculate_ratio(width, height)

                # Update offset
                self._x_offset = x_offset
                self._y_offset = y_offset

                # Update scaled width & height
                self._scaled_width = new_width
                self._scaled_height = new_height

                # Rescale frame
                self._last_image = pygame.transform.scale(img, (self._scaled_width, self._scaled_height))

            is_connected = self._connection.is_connected()
            if is_connected:
                # Render frame if there is connection
                if self._last_image:
                    screen.blit(self._last_image, (self._x_offset, self._y_offset))
            else:
                # Reset bandwidth monitor
                self._bandwidth_monitor.reset()

            # Render FPS, Pipeline FPS and bandwidth
            (FlexboxLayout()
             .set_mode("column")
             .set_align_items("start")
             .set_background((0, 0, 0))
             .add_child(TextLayout(f"FPS: {clock.get_fps():.2f}"))
             .add_child(TextLayout(f"Pipeline FPS: {pipe_frame_rate.get_fps():.2f}"))
             .set_text_size(24)
             .render(screen))

            # Render status bar
            bandwidth = self._bandwidth_monitor.get_bandwidth_str()
            (FlexboxLayout()
             .set_x(0)
             .set_y(self._window_height)
             .set_width(self._window_width)
             .set_height(20)
             .set_align_items("center")
             .set_justify_content("space-between")
             .set_background((46, 204, 113) if is_connected else (192, 57, 43))
             .add_child(
                TextLayout(f"Connected") if is_connected else
                ThreeDotsTextLayout(f"Disconnected"))
             .add_child(TextLayout(f"Bandwidth '{bandwidth}'"))
             .set_text_size(24)
             .render(screen))

            # Render mouse coordinates
            # MouseCoordinates().render(screen)

            # Render apply
            pygame.display.flip()

        pygame.quit()

    def stop(self) -> None:
        self._running = False
        self._connection.stop()
        self._packet_processor.stop()
        self._read_decode_pipeline.stop()

    def _calculate_ratio(self, width: int, height: int) -> Tuple[int, int, int, int]:
        aspect_ratio = float(width) / float(height)

        new_height = self._window_height
        new_width = int(aspect_ratio * new_height)

        if new_width > self._window_width:
            new_width = self._window_width
            new_height = int(new_width / aspect_ratio)

        x_offset = (self._window_width - new_width) // 2
        y_offset = (self._window_height - new_height) // 2

        return x_offset, y_offset, new_width, new_height

    def _if_event_sent_is_possible(self):
        return (self._client_width is not None
                and self._client_height is not None
                and self._x_offset is not None
                and self._y_offset is not None
                and self._scaled_width is not None
                and self._scaled_height is not None)

    def _if_cords_domain_in_range(self, x: int, y: int):
        return (self._x_offset <= x <= self._window_width - self._x_offset * 2
                and self._y_offset <= y <= self._window_height - self._y_offset * 2)

    def _recalculate_cords(self, x: int, y: int):
        return (
            int((x - self._x_offset) * (self._client_width / self._scaled_width)),
            int((y - self._y_offset) * (self._client_height / self._scaled_height))
        )


if __name__ == "__main__":
    try:
        server = Server(HOST, PORT, 1366, 720, FPS)
        server.run()
    except KeyboardInterrupt:
        pass
