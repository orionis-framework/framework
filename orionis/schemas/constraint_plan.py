# ruff: noqa: UP007
# Construct variable-length unions from runtime annotation tuples.
"""Provide schemas operations.

Includes ``register_messages``, ``annotation_messages``, ``constraint_plan``.
"""

from collections.abc import Collection, Mapping
from collections import OrderedDict
from threading import RLock
from typing import Annotated, Union, get_args, get_origin
import types
import msgspec

_KEYS = (
    "gt",
    "ge",
    "lt",
    "le",
    "multiple_of",
    "pattern",
    "min_length",
    "max_length",
    "tz",
)
"""Keys definitions used by ``constraint_plan``."""
_CACHE_MAX = 1024
"""Maximum number of retained constraint plans, including unhashable annotations."""
_CACHE: OrderedDict[int, tuple[object, tuple[object, tuple]]] = OrderedDict()
"""Bounded identity cache retaining each annotation alongside its immutable plan."""
_CACHE_LOCK = RLock()
"""Serialize cache promotion and eviction across concurrent schema consumers."""


class _ConstraintMessages:
    """Keep annotations with distinct messages from sharing a typing cache key."""

    __slots__ = ("messages",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, messages: dict[str, str]) -> None:
        """
        Retain local messages in metadata ignored by native validation.

        Parameters
        ----------
        messages : dict[str, str]
            Custom messages indexed by validation code.

        Returns
        -------
        None
            No return value.
        """
        self.messages = messages
        """Custom messages indexed by validation code."""


def register_messages(annotation: object, messages: dict[str, str]) -> object:
    """
    Attach and index local messages during annotation compilation.

    Parameters
    ----------
    annotation : object
        Compiled annotation that owns the messages.
    messages : dict[str, str]
        Custom messages indexed by validation code.

    Returns
    -------
    object
        Annotation carrying distinct message metadata, or the original
        annotation when no messages are supplied.
    """
    if not messages:
        return annotation
    return Annotated[annotation, _ConstraintMessages(messages)]


def annotation_messages(annotation: object) -> dict[str, str]:
    """
    Retrieve the most recently attached local message marker.

    Parameters
    ----------
    annotation : object
        Annotation whose custom messages are requested.

    Returns
    -------
    dict[str, str]
        Registered messages, or an empty mapping when none exist.
    """
    if get_origin(annotation) is Annotated:
        for metadata in reversed(get_args(annotation)[1:]):
            if isinstance(metadata, _ConstraintMessages):
                return metadata.messages
    return {}


def _cache_plan(annotation: object, plan: tuple[object, tuple]) -> None:
    """
    Publish a completed plan while evicting the least recently used annotations.

    Parameters
    ----------
    annotation : object
        Annotation whose identity identifies the completed plan.
    plan : tuple[object, tuple]
        Unconstrained type and independent native constraint probes.

    Returns
    -------
    None
        No return value.
    """
    with _CACHE_LOCK:
        key = id(annotation)
        _CACHE[key] = (annotation, plan)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)


def _constraint_probes(
    probe_base: object,
    meta: msgspec.Meta,
    messages: dict[str, str],
) -> list[tuple[str, object, str | None]]:
    """
    Build independent checks for the constraints in one metadata entry.

    Parameters
    ----------
    probe_base : object
        Unconstrained type checked by each probe.
    meta : ``msgspec.Meta``
        Native constraint metadata to split into individual checks.
    messages : dict[str, str]
        Custom messages indexed by validation code.

    Returns
    -------
    list[tuple[str, object, str | None]]
        Entries of ``(code, annotation, custom_message)``.
    """
    probes: list[tuple[str, object, str | None]] = []
    for key in _KEYS:
        value = getattr(meta, key)
        if value is None:
            continue
        code = key
        if key == "tz":
            code = "tz_aware" if value else "tz_naive"
        probes.append(
            (
                code,
                Annotated[probe_base, msgspec.Meta(**{key: value})],
                messages.get(code),
            ),
        )
    return probes


def constraint_plan(annotation: object) -> tuple[object, tuple]:
    """
    Build and cache independent native checks for local constraints.

    Parameters
    ----------
    annotation : object
        Field or element annotation, optionally containing union branches.

    Returns
    -------
    tuple[object, tuple]
        Type without local constraints and checks of
        ``(code, annotation, custom_message)`` for each constraint.
    """
    origin = get_origin(annotation)
    if (
        origin is not Annotated
        and origin is not Union
        and origin is not types.UnionType
    ):
        return annotation, ()
    with _CACHE_LOCK:
        cached = _CACHE.get(id(annotation))
        if cached is not None:
            _CACHE.move_to_end(id(annotation))
            return cached[1]
    if origin is Union or origin is types.UnionType:
        args = get_args(annotation)
        plans = tuple(constraint_plan(arg) for arg in args)
        base = Union[tuple(plan[0] for plan in plans)]
        probes = tuple(
            (
                code,
                Union[
                    tuple(
                        probe if index == selected else plan[0]
                        for index, plan in enumerate(plans)
                    )
                ],
                message,
            )
            for selected, (_, checks) in enumerate(plans)
            for code, probe, message in checks
        )
        result = base, probes
        _cache_plan(annotation, result)
        return result

    declared_base, *metadata = get_args(annotation)
    base, inner_probes = constraint_plan(declared_base)
    messages = annotation_messages(annotation)
    # Container constraints concern the container itself. Child types are
    # inspected separately, so a bad child cannot hide a length violation.
    probe_base = base
    origin = get_origin(base)
    if isinstance(origin, type) and issubclass(origin, Collection):
        probe_base = dict if issubclass(origin, Mapping) else origin
    probes = list(inner_probes)
    for meta in metadata:
        if isinstance(meta, msgspec.Meta):
            probes.extend(_constraint_probes(probe_base, meta, messages))
    result = base, tuple(probes)
    _cache_plan(annotation, result)
    return result
