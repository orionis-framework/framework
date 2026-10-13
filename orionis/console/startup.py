from __future__ import annotations
import os
import sys
from _thread import allocate_lock
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Sequence
    from typing import BinaryIO, Self, TextIO

_FRAME = "⠋ Inicializando Orionis..."
_ASCII_FRAME = "- Inicializando Orionis..."

class _OutputProxy:
    """Delegate output while retiring a startup message before its first write."""

    def __init__(
        self, stream: TextIO | BinaryIO, feedback: _StartupFeedback,
    ) -> None:
        """
        Initialize a stream proxy with shared startup feedback.

        Parameters
        ----------
        stream : TextIO | BinaryIO
            Wrapped stream that receives delegated operations.
        feedback : _StartupFeedback
            Controller that clears the startup message before output.

        Returns
        -------
        None
            Store the stream and controller without creating a buffer proxy.
        """
        self._stream = stream
        self.feedback = feedback
        self._buffer_proxy: _OutputProxy | None = None

    def __getattr__(self, name: str) -> object:
        """
        Delegate an unresolved attribute to the wrapped stream.

        Parameters
        ----------
        name : str
            Attribute name to retrieve from the wrapped stream.

        Returns
        -------
        object
            Attribute value exposed by the wrapped stream.
        """
        return getattr(self._stream, name)

    @property
    def buffer(self) -> _OutputProxy:
        """
        Return a cached proxy for the wrapped stream's binary buffer.

        Returns
        -------
        _OutputProxy
            Binary buffer proxy sharing the same feedback controller.
        """
        if self._buffer_proxy is None:
            self._buffer_proxy = _OutputProxy(self._stream.buffer, self.feedback)
        return self._buffer_proxy

    def write(self, value: str | bytes | bytearray | memoryview) -> int:
        """
        Write data and retire feedback before nonempty output.

        Parameters
        ----------
        value : str | bytes | bytearray | memoryview
            Text or binary data; empty values leave feedback unchanged.

        Returns
        -------
        int
            Number of characters or bytes written by the wrapped stream.
        """
        if not value or not self.feedback.active:
            return self._stream.write(value)
        with self.feedback.lock:
            self.feedback.clear()
            return self._stream.write(value)

    def writelines(self, lines: Iterable[str | bytes]) -> None:
        """
        Write each line through the proxy without adding separators.

        Parameters
        ----------
        lines : Iterable[str | bytes]
            Text or binary lines to forward in iteration order.

        Returns
        -------
        None
            Forward each line through ``write`` to retire active feedback.
        """
        for line in lines:
            self.write(line)

    def __enter__(self) -> Self:
        """
        Enter the wrapped stream's context and return this proxy.

        Returns
        -------
        Self
            This proxy after entering the wrapped stream's context.
        """
        self._stream.__enter__()
        return self

    def __exit__(self, *arguments: object) -> bool | None:
        """
        Exit the wrapped stream's context with its exception details.

        Parameters
        ----------
        *arguments : object
            Exception type, exception value, and traceback to forward.

        Returns
        -------
        bool | None
            Exception-suppression result returned by the wrapped stream.
        """
        return self._stream.__exit__(*arguments)

