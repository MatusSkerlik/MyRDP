import os

HOST = (os.getenv("RDP_SERVER_IP") or "127.0.0.1")
PORT = (os.getenv("RDP_SERVER_PORT") or 8082)
FPS = 30
