from __future__ import annotations
import base64
import datetime
import decimal
import enum
import importlib
import json
import secrets
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
import msgspec.json as _msgjson
from orionis.support.types.sentinel import _MISSING_TYPE, MISSING

if TYPE_CHECKING:
    from collections.abc import Callable

# Keys for type-discriminated payloads in the encoder output
_TK: str = "__type__"
_VK: str = "__value__"

def _identity(o: Any) -> Any:
    """
    Return *o* unchanged.

    Used as the encoder for primitive types (``str``, ``int``, ``float``,
    ``bool``, ``None``) that need no transformation before JSON serialisation.

    Parameters
    ----------
    o : Any
        Value to pass through.

    Returns
    -------
    Any
        The same object *o*, unmodified.
    """
    return o

def _encode_subclass(obj: Any, t: type) -> Any:  # NOSONAR
    """
    Encode subclass instances not covered by the exact-type dispatch table.

    Walk a priority-ordered chain of ``isinstance`` checks to handle Path
    subclasses, datetime hierarchy, collection subclasses, and sentinel
    values. Raises ``TypeError`` for unsupported types.

    Parameters
    ----------
    obj : Any
        Object whose type is not present in ``_ENCODE_EXACT``.
    t : type
        ``type(obj)``, passed by the caller to avoid recomputing it.

    Returns
    -------
    Any
        JSON-compatible representation of *obj*.

    Raises
    ------
    TypeError
        If *obj* does not match any supported subclass or singleton.
    """
    # Path subclasses (WindowsPath, PosixPath, etc.)
    if isinstance(obj, Path):
        return {
            _TK: "path",
            _VK: str(obj),
        }
    # datetime.datetime must be checked before datetime.date (it is a subclass)
    if isinstance(obj, datetime.datetime):
        return {
            _TK: "datetime",
            _VK: obj.isoformat(),
        }
    if isinstance(obj, datetime.date):
        return {
            _TK: "date",
            _VK: obj.isoformat(),
        }
    if isinstance(obj, datetime.time):
        return {
            _TK: "time",
            _VK: obj.isoformat(),
        }
    # dict/list subclasses: OrderedDict, defaultdict, UserList, etc.
    if isinstance(obj, dict):
        return {k: _encode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_encode(v) for v in obj]
    # Remaining subclasses and special singletons
    if isinstance(obj, type):
        return {
            _TK: "type",
            _VK: f"{obj.__module__}.{obj.__qualname__}",
        }
    if obj is MISSING or isinstance(obj, _MISSING_TYPE):
        return {
            _TK: "missing",
            _VK: None,
        }
    if isinstance(obj, tuple):
        return {
            _TK: "tuple",
            _VK: [_encode(v) for v in obj],
        }
    if isinstance(obj, frozenset):
        return {
            _TK: "frozenset",
            _VK: [_encode(v) for v in obj],
        }
    if isinstance(obj, set):
        return {
            _TK: "set",
            _VK: [_encode(v) for v in obj],
        }
    if isinstance(obj, enum.Enum):
        et = type(obj)
        class_path = f"{et.__module__}.{et.__qualname__}"
        return {
            _TK: "enum",
            _VK: {"class": class_path, "value": obj.value},
        }
    error_msg = f"Unsupported type for serialization: {t}"
    raise TypeError(error_msg)

# Mapping of exact types to their encoder functions, for O(1) dispatch via type lookup.
_ENCODE_EXACT: dict[type, Callable[[Any], Any]] = {
    str: _identity,
    int: _identity,
    float: _identity,
    bool: _identity,
    type(None): _identity,
    Path: lambda o: {
        _TK: "path",
        _VK: str(o),
    },
    bytes: lambda o: {
        _TK: "bytes",
        _VK: base64.b64encode(o).decode(),
    },
    datetime.datetime: lambda o: {
        _TK: "datetime",
        _VK: o.isoformat(),
    },
    datetime.date: lambda o: {
        _TK: "date",
        _VK: o.isoformat(),
    },
    datetime.time: lambda o: {
        _TK: "time",
        _VK: o.isoformat(),
    },
    datetime.timedelta: lambda o: {
        _TK: "timedelta",
        _VK: {"days": o.days, "seconds": o.seconds, "microseconds": o.microseconds},
    },
    decimal.Decimal: lambda o: {
        _TK: "decimal",
        _VK: str(o),
    },
    uuid.UUID: lambda o: {
        _TK: "uuid",
        _VK: str(o),
    },
    complex: lambda o: {
        _TK: "complex",
        _VK: {"real": o.real, "imag": o.imag},
    },
}

