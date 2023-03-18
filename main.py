from threading import Thread

from client import Client
from server import Server

HOST = "127.0.0.1"
PORT = 8080

if __name__ == "__main__":
    server = Server(HOST, PORT)
    client = Client(HOST, PORT, 800, 600, 30)

    thread_server = Thread(target=server.run)
    thread_client = Thread(target=client.run)

    thread_server.start()
    thread_client.start()

    thread_server.join()
    thread_client.join()
