from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

_CONTEXTS = frozenset({"api", "ai", "console", "web", "websocket"})
_COMMANDS = _CONTEXTS | {"config", "lifespan"}
_RECOVERING: ContextVar[str | None] = ContextVar(
    "orionis_bootstrap_route", default=None,
)

@contextmanager
def bootstrap_recovery(arguments: Sequence[str] | None) -> Generator[None]:
    """
    Enable missing route recovery only for an exact bootstrap invocation.

    Parameters
    ----------
    arguments : Sequence[str] | None
        CLI arguments, optionally preceded by the Reactor executable.

    Returns
    -------
    None
        Restore the previous recovery context when the generator completes.

    Yields
    ------
    None
        Run application initialization and command execution in this context.
    """
    # Recognize only supported commands and exclude help invocations.
    arguments = arguments or ()
    executable = arguments[0].replace("\\", "/").rsplit("/", 1)[-1] if arguments else ""
    offset = int(executable.rsplit(".", 1)[0] == "reactor")
    context = None
    if len(arguments) > offset and not {"--help", "-h"}.intersection(arguments):
        command = arguments[offset]
        prefix, separator, candidate = command.partition(":")
        if prefix == "bootstrap" and separator and candidate in _COMMANDS:
            context = candidate
    # Restore nested contexts even when application initialization fails.
    token = _RECOVERING.set(context)
    try:
        yield
    finally:
        _RECOVERING.reset(token)

def recovering_route(context: str) -> bool:
    """
    Return whether this particular context is being explicitly repaired.

    Parameters
    ----------
    context : str
        Routing context whose missing files would otherwise prevent startup.

    Returns
    -------
    bool
        Whether startup may retain missing paths for this context alone.
    """
    # Restrict missing-file recovery to the selected routing context.
    return context in _CONTEXTS and _RECOVERING.get() == context

def bootstrap_recovery_active() -> bool:
    """
    Return whether transient recovery configuration must bypass caches.

    Returns
    -------
    bool
        Whether a native route bootstrap command is currently initializing.
    """
    # Bypass compiled state for every supported bootstrap command.
    return _RECOVERING.get() is not None
