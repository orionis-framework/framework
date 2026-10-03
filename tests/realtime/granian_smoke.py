"""Run real Granian loopback checks using a deliberately tiny test-only client."""

import argparse
import asyncio
import base64
import hashlib
import os
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
import msgspec

_ROOT = Path(__file__).resolve().parents[2]


def _require(condition: object, message: str) -> None:
    """
    Raise a clear smoke-test failure when one wire assertion fails.

    Parameters
    ----------
    condition : object
        Value whose truthiness determines whether the assertion passes.
    message : str
        Explanation reported for a failed assertion.

    Returns
    -------
    None
        Accept a truthy condition.

    Raises
    ------
    AssertionError
        If the condition is falsy.
    """
    if not condition:
        raise AssertionError(message)


def _available_port() -> int:
    """
    Reserve and release an ephemeral loopback port for the server process.

    Returns
    -------
    int
        Selected port, released for the test server to bind.
    """
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return candidate.getsockname()[1]


def _start_server(interface: str, port: int, log: int) -> subprocess.Popen:
    """
    Start only the requested test server without opening a visible window.

    Parameters
    ----------
    interface : str
        Granian interface, either asgi or rsgi.
    port : int
        Loopback port for the test server.
    log : int
        File descriptor receiving server output and errors.

    Returns
    -------
    subprocess.Popen
        Owned server process using the fixed test application.
    """
    command = [
        sys.executable, "-m", "granian", "--interface", interface,
        "--host", "127.0.0.1", "--port", str(port), "--workers", "1",
        "--loop", "asyncio", "--log-level", "warning",
        "tests.realtime._granian_application:app",
    ]
    return subprocess.Popen(  # noqa: S603 - Fixed local test module and CLI arguments.
        command, cwd=_ROOT, stdout=log, stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def _stop_server(process: subprocess.Popen) -> None:
    """
    Release the exact owned process tree, including Granian's worker.

    Parameters
    ----------
    process : subprocess.Popen
        Test server process to stop, if still running.

    Returns
    -------
    None
        Stop the owned server and await its exit.

    Raises
    ------
    RuntimeError
        If taskkill is unavailable on Windows.
    subprocess.TimeoutExpired
        If process termination exceeds its five-second deadline.
    """
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        executable = shutil.which("taskkill")
        if executable is None:
            error_msg = "Windows taskkill is required to release the test server tree"
            raise RuntimeError(error_msg)
        subprocess.run(  # noqa: S603 - PID belongs to the child created above.
            [executable, "/PID", str(process.pid), "/T", "/F"],
            check=False, capture_output=True, timeout=5,
        )
    else:
        process.terminate()
    process.wait(timeout=5)


class _Peer:
    """Exchange small RFC6455 frames without creating a public client library."""

    __slots__ = ("reader", "writer")

    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        """
        Own one TCP reader and writer for a test connection.

        Parameters
        ----------
        reader : asyncio.StreamReader
            Incoming TCP stream.
        writer : asyncio.StreamWriter
            Outgoing TCP stream.

        Returns
        -------
        None
            Store both streams for frame exchange.
        """
        self.reader = reader
        self.writer = writer

    @classmethod
    async def connect(cls, port: int, path: str) -> _Peer:
        """
        Complete the HTTP upgrade and verify the server's handshake hash.

        Parameters
        ----------
        port : int
            Loopback server port.
        path : str
            WebSocket route requested during the upgrade.

        Returns
        -------
        _Peer
            Connected peer with a verified WebSocket handshake.

        Raises
        ------
        AssertionError
            If the response status or handshake hash is invalid.
        """
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            "Connection: Upgrade\r\nUpgrade: websocket\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        writer.write(request.encode("ascii"))
        await writer.drain()
        try:
            headers = await reader.readuntil(b"\r\n\r\n")
            expected = base64.b64encode(hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii"),
            ).digest())
            _require(headers.startswith(b"HTTP/1.1 101"), headers.decode("latin-1"))
            _require(expected in headers, "Server returned an invalid upgrade hash")
            return cls(reader, writer)
        except BaseException:
            writer.close()
            await writer.wait_closed()
            raise

    async def frame(self, opcode: int, payload: bytes) -> None:
        """
        Send one masked, unfragmented client frame.

        Parameters
        ----------
        opcode : int
            RFC6455 frame operation code.
        payload : bytes
            Frame content supported by the test client's short length encoding.

        Returns
        -------
        None
            Write the masked frame and await TCP backpressure.
        """
        mask = secrets.token_bytes(4)
        length = len(payload)
        prefix = bytes((0x80 | opcode, 0x80 | length)) if length < 126 else (
            bytes((0x80 | opcode, 0xFE)) + struct.pack("!H", length)
        )
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.writer.write(prefix + mask + masked)
        await self.writer.drain()

    async def receive(self) -> tuple[int, bytes]:
        """
        Read a complete server frame, acknowledging transport pings.

        Returns
        -------
        tuple[int, bytes]
            Operation code and payload of the next non-ping server frame.

        Raises
        ------
        AssertionError
            If a server frame is fragmented or masked.
        asyncio.IncompleteReadError
            If the connection ends before the full frame is available.
        """
        while True:
            first, second = await self.reader.readexactly(2)
            _require(bool(first & 0x80), "Small test responses must not be fragmented")
            _require(not second & 0x80, "A server must not mask its frames")
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", await self.reader.readexactly(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", await self.reader.readexactly(8))[0]
            payload = await self.reader.readexactly(length)
            opcode = first & 0x0F
            if opcode == 9:
                await self.frame(10, payload)
                continue
            return opcode, payload

    async def close(self) -> None:
        """
        Perform a client close handshake and release the TCP connection.

        Returns
        -------
        None
            Request normal closure and release the writer on every exit path.

        Raises
        ------
        AssertionError
            If the server does not acknowledge the close frame.
        """
        try:
            await self.frame(8, struct.pack("!H", 1000))
            opcode, _ = await self.receive()
            _require(opcode == 8, "Server did not acknowledge the close frame")
        finally:
            self.writer.close()
            await self.writer.wait_closed()


