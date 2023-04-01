import queue
import time
from queue import Queue
from typing import Dict, Union

from connection import NoDataAvailableError, NoConnection
from dao import MouseMoveData, MouseClickData, KeyboardData
from enums import PacketType
from lock import AutoLockingValue
from pread import SocketDataReader
from thread import Task


class PacketProcessor(Task):

    def __init__(self, reader: SocketDataReader):
        super().__init__()

        self._socket_data_reader = reader
        self._packet_queues: AutoLockingValue[Dict[PacketType, Queue]] = (
            AutoLockingValue({ptype: Queue() for ptype in PacketType})
        )

    def get_packet_data(self, packet_type: PacketType) -> Union[None, MouseMoveData, MouseClickData, KeyboardData]:
        try:
            return self._packet_queues.get(packet_type).get_nowait()
        except queue.Empty:
            return None

    def run(self):
        while self.running.getv():
            try:
                packet_type, data_object = self._socket_data_reader.read_packet()
                try:
                    self._packet_queues.get(packet_type).put_nowait(data_object)
                except queue.Full:
                    pass
            except NoConnection:
                # There is connection lost
                time.sleep(0.01)
            except NoDataAvailableError:
                # There are no packets in stream available
                time.sleep(0.01)
            except RuntimeError:
                # Application shutdown
                pass