class _StartupFeedback:
    """Own the temporary streams and clear the message once, without a thread."""

    def __init__(self, stdout: TextIO, stderr: TextIO, frame: str) -> None:
        """
        Initialize inactive startup feedback and its stream proxies.

        Parameters
        ----------
        stdout : TextIO
            Original standard output stream to restore after feedback.
        stderr : TextIO
            Original error stream used to display and clear the message.
        frame : str
            Single-line startup message to display on ``stderr``.

        Returns
        -------
        None
            Store the streams and prepare their proxies and shared lock.
        """
        self.stdout = stdout
        self.stderr = stderr
        self.frame = frame
        self.active = False
        self.lock = allocate_lock()
        self.stdout_proxy = _OutputProxy(stdout, self)
        self.stderr_proxy = _OutputProxy(stderr, self)

    def start(self) -> None:
        """
        Display the startup message and install temporary stream proxies.

        Returns
        -------
        None
            Activate feedback, replace both streams, and flush the message.
        """
        with self.lock:
            self.active = True
            sys.stdout = self.stdout_proxy
            sys.stderr = self.stderr_proxy
            self.stderr.write(self.frame)
            self.stderr.flush()

    def clear(self) -> None:
        """
        Clear active feedback and restore the original standard streams.

        Call while holding ``lock``. Suppress display I/O errors and restore
        only standard streams that still reference this controller's proxies.

        Returns
        -------
        None
            Deactivate feedback even if clearing the display fails.
        """
        if not self.active:
            return
        try:
            self.stderr.write("\r" + " " * len(self.frame) + "\r")
            self.stderr.flush()
        except (OSError, ValueError, UnicodeError):
            # Feedback must never replace a command's error or exit status.
            pass
        finally:
            if sys.stdout is self.stdout_proxy:
                sys.stdout = self.stdout
            if sys.stderr is self.stderr_proxy:
                sys.stderr = self.stderr
            self.active = False

    def finish(self) -> None:
        """
        Retire startup feedback while holding its lock.

        Returns
        -------
        None
            Clear active feedback and restore the original streams.
        """
        with self.lock:
            self.clear()

def _interactive_frame(arguments: Sequence[str] | None) -> str | None:
    """
    Select a startup message for an eligible interactive console.

    Parameters
    ----------
    arguments : Sequence[str] | None
        Reactor arguments, including the optional executable token.

    Returns
    -------
    str | None
        Unicode or ASCII message that fits without wrapping. Return ``None``
        for CI, MCP, redirected streams, nested feedback, dumb terminals,
        or insufficient terminal width.
    """
    arguments = arguments or ()
    executable = arguments[0].replace("\\", "/").rsplit("/", 1)[-1] if arguments else ""
    offset = int(executable.rsplit(".", 1)[0] == "reactor")
    if len(arguments) > offset and arguments[offset] == "mcp:start":
        return None
    if "CI" in os.environ or os.environ.get("TERM", "").lower() == "dumb":
        return None
    if isinstance(sys.stdout, _OutputProxy) or isinstance(sys.stderr, _OutputProxy):
        return None
    try:
        if not sys.stdout.isatty() or not sys.stderr.isatty():
            return None
    except (AttributeError, OSError, ValueError):
        return None

    frame = _FRAME
    try:
        frame.encode(getattr(sys.stderr, "encoding", None) or "utf-8")
    except (LookupError, UnicodeError):
        frame = _ASCII_FRAME
    try:
        columns = os.get_terminal_size(sys.stderr.fileno()).columns
    except (AttributeError, OSError, ValueError):
        try:
            columns = int(os.environ.get("COLUMNS", "80"))
        except ValueError:
            columns = 80
    # Filling the last column may wrap; in a narrow terminal omit the message.
    return frame if len(frame) < columns else None

def stop_startup_feedback() -> None:
    """
    Retire active feedback before executing a resolved command.

    Call before command execution to protect subprocess or ``os.write`` output
    that bypasses the proxies. Do nothing when no proxy is active.

    Returns
    -------
    None
        Clear active feedback and restore the original streams.
    """
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, _OutputProxy):
            stream.feedback.finish()
            return

@contextmanager
def startup_feedback(arguments: Sequence[str] | None) -> Generator[None]:
    """
    Show transient feedback during interactive CLI startup.

    Use a static message without timers or worker threads. Clear it on the
    first nonempty text or binary write, or when the context exits. Call
    ``stop_startup_feedback`` before dispatching native output. Disable
    feedback for pipes, redirection, CI, MCP, dumb terminals, and insufficient
    terminal width.

    Parameters
    ----------
    arguments : Sequence[str] | None
        Reactor arguments, including the optional executable token.

    Yields
    ------
    None
        Control to application bootstrap and command execution.
    """
    frame = _interactive_frame(arguments)
    if frame is None:
        yield
        return
    feedback = _StartupFeedback(sys.stdout, sys.stderr, frame)
    try:
        try:
            feedback.start()
        except (OSError, ValueError, UnicodeError):
            feedback.finish()
        yield
    finally:
        feedback.finish()
