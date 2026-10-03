from __future__ import annotations
import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import Future
    from pathlib import Path
    from typing import BinaryIO

async def _drain_future[T](pending: Future[T]) -> T:
    """
    Wait through repeated cancellation until the worker operation finishes.

    Parameters
    ----------
    pending : Future[T]
        Worker operation whose resources must remain owned until completion.

    Returns
    -------
    T
        Completed worker result, including an opened handle awaiting cleanup.
    """
    while not pending.done():
        with suppress(asyncio.CancelledError, Exception):
            await asyncio.shield(pending)
    return pending.result()

async def open_file(path: Path, start: int = 0) -> BinaryIO:
    """
    Open a file in a worker thread.

    Parameters
    ----------
    path : Path
        Path of the file to open.
    start : int, optional
        Byte offset at which to position the file.

    Returns
    -------
    BinaryIO
        The opened file positioned at ``start``.

    Raises
    ------
    asyncio.CancelledError
        If the waiting task is cancelled after the file opens.
    """
    def open_and_seek() -> BinaryIO:
        """Open the requested file and position it at the starting offset."""
        file = path.open("rb")
        try:
            if start:
                file.seek(start)
        except OSError:
            file.close()
            raise
        return file

    executor = asyncio.get_running_loop().run_in_executor
    opening = executor(None, open_and_seek)
    try:
        return await asyncio.shield(opening)
    except asyncio.CancelledError:
        # Preserve the first cancellation if the worker or close operation fails.
        with suppress(Exception, asyncio.CancelledError):
            file = await _drain_future(opening)
            await _drain_future(executor(None, file.close))
        raise

async def complete_file_read(pending: Future[bytes]) -> bytes:
    """
    Complete a pending worker read before propagating cancellation.

    Parameters
    ----------
    pending : Future[bytes]
        Future representing the pending file read.

    Returns
    -------
    bytes
        Bytes returned by the worker read.

    Raises
    ------
    asyncio.CancelledError
        If the waiting task is cancelled after the read completes.
    """
    try:
        return await asyncio.shield(pending)
    except asyncio.CancelledError:
        with suppress(Exception, asyncio.CancelledError):
            await _drain_future(pending)
        raise
