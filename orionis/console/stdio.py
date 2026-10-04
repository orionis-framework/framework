"""Reserve STDOUT before an MCP command boots application services."""

import sys
from contextlib import contextmanager, redirect_stdout
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

_PROTOCOL_STDOUT: ContextVar[BinaryIO | None] = ContextVar(
    "orionis_protocol_stdout", default=None,
)


def protocol_stdout() -> BinaryIO | None:
    """Return the original protocol writer while diagnostic stdout is redirected."""
    return _PROTOCOL_STDOUT.get()


@contextmanager
def protocol_stdio(arguments: Sequence[str] | None) -> Iterator[None]:
    """Route MCP bootstrap, command, and shutdown diagnostics to STDERR.

    Nested application entry points retain the first binary protocol writer.
    Ordinary Reactor commands keep their existing output behavior.
    """
    arguments = arguments or ()
    offset = int(bool(arguments and Path(arguments[0]).stem == "reactor"))
    selected = len(arguments) > offset and arguments[offset] == "mcp:start"
    if not selected or _PROTOCOL_STDOUT.get() is not None:
        yield
        return
    stream = getattr(sys.stdout, "buffer", None)
    token = _PROTOCOL_STDOUT.set(stream)
    try:
        with redirect_stdout(sys.stderr):
            yield
    finally:
        _PROTOCOL_STDOUT.reset(token)
