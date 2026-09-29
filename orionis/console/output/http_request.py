from __future__ import annotations
import asyncio
import contextlib
import shutil
import sys
import time
from typing import ClassVar, TYPE_CHECKING
from orionis.console.output.contracts.http_request import IHTTPRequestPrinter

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.responses import Response

# ANSI escape codes
_RESET = "\033[0m"
_BOLD  = "\033[1m"

# Foreground
_FG_BLACK = "\033[30m"
_FG_WHITE = "\033[37m"
_FG_CYAN  = "\033[36m"
_FG_GREEN = "\033[32m"
_FG_RED   = "\033[31m"
_FG_GREY  = "\033[90m"

# Background (standard)
_BG_RED     = "\033[41m"
_BG_GREEN   = "\033[42m"
_BG_YELLOW  = "\033[43m"
_BG_BLUE    = "\033[44m"
_BG_MAGENTA = "\033[45m"
_BG_CYAN    = "\033[46m"
_BG_WHITE   = "\033[47m"
_BG_BRIGHT  = "\033[100m"

# Background (256-colour approximations)
_BG_GREY37  = "\033[48;5;237m"   # ≈ grey37
_BG_GREY50  = "\033[48;5;244m"   # ≈ grey50
_BG_GREY70  = "\033[48;5;250m"   # ≈ grey70

