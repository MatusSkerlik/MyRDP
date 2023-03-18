import pygame

from lock import AutoLockingValue
from network import SocketFactory
from pread import SocketDataReader

BUFFER_SIZE = 4096


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.running = AutoLockingValue(False)
        self.socket = SocketFactory.bind(host, port)
        self.socket_reader = SocketDataReader(self.socket)

    def run(self):
        self.running.set(True)

        print(f"Server listening on {self.host}:{self.port}")
        client_socket, client_addr = self.socket.accept()
        print(f"Connected to client at {client_addr}")

        pygame.init()
        clock = pygame.time.Clock()
        screen = None
        container = av.open(None, "r", format="mp4")

        while self.running.get():
            video_data = self.socket_reader.read_packet()
            # Handle received data and render frames
            video_packet = av.Packet(video_data)
            container.decode(video_packet)
            for frame in container.decode(video_packet):
                if screen is None:
                    screen = pygame.display.set_mode((frame.width, frame.height))
                img = pygame.image.frombuffer(frame.planes[0], (frame.width, frame.height), "RGB")
                screen.blit(img, (0, 0))
                pygame.display.flip()
                clock.tick(30)

    def stop(self):
        if self.running.get():
            self.running.set(False)
            self.socket.close()
            pygame.quit()
