import queue
import threading
import time
from queue import Queue
from typing import Dict, Union

from dao import AbstractDataObject
from enums import PacketType
from lock import AutoLockingValue, AutoLockingProxy
from pread import SocketDataReader
from pwrite import SocketDataWriter


class StreamPacketProcessor(AutoLockingProxy):
    def __init__(self, reader: SocketDataReader, writer: SocketDataWriter):
        self._running = AutoLockingValue(False)
        self._socket_data_reader = reader
        self._socket_data_writer = writer
        self._packet_queues: Dict[PacketType, Queue] = {ptype: Queue(256) for ptype in PacketType}
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        self._running = False
        self._thread.join()

    def get_packet_data(self, packet_type: PacketType) -> Union[None, AbstractDataObject]:
        try:
            return self._packet_queues.get(packet_type).get_nowait()
        except queue.Empty:
            return None

    def _run(self):
        while self._running:
            try:
                packet_type, data_object = self._socket_data_reader.read_packet()
                try:
                    self._packet_queues.get(packet_type).put_nowait(data_object)
                except queue.Full:
                    pass
                time.sleep(0.01)
            except ConnectionError as e:
                print(f"Connection error: {e}")
                time.sleep(0.01)
