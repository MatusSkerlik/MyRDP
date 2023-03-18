import socket


class SocketFactory:
    """
    A factory class for creating and configuring TCP sockets.
    """

    @staticmethod
    def connect(host: str, port: int) -> socket.socket:
        """
        Creates a TCP socket and connects it to the specified host and port.

        Args:
            host (str): The hostname or IP address of the remote host to connect to.
            port (int): The port number to connect to on the remote host.

        Returns:
            socket.socket: A connected TCP socket object.
        """
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((host, port))
        return tcp_socket

    @staticmethod
    def bind(host: str, port: int) -> socket.socket:
        """
        Creates a TCP socket, binds it to the specified host and port, and starts listening for connections.

        Args:
            host (str): The hostname or IP address to bind the socket to.
            port (int): The port number to bind the socket to.

        Returns:
            socket.socket: A bound and listening TCP socket object.
        """
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.bind((host, port))
        tcp_socket.listen()
        return tcp_socket
