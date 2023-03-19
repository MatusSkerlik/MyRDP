import pygame

from bandwidth import BandwidthMonitor, BandwidthStateMachine
from command import MouseMoveCommand, MouseClickCommand, KeyboardEventCommand
from decode import AbstractDecoderStrategy, MPEGTS_H264Decoder
from enums import MouseButton, ButtonState, ASCIIEnum
from lock import AutoLockingValue
from network import SocketFactory
from pread import SocketDataReader
from pwrite import SocketDataWriter


class Server:
    def __init__(self, host: str, port: int, width: int, height: int, fps: int) -> None:
        self._host = host
        self._port = port

        self._width = width
        self._height = height
        self._fps = fps

        self._running = AutoLockingValue(False)
        self._server_socket = SocketFactory.bind(host, port)
        print(f"Server listening on {self._host}:{self._port}")
        self._client_socket, self._client_ip = self._server_socket.accept()
        print(f"Connected to client at {self._client_ip}")
        self._socket_reader = SocketDataReader(self._client_socket)
        self._socket_writer = SocketDataWriter(self._client_socket)
        self._monitor = BandwidthMonitor()
        self._bandwidth_state_machine = BandwidthStateMachine()
        self._decoder_strategy = MPEGTS_H264Decoder()

    def set_decoding_strategy(self, decoder_strategy: AbstractDecoderStrategy):
        self._decoder_strategy = decoder_strategy

    def is_running(self):
        return self._running.get()

    def run(self) -> None:
        if self._running.get():
            raise RuntimeError("The 'run' method can only be called once")
        self._running.set(True)

        pygame.init()
        clock = pygame.time.Clock()
        screen = pygame.display.set_mode((self._width, self._height))

        while self._running.get():
            # Receive video data
            video_data = self._socket_reader.read_packet()
            print(video_data)
            if not video_data:
                continue

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
                if event.type == pygame.MOUSEMOTION:
                    x, y = event.pos
                    cmd = MouseMoveCommand(self._socket_writer)
                    cmd.execute(x, y)

                elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP:
                    x, y = event.pos
                    button = MouseButton(event.button)
                    state = ButtonState.PRESSED if event.type == pygame.MOUSEBUTTONDOWN else ButtonState.RELEASED
                    cmd = MouseClickCommand(self._socket_writer)
                    cmd.execute(x, y, button, state)

                elif event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                    key_code = ASCIIEnum(event.key)
                    state = ButtonState.PRESSED if event.type == pygame.KEYDOWN else ButtonState.RELEASED
                    cmd = KeyboardEventCommand(self._socket_writer)
                    cmd.execute(key_code, state)

                elif event.type == pygame.QUIT:
                    self.stop()

            clock.tick(self._fps)

    def stop(self) -> None:
        if self._running.get():
            self._running.set(False)
            self._server_socket.close()
            pygame.quit()


HOST = "127.0.0.1"
PORT = 8081
FPS = 30

if __name__ == "__main__":
    server = Server(HOST, PORT, 1366, 720, FPS)
    server.run()