class HTTPRequestPrinter(IHTTPRequestPrinter):

    # ruff: noqa: ERA001

    # Minimum valid HTTP status code
    HTTP_MIN_STATUS_CODE: ClassVar[int] = 100

    # (bg_ansi, fg_ansi) tuples for HTTP methods
    HTTP_COLORS: ClassVar[dict] = {
        "GET":     (_BG_GREEN,   _FG_BLACK),
        "POST":    (_BG_BLUE,    _FG_WHITE),
        "PUT":     (_BG_YELLOW,  _FG_BLACK),
        "PATCH":   (_BG_MAGENTA, _FG_WHITE),
        "DELETE":  (_BG_RED,     _FG_WHITE),
        "OPTIONS": (_BG_CYAN,    _FG_BLACK),
        "HEAD":    (_BG_WHITE,   _FG_BLACK),
        "TRACE":   (_BG_GREY70,  _FG_BLACK),
        "CONNECT": (_BG_BRIGHT,  _FG_WHITE),
        "QUERY":   (_BG_GREY37,  _FG_WHITE),
        "default": (_BG_GREY37,  _FG_WHITE),
    }

    # (bg_ansi, fg_ansi) tuples for HTTP status categories
    STATUS_COLORS: ClassVar[dict] = {
        "1xx": (_BG_CYAN,    _FG_BLACK),
        "2xx": (_BG_GREEN,   _FG_WHITE),
        "3xx": (_BG_YELLOW,  _FG_BLACK),
        "4xx": (_BG_MAGENTA, _FG_WHITE),
        "5xx": (_BG_RED,     _FG_WHITE),
        "default": (_BG_GREY50, _FG_WHITE),
    }

    def __init__(self) -> None:
        """
        Initialize the HTTPRequestPrinter instance.

        Determines terminal width, precomputes reusable ANSI-coloured
        strings, and prepares the async queue and worker task references.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Determine terminal width, clamped between 60 and 120 columns
        cols = shutil.get_terminal_size(fallback=(80, 24)).columns
        self._total_width = max(60, min(120, int(cols * 0.8)))

        # Precompute status icons by HTTP code category
        self.__status_icons: dict[str, str] = {
            "1xx": " ⚪ ",
            "2xx": " 🟢 ",
            "3xx": " 🔵 ",
            "4xx": " 🟡 ",
            "5xx": " 🔴 ",
            "default": " ⚫ ",
        }

        # Enable HTTP request printing to console by default
        self.__enabled: bool = True

        # Async queue and worker task (initialized by start())
        self.__queue: asyncio.Queue | None = None
        self.__worker_task: asyncio.Task | None = None

        # Internal timer set by startTimer(); None until first call
        self.__start_timer: float | None = None

        # Cache stdout bound methods: LOAD_FAST vs sys.stdout LOAD_GLOBAL+LOAD_ATTR
        self._write = sys.stdout.write
        self._flush = sys.stdout.flush

    def setEnabled(self, *, enabled: bool) -> None:
        """
        Set whether to enable or disable console output for HTTP requests.

        Parameters
        ----------
        enabled : bool
            If True, HTTP requests are printed to console. If False, output
            is suppressed.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__enabled = enabled

    async def start(self) -> None:
        """
        Start the background print worker.

        Creates the internal async queue and spawns a background task
        to drain queued output lines. Must be called once from an async
        context before the first request is handled.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Initialize the async queue with a maximum size of 1000 items
        self.__queue = asyncio.Queue(maxsize=1000)

        # Spawn the background worker task
        self.__worker_task = asyncio.ensure_future(self.__worker())

    async def stop(self) -> None:
        """
        Drain remaining output and stop the background worker.

        Waits for every queued line to be written before cancelling the
        worker task. Safe to call even if start() was never invoked.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Wait for all queued lines to be processed
        if self.__queue is not None:
            await self.__queue.join()

        # Cancel the worker task and suppress the CancelledError
        if self.__worker_task is not None:
            self.__worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.__worker_task

        # Reset internal references
        self.__queue = None
        self.__worker_task = None

    async def __worker(self) -> None:
        """
        Write queued lines to stdout in the background.

        Continuously reads lines from the internal async queue and writes
        them to stdout, flushing after each write to ensure immediate display.

        Returns
        -------
        None
            This method does not return a value.
        """
        write = sys.stdout.write
        flush = sys.stdout.flush

        # Retrieve the next line from the queue and write it
        while True:
            line: str = await self.__queue.get()
            write(line)
            flush()
            self.__queue.task_done()

    def startTimer(self) -> float | None:
        """
        Capture the current high-resolution timestamp for request timing.

        Returns None immediately if printing is disabled, avoiding unnecessary
        work when output has been suppressed via setEnabled(enabled=False).

        Returns
        -------
        float | None
            A high-resolution monotonic timestamp from time.perf_counter(),
            or None if output is disabled.
        """
        if not self.__enabled:
            return None
        self.__start_timer = time.perf_counter()
        return self.__start_timer

    def printRequest(
        self,
        adapter: TransportAdapter,
        response: Response,
    ) -> None:
        """
        Print a formatted HTTP request line to stdout or queue.

        Computes the elapsed duration from start_time, builds an
        ANSI-coloured output line, and either enqueues it for the
        background worker (if start() was called) or writes directly
        to stdout.

        Parameters
        ----------
        adapter : TransportAdapter
            The transport adapter providing method and path information.
        response : Response
            The HTTP response object.

        Returns
        -------
        None
            This method does not return a value.
        """
        # If printing is disabled or no timer was captured, do nothing
        if not self.__enabled or self.__start_timer is None:
            return

        # Skip logging for well-known paths to reduce noise
        path = adapter.path()
        if path.startswith("/.well-known/"):
            return

        # Compute elapsed time from the captured start timestamp
        elapsed = time.perf_counter() - self.__start_timer

        # Cache class dicts and attrs as locals: LOAD_FAST vs LOAD_ATTR chain per use
        _http_colors = self.HTTP_COLORS
        _status_colors = self.STATUS_COLORS
        _status_icons = self.__status_icons
        total_width = self._total_width

        # Pure str methods (all C-level): no Stringable object creation
        method = adapter.method().strip().upper()
        bg, fg = _http_colors.get(method, _http_colors["default"])
        method_str = f"{_BOLD}{bg}{fg}{method.center(9)}{_RESET}"

        # Format duration in milliseconds or seconds
        duration_raw = (
            f"~ {elapsed * 1000:.0f}ms"
            if elapsed < 1.0
            else f"~ {elapsed:.2f}s"
        )
        duration_str = f"{_FG_CYAN}{duration_raw.rjust(8)}{_RESET}"

        # Format path with filler dots to reach total width
        path_dots_space = total_width - 18
        max_path = max(1, path_dots_space - 3)
        path_len = len(path)
        if path_len > max_path:
            path_display = path[:max_path - 3] + "..."
            display_len = max_path  # len(path[:n-3] + "...") == n always
        else:
            path_display = path
            display_len = path_len
        path_str = f"\033[37m{path_display}{_RESET}"
        filler_str = f"{_FG_GREY}{'.' * (path_dots_space - display_len)}{_RESET}"

        # Integer division: no str()+index; also unifies both status lookups to one key
        code = response.getStatusCode()
        code_s = str(code)
        code_category = (
            f"{code // 100}xx" if code >= self.HTTP_MIN_STATUS_CODE else "default"
        )
        status_str = _status_icons.get(code_category, _status_icons["default"])
        bg_c, fg_c = _status_colors.get(code_category, _status_colors["default"])
        code_str = f"{_BOLD}{bg_c}{fg_c}{code_s.center(5)}{_RESET}"

        # Assemble the complete output line
        line = (
            f"{method_str} {path_str}{filler_str}"
            f"{duration_str}{status_str}{code_str}\n"
        )

        # Cache queue ref: avoids double LOAD_ATTR (None check + put_nowait call)
        q = self.__queue
        if q is not None:
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(line)
        else:
            self._write(line)
            self._flush()
