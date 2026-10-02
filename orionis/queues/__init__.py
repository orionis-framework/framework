from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.queues.context import JobContext
    from orionis.queues.entities.envelope import JobEnvelope
    from orionis.queues.job import BaseJob
    from orionis.queues.pending import PendingDispatch

__all__ = ["BaseJob", "JobContext", "JobEnvelope", "PendingDispatch"]

_EXPORTS = {
    "BaseJob": ("orionis.queues.job", "BaseJob"),
    "JobContext": ("orionis.queues.context", "JobContext"),
    "JobEnvelope": ("orionis.queues.entities.envelope", "JobEnvelope"),
    "PendingDispatch": ("orionis.queues.pending", "PendingDispatch"),
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a declared public queue export.

    Parameters
    ----------
    name : str
        Public attribute requested by application code.

    Returns
    -------
    object
        Exported class from its defining module.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """
    List loaded attributes and declared public queue exports.

    Returns
    -------
    list[str]
        Sorted package attribute names.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
