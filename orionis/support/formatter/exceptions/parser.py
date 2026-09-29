from linecache import getlines
import traceback
from typing import Any
from orionis.support.formatter.exceptions.contracts.parser import IExceptionParser

class ExceptionParser(IExceptionParser):

    __slots__ = ("_cache", "_error_code", "_exc_type", "_tb")

    def __init__(self, exception: Exception) -> None:
        """
        Initialize ExceptionParser with an exception instance.

        Eagerly parses the exception traceback and metadata on construction
        so repeated calls to toDict() pay no extra CPU cost.

        Parameters
        ----------
        exception : Exception
            Exception to be parsed and formatted.
        """
        tb = traceback.TracebackException.from_exception(
            exception, capture_locals=False,
        )
        self._tb = tb
        self._exc_type: str = (
            tb.exc_type.__name__
            if tb.exc_type
            else type(exception).__name__
        )
        self._error_code: Any = getattr(exception, "code", None)
        self._cache: dict[str, Any] | None = None

    def toDict(self) -> dict[str, Any]:
        """
        Serialize exception details into a dictionary.

        The result is cached after the first call; subsequent calls return
        the same dict with no additional computation.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys:
            - 'error_type': str, type of the exception.
            - 'error_message': str, formatted traceback string.
            - 'error_code': Any, custom error code if present.
            - 'stack_trace': list[dict], frame details.
        """
        if self._cache is None:
            self._cache = {
                "error_type": self._exc_type,
                "error_message": str(self._tb).rstrip(),
                "error_code": self._error_code,
                "stack_trace": self._parseStack(self._tb.stack),
            }
        return self._cache

    def _getSourceCode(
        self,
        filename: str | None,
        lineno: int | None,
    ) -> tuple[list[int], list[str]]:
        """
        Extract source code lines around a specific line number from a file.

        Reuses cached file lines and builds the requested source window.

        Parameters
        ----------
        filename : str | None
            Path to the source file to read from.
        lineno : int | None
            Line number to center the code extraction around.

        Returns
        -------
        tuple[list[int], list[str]]
            Tuple containing line numbers and corresponding source code lines.
        """
        if not filename or not lineno:
            return [], []

        all_lines = getlines(filename)
        if not all_lines:
            return [], []

        start_idx = max(0, lineno - 3)
        end_idx = min(len(all_lines), lineno + 2)
        line_nums = list(range(start_idx + 1, end_idx + 1))
        source = [line.rstrip() for line in all_lines[start_idx:end_idx]]
        return line_nums, source

    def _parseStack(
        self,
        stack: traceback.StackSummary | list,
    ) -> list[dict[str, Any]]:
        """
        Parse stack trace summary into frame dictionaries.

        Iterate over the stack in reverse to produce the most-recent-first
        order. FrameSummary attributes are provided by the traceback contract.

        Parameters
        ----------
        stack : traceback.StackSummary | list
            Stack trace summary or an empty list.

        Returns
        -------
        list[dict[str, Any]]
            List of frame dicts ordered most-recent first.
        """
        if not stack:
            return []

        frames: list[dict[str, Any]] = []

        for frame_id, frame in enumerate(reversed(stack), start=1):
            source_filename = frame.filename
            source_lineno = frame.lineno
            filename = source_filename or "<unknown>"
            lineno = source_lineno or 0
            frame_name = frame.name
            frame_line = frame.line
            lines, source = self._getSourceCode(source_filename, source_lineno)

            frames.append({
                "id": frame_id,
                "filename": (
                    filename.replace("\\", "/")
                    if "\\" in filename else filename
                ),
                "lineno": lineno,
                "name": frame_name or "<unknown>",
                "line_code": frame_line,
                "code": source,
                "lines": lines,
                "code_with_lines": [
                    f"{ln}:{cd}"
                    for ln, cd in zip(lines, source, strict=True)
                ],
            })

        return frames