def _encode(obj: Any) -> Any:
    """
    Encode a Python object into a JSON-compatible structure.

    Dispatch to ``_ENCODE_EXACT`` for known types via O(1) hash lookup;
    fall back to fast-path dict/list handling, then ``_encode_subclass``
    for all remaining cases.

    Parameters
    ----------
    obj : Any
        The Python object to encode.

    Returns
    -------
    Any
        A JSON-serialisable representation of *obj*.

    Raises
    ------
    TypeError
        If *obj* is of an unsupported type.
    """
    t = type(obj)
    handler = _ENCODE_EXACT.get(t)
    if handler is not None:
        return handler(obj)
    # Fast-path for the two dominant exact collection types
    if t is dict:
        return {k: _encode(v) for k, v in obj.items()}
    if t is list:
        return [_encode(v) for v in obj]
    # Delegate all subclass/singleton cases to keep cognitive complexity low
    return _encode_subclass(obj, t)

def _dec_missing(_: Any) -> Any:
    """
    Return the singleton marker for missing values.

    Parameters
    ----------
    _ : Any
        Ignored encoded payload.

    Returns
    -------
    Any
        The ``MISSING`` sentinel.
    """
    return MISSING

def _dec_type(val: str) -> Any:
    """
    Resolve a dotted class path to the corresponding type object.

    Parameters
    ----------
    val : str
        Fully qualified class name, e.g. ``"module.submodule.ClassName"``.

    Returns
    -------
    Any
        The class object referenced by *val*.
    """
    module_name, _, class_name = val.rpartition(".")
    mod = sys.modules.get(module_name) or importlib.import_module(module_name)
    return getattr(mod, class_name)

def _dec_enum(val: dict) -> Any:
    """
    Reconstruct an enum member from its serialized class path and value.

    Parameters
    ----------
    val : dict
        Mapping with ``"class"`` (dotted class path) and ``"value"`` keys.

    Returns
    -------
    Any
        The enum member corresponding to the encoded value.
    """
    module_name, _, class_name = val["class"].rpartition(".")
    mod = sys.modules.get(module_name) or importlib.import_module(module_name)
    return getattr(mod, class_name)(val["value"])

def _dec_timedelta(v: Any) -> datetime.timedelta:
    """
    Decode a mapping into a ``datetime.timedelta``.

    Parameters
    ----------
    v : Any
        Mapping of timedelta constructor fields.

    Returns
    -------
    datetime.timedelta
        Decoded time delta value.
    """
    return datetime.timedelta(**v)

def _dec_tuple(v: Any) -> tuple:
    """
    Decode an iterable payload into a tuple.

    Parameters
    ----------
    v : Any
        Encoded iterable of tuple elements.

    Returns
    -------
    tuple
        Tuple with recursively decoded elements.
    """
    return tuple(_decode(x) for x in v)

def _dec_set(v: Any) -> set:
    """
    Decode an iterable payload into a set.

    Parameters
    ----------
    v : Any
        Encoded iterable of set elements.

    Returns
    -------
    set
        Set with recursively decoded elements.
    """
    return {_decode(x) for x in v}

def _dec_frozenset(v: Any) -> frozenset:
    """
    Decode an iterable payload into a frozenset.

    Parameters
    ----------
    v : Any
        Encoded iterable of frozenset elements.

    Returns
    -------
    frozenset
        Frozen set with recursively decoded elements.
    """
    return frozenset(_decode(x) for x in v)

