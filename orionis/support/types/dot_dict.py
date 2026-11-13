"""Expose nested dictionary values through attribute access."""

from __future__ import annotations
from copy import deepcopy
from typing import Any

_MISSING = object()
"""Sentinel distinguishing missing from ordinary values."""


class DotDict(dict):
    """Expose nested dictionary values through attribute access."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def __getattr__(self, key: str) -> object | None:
        """
        Retrieve a value using attribute-style access.

        Parameters
        ----------
        key : str
            Attribute name to retrieve.

        Returns
        -------
        object or None
            Value associated with the key, converted to DotDict if it is a dict.
            Returns None if the key does not exist.

        Notes
        -----
        Enables attribute-style access for dictionary keys. Converts plain dicts
        to DotDict for consistency.
        """
        value = dict.get(self, key, _MISSING)
        if value is _MISSING:
            return None
        if type(value) is dict:
            value = DotDict(value)
            dict.__setitem__(self, key, value)
        return value

    def __setattr__(self, key: str, value: object) -> None:
        """
        Set an attribute on the DotDict instance.

        Parameters
        ----------
        key : str
            Attribute name to set.
        value : object
            Value to assign. If a dict (not DotDict), it is converted to DotDict.

        Returns
        -------
        None
            No return value.

        Notes
        -----
        Enables attribute-style assignment for dictionary keys. Converts plain
        dicts to DotDict for recursive attribute access.
        """
        if type(value) is dict:
            value = DotDict(value)
        dict.__setitem__(self, key, value)

    def __delattr__(self, key: str) -> None:
        """
        Delete an attribute from the DotDict instance.

        Parameters
        ----------
        key : str
            Name of the attribute to delete.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        AttributeError
            If the attribute does not exist in the DotDict.

        Notes
        -----
        Supports attribute-style deletion for dictionary keys.
        """
        try:
            del self[key]
        except KeyError as e:
            message = f"'{type(self).__name__}' has no attribute '{key}'"
            raise AttributeError(
                message,
            ) from e

    def get(self, key: str, default: object | None = None) -> object | None:
        """
        Get the value for a key, returning default if the key is not found.

        Parameters
        ----------
        key : str
            The key to look up in the dictionary.
        default : object or None, optional
            The value to return if the key is not found. Defaults to None.

        Returns
        -------
        object or None
            The value associated with the key, converted to DotDict if it is a
            dict. Returns the specified default value if the key is not present.
        """
        value = dict.get(self, key, _MISSING)
        if value is _MISSING:
            return default
        if type(value) is dict:
            value = DotDict(value)
            dict.__setitem__(self, key, value)
        return value

    def export(self) -> dict[str, Any]:
        """
        Export the DotDict as a standard dictionary recursively.

        Returns
        -------
        dict
            A dictionary where all nested DotDict instances are converted to
            standard dictionaries. Non-DotDict values are returned unchanged.
        """
        result: dict[str, Any] = {}
        for k, v in dict.items(self):
            if type(v) is DotDict:
                result[k] = v.export()
            elif isinstance(v, dict):
                result[k] = DotDict(v).export()
            else:
                result[k] = v
        return result

    def copy(self) -> DotDict:
        """
        Create a deep copy of the DotDict.

        Returns
        -------
        orionis.support.types.DotDict
            A new DotDict instance with recursively copied contents.
        """
        return deepcopy(self)

    def __deepcopy__(self, memo: dict[int, object]) -> DotDict:
        """
        Copy values while preserving shared references and cycles.

        Parameters
        ----------
        memo : dict[int, object]
            Objects already copied by the standard copy protocol.

        Returns
        -------
        DotDict
            Independent contents with dictionary-valued members exposed as DotDict.
        """
        return _copy_mapping(self, memo)


def _copy_mapping(source: dict, memo: dict[int, object]) -> DotDict:
    """
    Copy a mapping into DotDict using the shared deepcopy memo.

    Parameters
    ----------
    source : dict
        Mapping whose contents will be copied.
    memo : dict[int, object]
        Previously copied objects, including active mapping ancestors.

    Returns
    -------
    DotDict
        Copied mapping or its existing shared copy.
    """
    if id(source) in memo:
        return memo[id(source)]
    result = DotDict()
    memo[id(source)] = result
    for key, value in source.items():
        copied = (
            _copy_mapping(value, memo)
            if isinstance(value, dict)
            else deepcopy(value, memo)
        )
        result[deepcopy(key, memo)] = copied
    return result
