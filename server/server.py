import pygame
from pygame import QUIT

from lock import AutoLockingValue
from network import SocketFactory
from pread import SocketDataReader
from server.bandwidth import BandwidthMonitor, BandwidthStateMachine
from server.decode import PyAvH264Decoder, AbstractDecoderStrategy


class Server:
    def __init__(self, host: str, port: int, width: int, height: int, fps: int) -> None:
        self._host = host
        self._port = port

        self._width = width
        self._height = height
        self._fps = fps

        self._running = AutoLockingValue(False)
        self._socket = SocketFactory.bind(host, port)
        self._socket_reader = SocketDataReader(self._socket)
        self._monitor = BandwidthMonitor()
        self._bandwidth_state_machine = BandwidthStateMachine()
        self._decoder_strategy = PyAvH264Decoder()

    def set_decoding_strategy(self, decoder_strategy: AbstractDecoderStrategy):
        self._decoder_strategy = decoder_strategy

    def is_running(self):
        return self._running.get()

    def run(self) -> None:
        if self._running.get():
            raise RuntimeError("The 'run' method can only be called once")
        self._running.set(True)

        print(f"Server listening on {self._host}:{self._port}")
        client_socket, client_addr = self._socket.accept()
        print(f"Connected to client at {client_addr}")

        pygame.init()
        clock = pygame.time.Clock()
        screen = pygame.display.set_mode((self._width, self._height))

        while self._running.get():
            # Receive video data
            video_data = self._socket_reader.read_packet()

            # Update minute bandwidth statistics
            self._monitor.register_received_bytes(len(video_data))

            # Update bandwidth state machine
            self._bandwidth_state_machine.update_state(self._monitor.get_bandwidth())

            # Handle received data and render frames
            frames = self._decoder_strategy.decode_packet(video_data)

            # Render only last frame
            if len(frames) > 0:
                frame = frames[-1]
                img = pygame.image.frombuffer(frame.planes[0], (frame.width, frame.height), "RGB")

                # Calculate new width and height while preserving aspect ratio
                aspect_ratio = float(frame.width) / float(frame.height)
                new_height = self._height
                new_width = int(aspect_ratio * new_height)
                if new_width > self._width:
                    new_width = self._width
                    new_height = int(new_width / aspect_ratio)

                img_scaled = pygame.transform.scale(img, (new_width, new_height))
                x_offset = (self._width - new_width) // 2
                y_offset = (self._height - new_height) // 2

                screen.fill((0, 0, 0))
                screen.blit(img_scaled, (x_offset, y_offset))
                pygame.display.flip()

            # Handle events
            for event in pygame.event.get():
                if event.type == QUIT:
                    self._running.set(False)

            clock.tick(self._fps)

    def stop(self) -> None:
        if self._running.get():
            self._running.set(False)
            self._socket.close()
            pygame.quit()