async def _check_raw(port: int) -> None:
    """
    Verify Unicode text and binary echo over the installed Granian server.

    Parameters
    ----------
    port : int
        Loopback server port.

    Returns
    -------
    None
        Check both frame kinds and close the test connection.

    Raises
    ------
    AssertionError
        If a received frame differs from the sent frame.
    """
    peer = await _Peer.connect(port, "/echo")
    try:
        for opcode, payload in ((1, "¡Hola, 世界!".encode()), (2, b"\x00\xff\x80")):
            await peer.frame(opcode, payload)
            _require(await peer.receive() == (opcode, payload), "Raw echo mismatch")
    finally:
        await peer.close()


async def _check_hub(port: int, codec: str) -> None:
    """
    Check ready, scalar RPC and client-result correlation for one codec.

    Parameters
    ----------
    port : int
        Loopback server port.
    codec : str
        Route-selected json or msgpack codec.

    Returns
    -------
    None
        Verify ready metadata and bidirectional results, then close the peer.

    Raises
    ------
    AssertionError
        If handshake, envelope or correlation assertions fail.
    """
    peer = await _Peer.connect(port, "/" + codec)
    encode = msgspec.json.encode if codec == "json" else msgspec.msgpack.encode
    decode = msgspec.json.decode if codec == "json" else msgspec.msgpack.decode
    opcode = 1 if codec == "json" else 2
    try:
        frame_type, payload = await peer.receive()
        ready = decode(payload)
        _require(frame_type == opcode and ready["type"] == "ready", "Missing ready")
        _require(
            ready["version"] == 1 and bool(ready["connection_id"]), "Invalid ready",
        )
        await peer.frame(opcode, encode({
            "type": "invoke", "id": "add-1", "target": "add", "args": [20, 22],
        }))
        _, payload = await peer.receive()
        _require(decode(payload) == {
            "type": "completion", "id": "add-1", "result": 42,
        }, "Hub arithmetic completion mismatch")
        await peer.frame(opcode, encode({
            "type": "invoke", "id": "ask-1", "target": "ask", "args": [],
        }))
        _, payload = await peer.receive()
        invoke = decode(payload)
        _require(invoke["type"] == "invoke", "Expected server-to-client invocation")
        _require(invoke["target"] == "getState", "Unexpected client method")
        await peer.frame(opcode, encode({
            "type": "completion", "id": invoke["id"], "result": {"online": True},
        }))
        _, payload = await peer.receive()
        _require(decode(payload) == {
            "type": "completion", "id": "ask-1", "result": {"online": True},
        }, "Bidirectional completion mismatch")
    finally:
        await peer.close()


async def _run(interface: str) -> None:
    """
    Start the real server, execute all wire checks and release child processes.

    Parameters
    ----------
    interface : str
        Granian interface, either asgi or rsgi.

    Returns
    -------
    None
        Verify raw and Hub traffic, report results and stop the owned server.

    Raises
    ------
    AssertionError
        If server startup or wire assertions fail.
    TimeoutError
        If startup and wire checks exceed fifteen seconds.
    """
    port = _available_port()
    with tempfile.TemporaryFile() as log:
        process = _start_server(interface, port, log.fileno())
        try:
            async with asyncio.timeout(15):
                while True:
                    _require(process.poll() is None, "Granian exited during startup")
                    try:
                        reader, writer = await asyncio.open_connection(
                            "127.0.0.1", port,
                        )
                    except OSError:
                        await asyncio.sleep(0.05)
                    else:
                        del reader
                        writer.close()
                        await writer.wait_closed()
                        break
                await _check_raw(port)
                await _check_hub(port, "json")
                await _check_hub(port, "msgpack")
            sys.stdout.write(
                f"PASS Granian {interface}: raw text/binary, "
                "JSON+MessagePack, bidirectional RPC\n",
            )
        except BaseException:
            log.seek(0)
            sys.stderr.write(log.read().decode("utf-8", errors="replace"))
            raise
        finally:
            _stop_server(process)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("interface", choices=("asgi", "rsgi"))
    asyncio.run(_run(parser.parse_args().interface))
