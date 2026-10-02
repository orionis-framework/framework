import inspect
import math
from dataclasses import dataclass
from types import UnionType
from typing import ClassVar, cast, get_args, get_origin
import msgspec
from orionis.queues.contracts.serializer import IJobSerializer
from orionis.queues.entities.envelope import JobEnvelope
from orionis.queues.exceptions import (
    QueueConfigurationError,
    QueuePayloadError,
    UnknownJobError,
)
from orionis.queues.job import BaseJob

_MAX_PAYLOAD_BYTES = 1024 * 1024
_MAX_STATE_DEPTH = 32
_TUPLE_EXTENSION = 1
_OPTIONS = frozenset({"tries", "timeout", "backoff"})
_SCALAR_TYPES = frozenset({str, bytes, int, float, bool, type(None)})

@dataclass(frozen=True, slots=True)
class _JobMetadata:
    """Retain trusted class metadata independently of live job instances."""

    job_type: type[BaseJob]
    names: tuple[str, ...]
    annotations: dict[str, object]

def _validate_annotation(annotation: object) -> bool:
    """
    Check whether a field annotation contains only supported state types.

    Parameters
    ----------
    annotation : object
        Trusted class field annotation.

    Returns
    -------
    bool
        Whether msgspec can validate this field without constructing services.
    """
    if annotation in _SCALAR_TYPES:
        return True
    origin = get_origin(annotation)
    if origin not in {list, dict, tuple, UnionType}:
        return annotation in {list, dict, tuple}
    return all(
        argument is Ellipsis or _validate_annotation(argument)
        for argument in get_args(annotation)
    )

def _pack_value(value: object, depth: int = 0) -> object:
    """
    Validate owned primitive data and tag tuples in MessagePack.

    Parameters
    ----------
    value : object
        Field value or nested item.
    depth : int, optional
        Current nesting level.

    Returns
    -------
    object
        Data supported by the MessagePack encoder.

    Raises
    ------
    QueuePayloadError
        If state exceeds the depth limit, contains unsupported objects,
        nonfinite numbers, or dictionary keys that are not plain strings.
    """
    if depth > _MAX_STATE_DEPTH:
        message = "Job state exceeds the maximum nesting depth."
        raise QueuePayloadError(message)
    if type(value) in _SCALAR_TYPES:
        if isinstance(value, float) and not math.isfinite(value):
            message = "Job state cannot contain nonfinite numbers."
            raise QueuePayloadError(message)
        return value
    if type(value) in {list, tuple}:
        sequence = cast("list[object] | tuple[object, ...]", value)
        items = [_pack_value(item, depth + 1) for item in sequence]
        if isinstance(value, tuple):
            return msgspec.msgpack.Ext(
                _TUPLE_EXTENSION, msgspec.msgpack.encode(items),
            )
        return items
    if type(value) is dict:
        mapping = cast("dict[object, object]", value)
        if any(type(key) is not str for key in mapping):
            message = "Job state dictionaries require string keys."
            raise QueuePayloadError(message)
        return {
            key: _pack_value(item, depth + 1) for key, item in mapping.items()
        }
    message = f"Job state cannot serialize objects of type {type(value).__name__}."
    raise QueuePayloadError(message)

def _unpack_extension(code: int, data: memoryview) -> tuple[object, ...]:
    """
    Restore the tuple extension without importing or invoking payload types.

    Parameters
    ----------
    code : int
        MessagePack extension discriminator.
    data : memoryview
        Encoded tuple items.

    Returns
    -------
    tuple[object, ...]
        Restored primitive tuple.
    """
    if code != _TUPLE_EXTENSION:
        message = "Unsupported job state extension."
        raise QueuePayloadError(message)
    items = msgspec.msgpack.decode(data, ext_hook=_unpack_extension)
    if not isinstance(items, list):
        message = "Tuple extension must contain an array."
        raise QueuePayloadError(message)
    return tuple(items)

