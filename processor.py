import queue
import threading
import time
from queue import Queue
from typing import Dict, Union

from dao import MouseMoveData, MouseClickData, KeyboardData
from enums import PacketType
from lock import AutoLockingValue
from pread import SocketDataReader
from pwrite import SocketDataWriter


class StreamPacketProcessor:
    def __init__(self, reader: SocketDataReader, writer: SocketDataWriter):
        self._running = AutoLockingValue(False)
        self._socket_data_reader = reader
        self._socket_data_writer = writer
        self._packet_queues: AutoLockingValue[Dict[PacketType, Queue]] = (
            AutoLockingValue({ptype: Queue() for ptype in PacketType})
        )
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True

    def start(self):
        self._running.setv(True)
        self._thread.start()

    def stop(self):
        self._running.setv(False)
        self._thread.join()

    def get_packet_data(self, packet_type: PacketType) -> Union[None, MouseMoveData, MouseClickData, KeyboardData]:
        try:
            return self._packet_queues.get(packet_type).get_nowait()
        except queue.Empty:
            return None

    def _run(self):
        while self._running.getv():
            try:
                packet_type, data_object = self._socket_data_reader.read_packet()
                try:
                    self._packet_queues.get(packet_type).put_nowait(data_object)
                except queue.Full:
                    pass
            except ConnectionError:
                time.sleep(0.01)
                pass
