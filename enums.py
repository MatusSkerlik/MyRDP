from enum import IntEnum, EnumMeta, Enum


class PacketType(IntEnum):
    """
    Enumeration representing different packet types for the screen capture application.
    """
    MOUSE_CLICK = 0x01
    MOUSE_MOVE = 0x02
    VIDEO_DATA = 0x03
    KEYBOARD_EVENT = 0x04
    # Add more packet types as needed


class MouseButton(IntEnum):
    """
    Enumeration representing different mouse button identifiers.
    """
    LEFT = 0x01
    MIDDLE = 0x02
    RIGHT = 0x03


class ButtonState(IntEnum):
    """
    Enumeration representing the state of a button (pressed or released).
    """
    PRESS = 0x01
    RELEASE = 0x00


class ASCIIEnumMeta(EnumMeta):
    """
    Custom metaclass to generate an ASCII character enumeration during class creation.
    """

    def __new__(mcs, name, bases, classdict):
        temp_enum = {}
        for i in range(128):
            char_name = f"CHAR_{chr(i)}"
            temp_enum[char_name] = i
        new_class = super().__new__(mcs, name, bases, classdict)
        for key, value in temp_enum.items():
            new_class._member_map_[key] = value
            new_class._value2member_map_[value] = value
            new_class._member_names_.append(key)
            new_class._member_type_ = int
        return new_class


class ASCIIEnum(IntEnum, metaclass=ASCIIEnumMeta):
    """
    Enumeration representing ASCII characters.
    Automatically populated with ASCII character codes using the ASCIIEnumMeta metaclass.
    """
    pass
