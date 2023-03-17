import socket


class SocketFactory:
    """
    A factory class for creating and binding TCP sockets.
    """

    @staticmethod
    def connect(host: str, port: int) -> socket.socket:
        """
        Create a new TCP socket and bind it to the given host and port.

        :param host: The host address to bind the socket to.
        :param port: The port number to bind the socket to.
        :return: A new socket.socket instance configured for TCP and connected to the specified host and port.
        """
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((host, port))
        return tcp_socket
