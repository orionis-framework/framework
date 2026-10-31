import socket
from importlib import import_module
from uvicorn.config import Config

class TcpNoDelayConfig(Config):
    """Keep TCP_NODELAY enabled on sockets shared by benchmark workers."""

    def bind_socket(self) -> socket.socket:
        """
        Bind the native listener and disable Nagle before workers inherit it.

        Returns
        -------
        socket.socket
            Native listener with TCP_NODELAY enabled for IPv4 or IPv6.

        Raises
        ------
        OSError
            If configuring TCP_NODELAY fails; the listener is closed first.
        """
        listener = super().bind_socket()
        if listener.family not in {socket.AF_INET, socket.AF_INET6}:
            return listener
        try:
            listener.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            listener.close()
            raise
        return listener

def main() -> None:
    """
    Run Uvicorn's unchanged CLI using the benchmark socket configuration.

    Returns
    -------
    None
        Restore the native configuration after the CLI returns or raises.
    """
    entrypoint = import_module("uvicorn.main")
    native_config = entrypoint.Config
    entrypoint.Config = TcpNoDelayConfig
    try:
        entrypoint.main()
    finally:
        entrypoint.Config = native_config

if __name__ == "__main__":
    main()
