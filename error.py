class UnexpectedPacketTypeError(Exception):
    """
    Raised when the packet type is unexpected or unknown.
    """

    def __init__(self, packet_type: int):
        self.packet_type = packet_type
        super().__init__(f"Unexpected packet type: {packet_type}")
