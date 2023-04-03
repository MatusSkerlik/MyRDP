import os
import signal
import subprocess
import sys
import time


def main():
    server_script = "server.py"
    client_script = "client.py"

    server_process = subprocess.Popen([sys.executable, server_script])
    client_process = subprocess.Popen([sys.executable, client_script])

    try:
        while server_process.poll() is None and client_process.poll() is None:
            time.sleep(0.025)

        if server_process.poll() is None:
            print("Client process exited, terminating server process...")
            os.kill(server_process.pid, signal.SIGTERM)

        elif client_process.poll() is None:
            print("Server process exited, terminating client process...")
            os.kill(client_process.pid, signal.SIGTERM)

    except KeyboardInterrupt:
        print("KeyboardInterrupt received, terminating processes...")
        os.kill(server_process.pid, signal.SIGTERM)
        os.kill(client_process.pid, signal.SIGTERM)

    except Exception as e:
        print(f"Unexpected error occurred: {e}, terminating processes...")
        os.kill(server_process.pid, signal.SIGTERM)
        os.kill(client_process.pid, signal.SIGTERM)


if __name__ == "__main__":
    main()
