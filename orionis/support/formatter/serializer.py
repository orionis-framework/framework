"""Convert supported Python values into serializable representations."""

from orionis.support.formatter.exceptions.parser import ExceptionParser

class Parser:
    """Convert supported Python values into serializable representations."""

    @staticmethod
    def exception(exception: Exception) -> ExceptionParser:
        """
        Create and return an ExceptionParser instance for the given exception.

        Parameters
        ----------
        exception : Exception
            The exception object to be parsed.

        Returns
        -------
        orionis.support.formatter.exceptions.parser.ExceptionParser
            An ExceptionParser instance initialized with the provided exception.
        """
        # Instantiate and return an ExceptionParser for the given exception
        return ExceptionParser(exception)
