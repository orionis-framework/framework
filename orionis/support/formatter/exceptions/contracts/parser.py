"""Define the contract for exception parser implementations."""

from typing import Any, Protocol


class IExceptionParser(Protocol):
    """Define the contract for exception parser implementations."""

    def toDict(self) -> dict[str, Any]:
        """
        Serialize exception details into a dictionary.

        Parameters
        ----------
        self : orionis.support.formatter.exceptions.parser.ExceptionParser
            Instance of ExceptionParser.

        Returns
        -------
        dict[str, typing.Any]
            Dictionary with keys:
            - 'error_type': str, type of the exception.
            - 'error_message': str, formatted traceback string.
            - 'error_code': Any, custom error code if present.
            - 'stack_trace': list[dict], frame details.
        """
        ...
