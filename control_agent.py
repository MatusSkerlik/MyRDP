import pygame
from typing import Tuple

from bandwidth import BandwidthMonitor
from command import MouseMoveNetworkCommand, MouseClickNetworkCommand, KeyboardEventNetworkCommand
from connection import Connection
from constants import *
from enums import MouseButton, ButtonState
from fps import FrameRateCalculator
from keyboard import KEY_MAPPING
from pipeline import ReadDecodePipeline
from pread import SocketDataReader
from processor import PacketProcessor
from pwrite import SocketDataWriter
from render import FlexboxLayout, TextLayout


class ControlAgent:

    def __init__(self,
                 local_ip: str,
                 local_port: int,
                 remote_ip: str,
                 remote_port: int,
                 width: int,
                 height: int,
                 fps: int,
                 caption: str = "Server") -> None:

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
        self._connection = Connection(local_ip, local_port, remote_ip, remote_port)
        self._socket_reader = SocketDataReader(self._connection, buffer_size=4096)
        self._socket_writer = SocketDataWriter(self._connection)
        self._packet_processor = PacketProcessor(self._socket_reader)
        self._read_decode_pipeline = ReadDecodePipeline(self._packet_processor)
        self._bandwidth_monitor = BandwidthMonitor()

    def run(self) -> None:
        if self._running:
            raise RuntimeError("The 'run' method can only be called once")
        self._packet_processor.start()
        self._read_decode_pipeline.start()
        self._running = True

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

            data = self._read_decode_pipeline.pop_result()

            # If data from pipeline are available
            if data is not None:
                # Track fps of pipeline
                pipe_frame_rate.tick()

                # Handle video data
                video_data, frames = data
                width = video_data.get_width()
                height = video_data.get_height()

                # Update client width and height
                self._client_width = width
                self._client_height = height

                # Update minute bandwidth statistics
                self._bandwidth_monitor.register_received_bytes(len(video_data.get_data()))

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
                screen.blit(self._last_image, (self._x_offset, self._y_offset))
            elif self._last_image:
                screen.blit(self._last_image, (self._x_offset, self._y_offset))

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
             .add_child(TextLayout(f"Bandwidth '{bandwidth}'"))
             .set_text_size(24)
             .render(screen))

            # Render mouse coordinates
            # MouseCoordinates().render(screen)

            # Render apply
            pygame.display.flip()

        pygame.quit()

    def stop(self) -> None:
        self._packet_processor.stop()
        self._read_decode_pipeline.stop()
        self._running = False

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
        server = ControlAgent(CONTROL_AGENT_IP, CONTROL_AGENT_PORT, OBEDIENT_AGENT_IP, OBEDIENT_AGENT_PORT, 1366, 720,
                              FPS)
        server.run()
    except KeyboardInterrupt:
        pass
