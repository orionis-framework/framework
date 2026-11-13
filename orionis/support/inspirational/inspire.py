# ruff: noqa: TC001
# Retain the console annotation for dependency injection at runtime.
"""Select inspirational quotations for console output."""

import secrets
from typing import ClassVar
from orionis.console.output.console import Console
from orionis.support.inspirational.contracts.inspire import IInspire
from orionis.support.inspirational.quotes import INSPIRATIONAL_QUOTES


class Inspire(IInspire):
    """Select inspirational quotations for console output."""

    __slots__ = ("_quotes",)
    """Declare the instance attribute slots reserved by this class."""

    _FALLBACK: ClassVar[dict] = {
        "quote": (
            "Greatness is not measured by what you build, "
            "but by what you inspire others to create."
        ),
        "author": "Raul M. Uñate",
    }
    """Fallback definitions used by ``Inspire``."""

    def __init__(self, quotes: list[dict] | None = None) -> None:
        """
        Initialize the service with inspirational quotes.

        Parameters
        ----------
        quotes : list[dict] | None, optional
            Quote dictionaries with ``quote`` and ``author`` keys. If omitted or
            empty, use ``INSPIRATIONAL_QUOTES``.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        TypeError
            If any item is not a dict.
        ValueError
            If any item is missing 'quote' or 'author' keys.
        """
        if not quotes:
            self._quotes = INSPIRATIONAL_QUOTES
            """
            Quote dictionaries with ``quote`` and ``author`` keys. If omitted or
            empty, use ``INSPIRATIONAL_QUOTES``.
            """
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

    def random(self) -> dict:
        """
        Select a random quote or the fallback quote.

        Returns
        -------
        dict
            Quote dictionary containing ``quote`` and ``author`` keys.
        """
        if not self._quotes:
            return self._FALLBACK
        return secrets.choice(self._quotes)

    def printQuote(self, console: Console) -> None:
        """
        Print a random quote to the console.

        Parameters
        ----------
        console : orionis.console.Console
            Console used to write the formatted quote.

        Returns
        -------
        None
            No return value.
        """
        quote = self.random()
        console.writeLine(f'"{quote["quote"]}" - {quote["author"]}')
