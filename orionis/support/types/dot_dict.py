from __future__ import annotations
from typing import Any

_MISSING = object()

class DotDict(dict):

    __slots__ = ()

    def __getattr__(self, key: str) -> object | None:
        """
        Retrieve a value using attribute-style access.

        Parameters
        ----------
        key : str
            Attribute name to retrieve.

        Returns
        -------
        Any or None
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
        value : Any
            Value to assign. If a dict (not DotDict), it is converted to DotDict.

        Returns
        -------
        None
            This method does not return a value.

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
            This method does not return a value.

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
        value = dict.get(self, key, default)
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
        DotDict
            A new DotDict instance with recursively copied contents.
        """
        result = DotDict()
        _setitem = dict.__setitem__
        for k, v in dict.items(self):
            if type(v) is DotDict:
                _setitem(result, k, v.copy())
            elif isinstance(v, dict):
                _setitem(result, k, DotDict(v).copy())
            else:
                _setitem(result, k, v)
        return result
