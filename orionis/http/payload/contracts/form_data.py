from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from collections.abc import Iterator
    from types import TracebackType
    from orionis.http.payload.uploaded_file import UploadedFile

class IFormData(ABC):
    """
    Define the contract for parsed multipart form data.

    Notes
    -----
    Holds ordered ``(name, value)`` pairs from a multipart body,
    supports multiple values per field name, and releases open file
    handles via the context-manager protocol.
    """

    __slots__ = ()

    # Abstract property returning text fields grouped by name
    @property
    @abstractmethod
    def fields(self) -> dict[str, list[str]]:
        """
        Return all text field values grouped by name.

        Returns
        -------
        dict[str, list[str]]
            Mapping of field names to string values in insertion order.
        """

    # Abstract property returning uploaded files grouped by name
    @property
    @abstractmethod
    def files(self) -> dict[str, list[UploadedFile]]:
        """
        Return all uploaded file values grouped by name.

        Returns
        -------
        dict[str, list[UploadedFile]]
            Mapping of field names to ``UploadedFile`` instances
            in insertion order.
        """

    # Abstract property exposing the raw (name, value) sequence
    @property
    @abstractmethod
    def allItems(self) -> list[tuple[str, str | UploadedFile]]:
        """
        Return all ``(name, value)`` pairs in insertion order.

        Returns
        -------
        list[tuple[str, str | UploadedFile]]
            The underlying item sequence; callers must not mutate it.
        """

    # Abstract method for last-value retrieval by field name
    @abstractmethod
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

    # Abstract method for multi-value retrieval by field name
    @abstractmethod
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

    # Abstract method returning a copy of all (name, value) pairs
    @abstractmethod
    def multiItems(self) -> list[tuple[str, str | UploadedFile]]:
        """
        Return all ``(name, value)`` pairs in insertion order.

        Returns
        -------
        list[tuple[str, str | UploadedFile]]
            A copy of the underlying item sequence.
        """

    # Abstract method to release all open uploaded-file handles
    @abstractmethod
    def close(self) -> None:
        """
        Close all uploaded file handles to release resources.

        Returns
        -------
        None
            Always returns ``None``.
        """

    # Abstract subscript accessor returning the last value for a key
    @abstractmethod
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

    # Abstract membership test for field names
    @abstractmethod
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

    # Abstract iterator over unique field names in insertion order
    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        """
        Iterate over unique field names in first-seen insertion order.

        Returns
        -------
        Iterator[str]
            Each unique field name exactly once.
        """

    # Abstract length operator returning the count of distinct keys
    @abstractmethod
    def __len__(self) -> int:
        """
        Return the number of unique field names.

        Returns
        -------
        int
            Count of distinct keys, not the total item count.
        """

    # Abstract canonical string representation of the instance
    @abstractmethod
    def __repr__(self) -> str:
        """
        Return the canonical string representation.

        Returns
        -------
        str
            Developer-facing string describing the instance.
        """

    # Abstract context manager entry returning this instance
    @abstractmethod
    def __enter__(self) -> Self:
        """
        Enter the context manager and return this instance.

        Returns
        -------
        Self
            The ``IFormData`` instance itself.
        """

    # Abstract context manager exit closing all open file handles
    @abstractmethod
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
