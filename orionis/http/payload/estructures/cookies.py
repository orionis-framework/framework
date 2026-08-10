from typing import TYPE_CHECKING
from urllib.parse import unquote
from orionis.support.patterns.final.meta import Final

if TYPE_CHECKING:
    from collections.abc import Iterator

class Cookies(metaclass=Final):

    __slots__ = ("_data",)

    def __init__(self, cookie_header: str | None) -> None:
        """
        Initialize the Cookies object by parsing the Cookie header.

        Parameters
        ----------
        cookie_header : str | None
            The raw Cookie header string to parse.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._data: dict[str, str] = {}

        if not cookie_header:
            return

        # Split the header by ';' to get individual cookie pairs.
        pairs = cookie_header.split(";")

        for raw_pair in pairs:
            pair = raw_pair.strip()
            if not pair:
                continue

            if "=" not in pair:
                continue

            # Split the pair into key and value.
            key, value = pair.split("=", 1)
            value = value.strip()

            # Legacy clients may send the value wrapped in double quotes.
            if len(value) > 1 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]

            self._data[key.strip()] = unquote(value)

    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Retrieve the value of a cookie by key.

        Parameters
        ----------
        key : str
            The name of the cookie to retrieve.
        default : str | None, optional
            The value to return if the key is not found (default is None).

        Returns
        -------
        str | None
            The value of the cookie if found, otherwise the default value.
        """
        return self._data.get(key, default)

    def getAll(self) -> dict[str, str]:
        """
        Return a copy of all cookies as a dictionary.

        Returns
        -------
        dict[str, str]
            A dictionary containing all cookie key-value pairs.
        """
        return self._data.copy()

    def __getitem__(self, key: str) -> str:
        """
        Retrieve the value of a cookie by key using the indexing operator.

        Parameters
        ----------
        key : str
            The name of the cookie to retrieve.

        Returns
        -------
        str
            The value of the cookie associated with the given key.

        Raises
        ------
        KeyError
            If the key is not found in the cookie data.
        """
        return self._data[key]

    def __contains__(self, key: str) -> bool:
        """
        Check if a cookie key exists in the container.

        Parameters
        ----------
        key : str
            The name of the cookie to check.

        Returns
        -------
        bool
            True if the key exists, False otherwise.
        """
        return key in self._data

    def items(self) -> dict[str, str].items:
        """
        Return a view of the cookie container's items.

        Returns
        -------
        ItemsView[str, str]
            A view object displaying the cookie's key-value pairs.
        """
        return self._data.items()

    def keys(self) -> dict[str, str].keys:
        """
        Return a view of the cookie container's keys.

        Returns
        -------
        KeysView[str]
            A view object displaying the cookie's keys.
        """
        return self._data.keys()

    def values(self) -> dict[str, str].values:
        """
        Return a view of the cookie container's values.

        Returns
        -------
        ValuesView[str]
            A view object displaying the cookie's values.
        """
        return self._data.values()

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """
        Iterate over the cookie container's key-value pairs.

        Returns
        -------
        Iterator[tuple[str, str]]
            An iterator over the cookie's key-value pairs.
        """
        return iter(self._data.items())

    def __len__(self) -> int:
        """
        Return the number of cookies in the container.

        Returns
        -------
        int
            The number of cookie key-value pairs.
        """
        return len(self._data)

    def __repr__(self) -> str:
        """
        Return the string representation of the Cookies object.

        Returns
        -------
        str
            The string representation of the Cookies object.
        """
        return f"Cookies({self._data!r})"
