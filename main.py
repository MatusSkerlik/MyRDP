import multiprocessing
import subprocess
import sys
import time


def start_server():
    subprocess.run([sys.executable, "server.py"])


def start_client():
    subprocess.run([sys.executable, "client.py"])


if __name__ == "__main__":
    server_process = multiprocessing.Process(target=start_server)
    client_process = multiprocessing.Process(target=start_client)

    server_process.start()
    time.sleep(1)
    client_process.start()

    server_process.join()
    client_process.join()