def _collect_job_fields(
    parent: type[BaseJob],
    names: dict[str, None],
    annotations: dict[str, object],
) -> None:
    """
    Collect one job class's declared slots and persistent annotations.

    Parameters
    ----------
    parent : type[BaseJob]
        Registered job class or one of its BaseJob ancestors.
    names : dict[str, None]
        Ordered persistent field names collected across the hierarchy.
    annotations : dict[str, object]
        Field constraints updated by more specific classes.

    Returns
    -------
    None
        Update the field names and annotations in place.
    """
    slots = parent.__dict__.get("__slots__", ())
    if isinstance(slots, str):
        slots = (slots,)
    for name in slots:
        if name not in {"__dict__", "__weakref__"}:
            names[name] = None
    for name, annotation in inspect.get_annotations(parent).items():
        if name not in _OPTIONS and get_origin(annotation) is not ClassVar:
            names[name] = None
            annotations[name] = annotation

def _job_metadata(job_type: type[BaseJob]) -> _JobMetadata:
    """
    Collect inherited persistent slots and annotations from a trusted class.

    Parameters
    ----------
    job_type : type[BaseJob]
        Concrete job class registered by application code.

    Returns
    -------
    _JobMetadata
        Persistent field names and optional primitive type constraints.

    Raises
    ------
    QueueConfigurationError
        If persistent fields are private, shadow job options, or use
        unsupported annotations.
    """
    names: dict[str, None] = {}
    annotations: dict[str, object] = {}
    for parent in reversed(job_type.__mro__):
        if not issubclass(parent, BaseJob):
            continue
        _collect_job_fields(parent, names, annotations)
    if any(name.startswith("_") or name in _OPTIONS for name in names):
        message = "Persistent job fields must be public and cannot shadow job options."
        raise QueueConfigurationError(message)
    if any(not _validate_annotation(value) for value in annotations.values()):
        message = "Job field annotations must describe primitive persistent data."
        raise QueueConfigurationError(message)
    return _JobMetadata(job_type, tuple(names), annotations)


