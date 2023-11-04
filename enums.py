from enum import IntEnum


class PacketType(IntEnum):
    """
    Enumeration representing different packet types for the screen capture application.
    """
    SYNC = 0
    VIDEO_DATA = 1
    MOUSE_CLICK = 2
    MOUSE_MOVE = 3
    KEYBOARD_EVENT = 4
    # Add more packet types as needed


class MouseButton(IntEnum):
    """
    Enumeration representing different mouse button identifiers.
    """
    LEFT = 0x01
    MIDDLE_WHEEL_UP = 0x02
    MIDDLE_WHEEL_DOWN = 0x03
    RIGHT = 0x04


class ButtonState(IntEnum):
    """
    Enumeration representing the state of a button (pressed or released).
    """
    PRESS = 0x01
    RELEASE = 0x00
