from abc import ABC, abstractmethod

from enums import MouseButton, ButtonState, ASCIIEnum
from pfactory import MouseMovePacketFactory, MouseClickPacketFactory, KeyboardEventPacketFactory
from pwrite import SocketDataWriter


class Command(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError


class MouseMoveCommand(Command):
    def __init__(self, socket_writer: SocketDataWriter):
        self._writer = socket_writer

    def execute(self, x: int, y: int):
        packet = MouseMovePacketFactory.create_packet(x, y)
        self._writer.write_packet(packet)


class MouseClickCommand(Command):
    def __init__(self, socket_writer: SocketDataWriter):
        self._writer = socket_writer

    def execute(self, x: int, y: int, button: MouseButton, state: ButtonState):
        packet = MouseClickPacketFactory.create_packet(x, y, button, state)
        self._writer.write_packet(packet)


class KeyboardEventCommand(Command):
    def __init__(self, socket_writer: SocketDataWriter):
        self._writer = socket_writer

    def execute(self, key_code: ASCIIEnum, state: ButtonState):
        packet = KeyboardEventPacketFactory.create_packet(key_code, state)
        self._writer.write_packet(packet)