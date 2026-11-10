"""
Provide http adapters response operations.

Includes ``open_file``, ``complete_file_read``.
"""

from __future__ import annotations
import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING
from orionis.failure.runtime import capture
from orionis.support.concurrency import wait_for_completion

if TYPE_CHECKING:
    from asyncio import Future
    from pathlib import Path
    from typing import BinaryIO

async def _drain_future[T](pending: Future[T]) -> T:
    """
    Wait through repeated cancellation until the worker operation finishes.

    Parameters
    ----------
    pending : asyncio.Future[``T``]
        Worker operation whose resources must remain owned until completion.

    Returns
    -------
    ``T``
        Completed worker result, including an opened handle awaiting cleanup.
    """
    while not pending.done():
        with suppress(asyncio.CancelledError, Exception):
            await wait_for_completion(pending)
    return pending.result()

async def open_file(path: Path, start: int = 0) -> BinaryIO:
    """
    Open a file in a worker thread.

    Parameters
    ----------
    path : pathlib.Path
        Path of the file to open.
    start : int, optional
        Byte offset at which to position the file.

    Returns
    -------
    typing.BinaryIO
        The opened file positioned at ``start``.

    Raises
    ------
    asyncio.CancelledError
        If the waiting task is cancelled after the file opens.
    """
    cleanup_error: Exception | None = None

    def open_and_seek() -> BinaryIO:
        """
        Open the requested file and position it at the starting offset.

        Returns
        -------
        typing.BinaryIO
            Result of the operation described above.
        """
        nonlocal cleanup_error
        file = path.open("rb")
        try:
            if start:
                file.seek(start)
        except OSError as error:
            try:
                file.close()
            except Exception as secondary:
                cleanup_error = secondary
                raise error from secondary
            raise
        return file

    executor = asyncio.get_running_loop().run_in_executor
    opening = executor(None, open_and_seek)
    try:
        return await wait_for_completion(opening)
    except asyncio.CancelledError:
        # Preserve the first cancellation if the worker or close operation fails.
        with suppress(asyncio.CancelledError):
            try:
                file = await _drain_future(opening)
                await _drain_future(executor(None, file.close))
            except Exception as error:  # noqa: BLE001 - Retain caller cancellation.
                await capture(error, flow="http", phase="file.cleanup")
        raise
    except Exception as error:
        if cleanup_error is not None:
            await capture(error, flow="http", phase="file.open")
        raise
    finally:
        if cleanup_error is not None:
            await capture(cleanup_error, flow="http", phase="file.cleanup")

async def complete_file_read(pending: Future[bytes]) -> bytes:
    """
    Complete a pending worker read before propagating cancellation.

    Parameters
    ----------
    pending : asyncio.Future[bytes]
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
        return await wait_for_completion(pending)
    except asyncio.CancelledError:
        # The first cancellation stays public after owned work has been drained.
        with suppress(asyncio.CancelledError):
            try:
                await _drain_future(pending)
            except Exception as error:  # noqa: BLE001 - Retain caller cancellation.
                await capture(error, flow="http", phase="file.read")
        raise
