import queue
import time
from queue import Queue
from typing import Dict, Union

from command import MouseMoveCommand, MouseClickCommand, KeyboardEventCommand
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


class CommandProcessor(Task):

    def __init__(self, packet_processor: PacketProcessor):
        super().__init__()
        self._packet_processor = packet_processor

    def __str__(self) -> str:
        return f"CommandExecutor()"

    def run(self):
        while self.running.getv():

            mouse_move: MouseMoveData = self._packet_processor.get_packet_data(PacketType.MOUSE_MOVE)
            if mouse_move:
                cmd = MouseMoveCommand(mouse_move)
                cmd.execute()

            mouse_click: MouseClickData = self._packet_processor.get_packet_data(PacketType.MOUSE_CLICK)
            if mouse_click:
                cmd = MouseClickCommand(mouse_click)
                cmd.execute()

            keyboard_data: KeyboardData = self._packet_processor.get_packet_data(PacketType.KEYBOARD_EVENT)
            if keyboard_data:
                cmd = KeyboardEventCommand(keyboard_data)
                cmd.execute()

            time.sleep(0.005)
