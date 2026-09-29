from typing import TYPE_CHECKING
from urllib.parse import parse_qsl
from orionis.support.patterns.final.meta import Final

if TYPE_CHECKING:
    from collections.abc import Iterator

class QueryParams(metaclass=Final):

    __slots__ = ("_index", "_items")

    def __init__(self, query_string: str) -> None:
        """
        Initialize QueryParams with a query string.

        Parameters
        ----------
        query_string : str
            The query string to parse.

        Returns
        -------
        None
            This method initializes the instance.
        """
        # Parse the query string into an ordered list of key-value pairs.
        self._items: list[tuple[str, str]] = parse_qsl(
            query_string,
            keep_blank_values=True,
            strict_parsing=False,
        )
        # Store single values and collect repeated parameters in order.
        index: dict[str, str | list[str]] = {}
        for key, value in self._items:
            previous = index.get(key)
            if previous is None:
                index[key] = value
            elif isinstance(previous, list):
                previous.append(value)
            else:
                index[key] = [previous, value]
        self._index = index

    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve the last value for a given key.

        Parameters
        ----------
        key : str
            The key to search for.
        default : str | None, optional
            The value to return if the key is not found (default is None).

        Returns
        -------
        str | None
            The last value associated with the key, or default if not found.
        """
        value = self._index.get(key, default)
        return value[-1] if isinstance(value, list) else value

    def getAll(self, key: str) -> list[str]:
        """
        Return every value for *key* in insertion order.

        Unlike ``get()``, which returns only the last occurrence, this method
        preserves all values so that repeated parameters such as
        ``?tag=a&tag=b`` are handled without data loss.

        Parameters
        ----------
        key : str
            The query parameter name to look up.

        Returns
        -------
        list[str]
            All values for *key* in the order they appear in the query string.
            Returns an empty list when *key* is absent.
        """
        value = self._index.get(key)
        if value is None:
            return []
        return value.copy() if isinstance(value, list) else [value]

    def getList(self, key: str) -> list[str]:
        """
        Alias for ``getAll()``.

        Parameters
        ----------
        key : str
            The query parameter name to look up.

        Returns
        -------
        list[str]
            All values for *key* in insertion order.
        """
        return self.getAll(key)

    def multiItems(self) -> list[tuple[str, str]]:
        """
        Return all ``(key, value)`` pairs in insertion order.

        Parameters
        ----------
        None

        Returns
        -------
        list[tuple[str, str]]
            A copy of the full ordered sequence of query parameter pairs.
        """
        return list(self._items)

    def __contains__(self, key: str) -> bool:
        """
        Check if the key exists in the query parameters.

        Parameters
        ----------
        key : str
            The key to check for.

        Returns
        -------
        bool
            True if the key exists, False otherwise.
        """
        # Check whether the field name is present in the index.
        return key in self._index

    def __getitem__(self, key: str) -> str:
        """
        Retrieve the last value for a given key or raise KeyError.

        Parameters
        ----------
        key : str
            The key to retrieve.

        Returns
        -------
        str
            The last value associated with the key.

        Raises
        ------
        KeyError
            If the key is not found.
        """
        value = self.get(key)
        if value is None:
            error_msg = key
            raise KeyError(error_msg)
        return value

    def items(self) -> list[tuple[str, str]]:
        """
        Return all key-value pairs as a list.

        Returns
        -------
        list[tuple[str, str]]
            List of all key-value pairs.
        """
        # Return a copy of the internal items list.
        return list(self._items)

    def keys(self) -> set[str]:
        """
        Return all keys in the query parameters.

        Returns
        -------
        set[str]
            Set of all unique keys.
        """
        # Return the set of indexed parameter names.
        return set(self._index)

    def values(self) -> list[str]:
        """
        Return all values in the query parameters.

        Returns
        -------
        list[str]
            List of all values.
        """
        # Extract all values from the items.
        return [v for _, v in self._items]

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """
        Return an iterator over the key-value pairs.

        Returns
        -------
        Iterator[tuple[str, str]]
            Iterator over all key-value pairs.
        """
        # Return an iterator for the items.
        return iter(self._items)

    def __len__(self) -> int:
        """
        Return the number of key-value pairs.

        Returns
        -------
        int
            The number of key-value pairs.
        """
        # Return the length of the items list.
        return len(self._items)

    def __repr__(self) -> str:
        """
        Return the string representation of the QueryParams object.

        Returns
        -------
        str
            String representation of the QueryParams instance.
        """
        # Return a formatted string showing the items.
        return f"QueryParams({self._items!r})"
