from typing import TYPE_CHECKING
from orionis.support.patterns.final.meta import Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

class Headers(metaclass=Final):

    __slots__ = ("_index", "_items")

    def __init__(self, raw: Iterable[tuple[str, str]]) -> None:
        """
        Initialize Headers from an iterable of key-value pairs.

        Parameters
        ----------
        raw : Iterable[tuple[str, str]]
            Iterable of ``(header_name, header_value)`` pairs.

        Returns
        -------
        None
        """
        # Adopt list inputs as-is; transports already hand over a fresh list.
        items: list[tuple[str, str]] = (
            raw if type(raw) is list else list(raw)
        )
        self._items: list[tuple[str, str]] = items
        # Build a lowercase-keyed index for O(1) single-value lookups.
        index: dict[str, list[str]] = {}
        for k, v in items:
            key = k.lower()
            bucket = index.get(key)
            if bucket is None:
                index[key] = [v]
            else:
                bucket.append(v)
        self._index: dict[str, list[str]] = index

    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Return the last value for the given header key.

        Parameters
        ----------
        key : str
            Case-insensitive header name to look up.
        default : str | None, optional
            Value returned when the key is absent (default ``None``).

        Returns
        -------
        str | None
            Last matching value, or ``default`` if not found.
        """
        values = self._index.get(key.lower())
        return values[-1] if values else default

    def getAll(
        self, key: str | None = None,
    ) -> dict[str, list[str]] | list[str]:
        """
        Return all values for a key, or a mapping of all headers.

        Parameters
        ----------
        key : str | None, optional
            Header name to look up. When ``None``, returns a dict
            mapping every lowercase header name to its values.

        Returns
        -------
        dict[str, list[str]]
            All headers grouped by name when ``key`` is ``None``.
        list[str]
            Ordered list of values for the specified header, or an
            empty list when the header is absent.
        """
        if key is None:
            return dict(self._index)
        return list(self._index.get(key.lower(), []))

    def __contains__(self, key: str) -> bool:
        """
        Check whether the given header key is present.

        Parameters
        ----------
        key : str
            Case-insensitive header name to check.

        Returns
        -------
        bool
            ``True`` if at least one entry matches, ``False`` otherwise.
        """
        return key.lower() in self._index

    def __getitem__(self, key: str) -> str:
        """
        Return the last value for the given header key.

        Parameters
        ----------
        key : str
            Case-insensitive header name to retrieve.

        Returns
        -------
        str
            Last value associated with the key.

        Raises
        ------
        KeyError
            If the header key is not found.
        """
        value = self.get(key)
        if value is None:
            error_msg = key
            raise KeyError(error_msg)
        return value

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """
        Iterate over all header key-value pairs.

        Returns
        -------
        Iterator[tuple[str, str]]
            An iterator over ``(name, value)`` pairs.
        """
        return iter(self._items)

    def items(self) -> list[tuple[str, str]]:
        """
        Return a copy of all header key-value pairs.

        Returns
        -------
        list[tuple[str, str]]
            All ``(name, value)`` pairs in insertion order.
        """
        return list(self._items)

    def byteItems(self) -> Iterator[tuple[bytes, bytes]]:
        """
        Yield all header pairs as UTF-8 encoded byte strings.

        Returns
        -------
        Iterator[tuple[bytes, bytes]]
            Each ``(name, value)`` pair encoded as UTF-8 bytes.
        """
        for k, v in self._items:
            yield k.encode("utf-8"), v.encode("utf-8")

    def keys(self) -> set[str]:
        """
        Return the set of unique header names.

        Returns
        -------
        set[str]
            All unique header names in their original casing.
        """
        return {k for k, _ in self._items}

    def values(self) -> list[str]:
        """
        Return all header values in insertion order.

        Returns
        -------
        list[str]
            All header values as a list.
        """
        return [v for _, v in self._items]

    def __len__(self) -> int:
        """
        Return the total number of header entries.

        Returns
        -------
        int
            Number of ``(name, value)`` pairs stored.
        """
        return len(self._items)

    def __repr__(self) -> str:
        """
        Return the canonical string representation of this instance.

        Returns
        -------
        str
            Unambiguous representation showing all stored header pairs.
        """
        return f"Headers({self._items!r})"