def _dec_complex(v: Any) -> complex:
    """
    Decode a mapping payload into a complex number.

    Parameters
    ----------
    v : Any
        Mapping with ``real`` and ``imag`` components.

    Returns
    -------
    complex
        Decoded complex value.
    """
    return complex(v["real"], v["imag"])

# Dispatch table: keyed by the type string written by the encoder.
_DECODE_DISPATCH: dict[str, Callable[[Any], Any]] = {
    "missing": _dec_missing,
    "path": Path,
    "bytes": base64.b64decode,
    "datetime": datetime.datetime.fromisoformat,
    "date": datetime.date.fromisoformat,
    "time": datetime.time.fromisoformat,
    "timedelta": _dec_timedelta,
    "decimal": decimal.Decimal,
    "uuid": uuid.UUID,
    "tuple": _dec_tuple,
    "set": _dec_set,
    "frozenset": _dec_frozenset,
    "complex": _dec_complex,
    "type": _dec_type,
    "enum": _dec_enum,
}

def _decode(obj: Any) -> Any:
    """
    Decode recursively serialized cache payloads into Python objects.

    Parameters
    ----------
    obj : Any
        Value produced by the serializer, including nested lists and mappings.

    Returns
    -------
    Any
        Decoded Python object, with typed payload wrappers resolved via
        ``_DECODE_DISPATCH``.

    Raises
    ------
    ValueError
        If a serialized type key is present but has no registered decoder.
    """
    if type(obj) is list:
        return [_decode(v) for v in obj]
    if type(obj) is dict:
        if _TK in obj:
            handler = _DECODE_DISPATCH.get(obj[_TK])
            if handler is None:
                error_msg = f"Unknown serialized type: {obj[_TK]}"
                raise ValueError(error_msg)
            return handler(obj[_VK])
        return {k: _decode(v) for k, v in obj.items()}
    # Primitive types (str, int, float, bool, None) are returned as-is
    return obj

class Serializer:

    # ruff: noqa: ANN401, PLR0911, C901

    @staticmethod
    def dumps(data: Any, indent: int | None = None) -> str:
        """
        Serialize an object to a JSON-formatted string.

        Parameters
        ----------
        data : Any
            The object to serialize.
        indent : int or None, optional
            Number of spaces for indentation in the output JSON string.

        Returns
        -------
        str
            The JSON-formatted string representing the serialized object.
        """
        encoded = _encode(data)
        if indent is not None:
            return json.dumps(encoded, indent=indent, separators=(",", ":"))
        return _msgjson.encode(encoded).decode()

    @staticmethod
    def loads(raw: str | bytes) -> Any:
        """
        Deserialize a JSON-formatted string to a Python object.

        Parameters
        ----------
        raw : str
            JSON-formatted string to deserialize.

        Returns
        -------
        Any
            The deserialized Python object.
        """
        return _decode(_msgjson.decode(raw))

    @staticmethod
    def dumpToFile(data: Any, file_path: Path) -> None:
        """
        Write serialized data to a file atomically.

        Parameters
        ----------
        data : Any
            The object to serialize and write.
        file_path : Path
            The file path where the serialized data will be written.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        OSError
            If the payload cannot be staged or renamed into place.
        """
        # Stage in a unique sibling so concurrent writers never share it
        tmp_file = file_path.with_name(
            f"{file_path.name}.{secrets.token_hex(8)}.tmp",
        )
        try:
            tmp_file.write_bytes(_msgjson.encode(_encode(data)))
            tmp_file.replace(file_path)
        except OSError:
            tmp_file.unlink(missing_ok=True)
            raise

    @staticmethod
    def loadFromFile(file_path: Path) -> Any:
        """
        Load and deserialize data from a file.

        Parameters
        ----------
        file_path : Path
            Path to the file from which to load and deserialize data.

        Returns
        -------
        Any
            The deserialized Python object, or None if the file does not exist or is
            empty.
        """
        # EAFP: one syscall instead of exists() + stat() + open()
        try:
            content = file_path.read_bytes()
        except OSError:
            return None
        if not content:
            return None
        return _decode(_msgjson.decode(content))
