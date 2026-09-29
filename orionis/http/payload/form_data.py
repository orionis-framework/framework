from __future__ import annotations
from typing import TYPE_CHECKING, Self
from orionis.http.payload.contracts.form_data import IFormData

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType
    from orionis.http.payload.uploaded_file import UploadedFile

class FormData(IFormData):
    """
    Hold parsed multipart form fields and uploaded files.

    Notes
    -----
    Stores ordered ``(name, value)`` pairs and supports multiple values
    under the same field name. Implements the context-manager protocol
    to guarantee all open file handles are released on exit.
    """

    __slots__ = ("_index", "_items")

    # Constructor building the item list and positional index
    def __init__(
        self,
        items: list[tuple[str, str | UploadedFile]],
    ) -> None:
        """
        Initialize FormData from an ordered list of ``(name, value)`` pairs.

        Parameters
        ----------
        items : list[tuple[str, str | UploadedFile]]
            Ordered ``(field_name, value)`` pairs from the multipart
            stream parser. Multiple pairs with the same name are
            preserved in insertion order.

        Returns
        -------
        None
            Always returns ``None``.
        """
        self._items: list[tuple[str, str | UploadedFile]] = list(items)
        # Store single values and collect repeated fields in order.
        index: dict[str, str | UploadedFile | list[str | UploadedFile]] = {}
        for key, value in self._items:
            previous = index.get(key)
            if previous is None:
                index[key] = value
            elif isinstance(previous, list):
                previous.append(value)
            else:
                index[key] = [previous, value]
        self._index = index

    # ---- Backward-compatible grouped views ----

    # Property returning only text fields grouped by name
    @property
    def fields(self) -> dict[str, list[str]]:
        """
        Return all text field values grouped by name.

        Returns
        -------
        dict[str, list[str]]
            Mapping of field names to string values in insertion order.
        """
        result: dict[str, list[str]] = {}
        for k, v in self._items:
            if isinstance(v, str):
                result.setdefault(k, []).append(v)
        return result

    # Property returning only uploaded files grouped by name
    @property
    def files(self) -> dict[str, list[UploadedFile]]:
        """
        Return all uploaded file values grouped by name.

        Returns
        -------
        dict[str, list[UploadedFile]]
            Mapping of field names to ``UploadedFile`` instances
            in insertion order.
        """
        result: dict[str, list[UploadedFile]] = {}
        for k, v in self._items:
            if not isinstance(v, str):
                result.setdefault(k, []).append(v)  # type: ignore[arg-type]
        return result

    # ---- Retrieval ----

    # Method returning the last value for a given key
    def get(
        self,
        key: str,
        default: object | None = None,
    ) -> object | None:
        """
        Return the last value for *key*, or *default*.

        Parameters
        ----------
        key : str
            Field name to look up.
        default : object | None, optional
            Fallback when *key* is absent. Defaults to ``None``.

        Returns
        -------
        object | None
            Last ``str`` or ``UploadedFile`` for *key*, or *default*.
        """
        value = self._index.get(key)
        if value is None:
            return default
        return value[-1] if isinstance(value, list) else value

    # Method returning all values for a given key in insertion order
    def getAll(self, key: str) -> list[str | UploadedFile]:
        """
        Return every value for *key* in insertion order.

        Parameters
        ----------
        key : str
            Field name to look up.

        Returns
        -------
        list[str | UploadedFile]
            All values for *key*, or an empty list if absent.
        """
        value = self._index.get(key)
        if value is None:
            return []
        return value.copy() if isinstance(value, list) else [value]

    # Property exposing the raw (name, value) sequence without copying
    @property
    def allItems(self) -> list[tuple[str, str | UploadedFile]]:
        """
        Return all ``(name, value)`` pairs in insertion order.

        Returns
        -------
        list[tuple[str, str | UploadedFile]]
            The underlying item sequence; callers must not mutate it.
        """
        return self._items

    # Method returning a copied list of all (name, value) pairs
    def multiItems(self) -> list[tuple[str, str | UploadedFile]]:
        """
        Return all ``(name, value)`` pairs in insertion order.

        Returns
        -------
        list[tuple[str, str | UploadedFile]]
            A copy of the underlying item sequence.
        """
        return list(self._items)

    # ---- Mapping protocol ----

    # Subscript accessor delegating to get()
    def __getitem__(self, key: str) -> object:
        """
        Return the last value for *key* using subscript notation.

        Parameters
        ----------
        key : str
            Field name to retrieve.

        Returns
        -------
        object
            Last value for *key*, or ``None`` if absent.
        """
        return self.get(key)

    # Membership test delegating to the positional index
    def __contains__(self, key: str) -> bool:
        """
        Return ``True`` if at least one item with *key* exists.

        Parameters
        ----------
        key : str
            Field name to check.

        Returns
        -------
        bool
            ``True`` if *key* is present, ``False`` otherwise.
        """
        # Check whether the field name is present in the index.
        return key in self._index

    # Iterator over unique field names in first-seen insertion order
    def __iter__(self) -> Iterator[str]:
        """
        Iterate over unique field names in first-seen insertion order.

        Returns
        -------
        Iterator[str]
            Each unique field name exactly once.
        """
        # The index dict preserves insertion order of first occurrence.
        return iter(self._index)

    # Length operator returning the count of distinct field names
    def __len__(self) -> int:
        """
        Return the number of unique field names.

        Returns
        -------
        int
            Count of distinct keys, not the total item count.
        """
        # O(1) — dict length is maintained as an internal counter.
        return len(self._index)

    # Canonical string representation of this instance
    def __repr__(self) -> str:
        """
        Return the canonical string representation.

        Returns
        -------
        str
            Developer-facing string showing the stored item pairs.
        """
        return f"FormData({self._items!r})"

    # ---- Resource management ----

    # Method closing all open uploaded-file handles
    def close(self) -> None:
        """
        Close all uploaded file handles to release resources.

        Returns
        -------
        None
            Always returns ``None``.
        """
        # Skip plain strings; only UploadedFile instances need closing.
        for _, v in self._items:
            if not isinstance(v, str):
                v.close()

    # Context manager entry returning this instance
    def __enter__(self) -> Self:
        """
        Enter the context manager and return this instance.

        Returns
        -------
        Self
            The ``FormData`` instance itself.
        """
        return self

    # Context manager exit delegating cleanup to close()
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Exit the context manager and close all uploaded file handles.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Exception class if one was raised, otherwise ``None``.
        exc_val : BaseException | None
            Exception instance if one was raised, otherwise ``None``.
        exc_tb : TracebackType | None
            Traceback if an exception was raised, otherwise ``None``.

        Returns
        -------
        None
            Always returns ``None``.
        """
        self.close()
