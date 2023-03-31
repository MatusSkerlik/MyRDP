import time

from command import MouseMoveCommand, MouseClickCommand, KeyboardEventCommand
from dao import MouseMoveData, MouseClickData, KeyboardData
from enums import PacketType
from processor import StreamPacketProcessor
from thread import Task


class CommandExecutor(Task):

    def __init__(self, stream_packet_processor: StreamPacketProcessor):
        super().__init__()
        self._stream_packet_processor = stream_packet_processor

    def run(self):
        while self.running.getv():
            time.sleep(0.005)

            mouse_move: MouseMoveData = self._stream_packet_processor.get_packet_data(PacketType.MOUSE_MOVE)
            if mouse_move:
                cmd = MouseMoveCommand(mouse_move)
                cmd.execute()

            mouse_click: MouseClickData = self._stream_packet_processor.get_packet_data(PacketType.MOUSE_CLICK)
            if mouse_click:
                cmd = MouseClickCommand(mouse_click)
                cmd.execute()

            keyboard_data: KeyboardData = self._stream_packet_processor.get_packet_data(PacketType.KEYBOARD_EVENT)
            if keyboard_data:
                cmd = KeyboardEventCommand(keyboard_data)
                cmd.execute()
