import secrets
from typing import ClassVar
from orionis.support.inspirational.contracts.inspire import IInspire
from orionis.support.inspirational.quotes import INSPIRATIONAL_QUOTES

class Inspire(IInspire):

    __slots__ = ("_count", "_quotes")

    _FALLBACK: ClassVar[dict] = {
        "quote": (
            "Greatness is not measured by what you build, "
            "but by what you inspire others to create."
        ),
        "author": "Raul M. Uñate",
    }

    def __init__(self, quotes: list[dict] | None = None) -> None:
        """
        Initialize the Inspire service with a list of inspirational quotes.

        Parameters
        ----------
        quotes : list[dict] | None, optional
            List of dictionaries, each containing 'quote' (str) and 'author' (str).
            If None or empty, defaults to INSPIRATIONAL_QUOTES.

        Returns
        -------
        None
            This method initializes the internal state of the Inspire service.

        Raises
        ------
        TypeError
            If any item is not a dict.
        ValueError
            If any item is missing 'quote' or 'author' keys.
        """
        if not quotes:
            self._quotes = INSPIRATIONAL_QUOTES
        else:
            for row in quotes:
                if not isinstance(row, dict):
                    msg = "Quotes must be provided as a list of dictionaries."
                    raise TypeError(msg)
                if "quote" not in row or "author" not in row:
                    msg = (
                        "Each quote dictionary must contain 'quote' and 'author' keys."
                    )
                    raise ValueError(msg)
            self._quotes = quotes
        self._count = len(self._quotes)

    def random(self) -> dict:
        """
        Return a random inspirational quote from the available list.

        Select a random quote from the internal list of inspirational quotes.
        If the list is empty, return a fallback quote to ensure a valid response.

        Returns
        -------
        dict
            Dictionary with 'quote' (str) and 'author' (str) keys. If no quotes
            are available, returns the fallback quote.
        """
        if self._count == 0:
            return self._FALLBACK
        return secrets.choice(self._quotes)

