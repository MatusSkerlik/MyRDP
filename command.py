from abc import ABC, abstractmethod

import pyautogui

from dao import MouseMoveData, MouseClickData, KeyboardData
from enums import MouseButton, ButtonState, ASCIIEnum
from packet import Packet
from pfactory import MouseMovePacketFactory, MouseClickPacketFactory, KeyboardEventPacketFactory
from pwrite import SocketDataWriter


class Command(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError


class NetworkCommand(Command):
    def __init__(self, socket_writer: SocketDataWriter, packet: Packet):
        self._socket_writer = socket_writer
        self._packet = packet

    def execute(self, *args, **kwargs):
        try:
            self._socket_writer.write_packet(self._packet, False)
        except ConnectionError:
            # There is no connection, ignore
            pass


class MouseMoveNetworkCommand(NetworkCommand):

    def __init__(self, socket_writer: SocketDataWriter, x: int, y: int):
        packet = MouseMovePacketFactory.create_packet(x, y)
        super().__init__(socket_writer, packet)


class MouseClickNetworkCommand(NetworkCommand):

    def __init__(self, socket_writer: SocketDataWriter, x: int, y: int, button: MouseButton, state: ButtonState):
        packet = MouseClickPacketFactory.create_packet(x, y, button, state)
        super().__init__(socket_writer, packet)


class KeyboardEventNetworkCommand(NetworkCommand):

    def __init__(self, socket_writer: SocketDataWriter, key_code: ASCIIEnum, state: ButtonState):
        packet = KeyboardEventPacketFactory.create_packet(key_code, state)
        super().__init__(socket_writer, packet)


class MouseMoveCommand(Command):

    def __init__(self, mouse_move: MouseMoveData) -> None:
        self._mouse_move = mouse_move

    def execute(self, *args, **kwargs):
        x = self._mouse_move.get_x()
        y = self._mouse_move.get_y()
        try:
            pyautogui.moveTo(x, y)
        except pyautogui.FailSafeException:
            pass


class MouseClickCommand(Command):

    def __init__(self, mouse_click: MouseClickData) -> None:
        self._mouse_click = mouse_click

    def execute(self, *args, **kwargs):
        x, y = self._mouse_click.get_x(), self._mouse_click.get_y()
        state, button = self._mouse_click.get_state(), self._mouse_click.get_button()

        if button == MouseButton.MIDDLE_UP:
            pyautogui.scroll(0.5)
        elif button == MouseButton.MIDDLE_DOWN:
            pyautogui.scroll(-0.5)
        elif button in (MouseButton.LEFT, MouseButton.RIGHT):
            pyautogui.mouseDown(x, y, button.name.lower()) if state == ButtonState.PRESS \
                else pyautogui.mouseUp(x, y, button.name.lower())
        else:
            raise RuntimeError("Unexpected mouse button")


class KeyboardEventCommand(Command):

    def __init__(self, keyboard_event: KeyboardData) -> None:
        self._keyboard_event = keyboard_event

    def execute(self, *args, **kwargs):
        state = self._keyboard_event.get_state()
        key = self._keyboard_event.get_key()

        if state == ButtonState.PRESS:
            pyautogui.keyDown(chr(key))
        elif state == ButtonState.RELEASE:
            pyautogui.keyUp(chr(key))