class JobSerializer(IJobSerializer):
    """Serialize explicit job state through a registry of application-trusted types."""

    __slots__ = ("_decoder", "_encoder", "_registry", "_state_decoder")

    def __init__(self) -> None:
        """
        Initialize reusable codecs and an empty trusted registry.

        Returns
        -------
        None
            Retain codecs without importing application job modules.
        """
        self._registry: dict[str, _JobMetadata] = {}
        self._encoder = msgspec.json.Encoder()
        self._decoder = msgspec.json.Decoder(JobEnvelope)
        self._state_decoder = msgspec.msgpack.Decoder(ext_hook=_unpack_extension)

    def register(self, job_type: type[BaseJob]) -> None:
        """
        Register a concrete async job class supplied by trusted application code.

        Parameters
        ----------
        job_type : type[BaseJob]
            Class imported by application bootstrap or dispatched locally.

        Returns
        -------
        None
            Cache metadata once for the stable identity.
        """
        if (
            not isinstance(job_type, type)
            or not issubclass(job_type, BaseJob)
            or inspect.isabstract(job_type)
            or not inspect.iscoroutinefunction(job_type.handle)
            or "<locals>" in job_type.__qualname__
        ):
            message = "Register an importable concrete BaseJob with an async handle()."
            raise QueueConfigurationError(message)
        identity = f"{job_type.__module__}:{job_type.__qualname__}"
        existing = self._registry.get(identity)
        if existing is not None:
            if existing.job_type is not job_type:
                message = f"Job identity [{identity}] is already registered."
                raise QueueConfigurationError(message)
            return
        self._registry[identity] = _job_metadata(job_type)

    def encode(self, job: BaseJob) -> tuple[str, bytes]:
        """
        Serialize declared fields while rejecting service and undeclared state.

        Parameters
        ----------
        job : BaseJob
            Trusted application job instance.

        Returns
        -------
        tuple[str, bytes]
            Stable identity and primitive MessagePack payload.
        """
        self.register(type(job))
        identity = f"{type(job).__module__}:{type(job).__qualname__}"
        metadata = self._registry[identity]
        instance_fields = getattr(job, "__dict__", {})
        if set(instance_fields) - set(metadata.names):
            message = "Declare all persistent job fields with slots or annotations."
            raise QueuePayloadError(message)
        try:
            values = {name: getattr(job, name) for name in metadata.names}
            self._validateFields(metadata, values)
            payload = msgspec.msgpack.encode(_pack_value(values))
        except (AttributeError, TypeError, ValueError, OverflowError) as error:
            message = "Job state does not match its declared persistent fields."
            raise QueuePayloadError(message) from error
        self._checkSize(payload)
        return identity, payload

    def decode(self, identity: str, payload: bytes) -> BaseJob:
        """
        Restore primitive fields for a registered identity without running init.

        Parameters
        ----------
        identity : str
            Stable trusted identity, never an instruction to import a module.
        payload : bytes
            Untrusted MessagePack state.

        Returns
        -------
        BaseJob
            Reconstructed job awaiting scoped DI invocation.
        """
        metadata = self._registry.get(identity)
        if metadata is None:
            message = f"Job type [{identity}] is absent from the trusted registry."
            raise UnknownJobError(message)
        self._checkSize(payload)
        try:
            values = self._state_decoder.decode(payload)
            if type(values) is not dict or set(values) != set(metadata.names):
                message = "Job payload fields do not match the registered class."
                raise QueuePayloadError(message)
            _pack_value(values)
            self._validateFields(metadata, values)
            job = object.__new__(metadata.job_type)
            for name in metadata.names:
                object.__setattr__(job, name, values[name])
        except (msgspec.DecodeError, TypeError, ValueError, RecursionError) as error:
            message = "Unable to decode persistent job state."
            raise QueuePayloadError(message) from error
        return job

    def _validateFields(
        self,
        metadata: _JobMetadata,
        values: dict[str, object],
    ) -> None:
        """
        Validate annotated fields without accepting arbitrary application types.

        Parameters
        ----------
        metadata : _JobMetadata
            Trusted persistent field constraints.
        values : dict[str, object]
            Restored or declared primitive state.

        Returns
        -------
        None
            Validate field types without invoking job constructors.
        """
        for name, annotation in metadata.annotations.items():
            msgspec.convert(values[name], type=annotation, strict=True)

    def _checkSize(self, payload: bytes) -> None:
        """
        Reject oversized or nonbinary wire data before decoding.

        Parameters
        ----------
        payload : bytes
            Serialized job or envelope.

        Returns
        -------
        None
            Enforce the wire-size limit.
        """
        if not isinstance(payload, bytes) or len(payload) > _MAX_PAYLOAD_BYTES:
            message = "Queue wire data must be bytes of at most 1 MiB."
            raise QueuePayloadError(message)

    def encodeEnvelope(self, envelope: JobEnvelope) -> bytes:
        """
        Encode the immutable envelope as explicit versioned JSON.

        Parameters
        ----------
        envelope : JobEnvelope
            Validated execution data.

        Returns
        -------
        bytes
            JSON suitable for native binary database or Redis storage.
        """
        payload = self._encoder.encode(envelope)
        self._checkSize(payload)
        return payload

    def decodeEnvelope(self, payload: bytes) -> JobEnvelope:
        """
        Validate untrusted envelope JSON without resolving its job type.

        Parameters
        ----------
        payload : bytes
            Stored wire data.

        Returns
        -------
        JobEnvelope
            Immutable options ready for registry-based state decoding.
        """
        self._checkSize(payload)
        try:
            return self._decoder.decode(payload)
        except (msgspec.DecodeError, QueueConfigurationError) as error:
            message = "Unable to decode the queue envelope."
            raise QueuePayloadError(message) from error
