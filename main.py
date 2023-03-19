from threading import Thread

from client import Client
from server import Server

HOST = "127.0.0.1"
PORT = 8080
FPS = 30

if __name__ == "__main__":
    server = Server(HOST, PORT, 1366, 720, FPS)
    client = Client(HOST, PORT, 200, 200, FPS)

    thread_server = Thread(target=server.run)
    thread_client = Thread(target=client.run)

    thread_server.start()
    thread_client.start()

    thread_server.join()
    thread_client.join()
