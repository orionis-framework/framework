"""Calculate worker counts from the current process and CPU environment."""

from __future__ import annotations
import math
import os
import psutil
from orionis.support.system.contracts.workers import IWorkers


# Helper function to determine the logical CPU count available to this process.
def _get_cpu_count() -> int:
    """
    Return the logical CPU count available to this process.

    Returns
    -------
    int
        Logical CPU count available to this process.
    """
    return os.process_cpu_count() or os.cpu_count() or 1


# Store the process resource limits for the lifetime of this process.
_CPU_COUNT: int = _get_cpu_count()
"""Store the process resource limits for the lifetime of this process."""
_RAM_TOTAL_BYTES: int = psutil.virtual_memory().total
"""Ram total bytes used by ``workers``."""
_BYTES_PER_GB: int = 1 << 30
"""Bytes per gb used by ``workers``."""
_DEFAULT_RAM_PER_WORKER_BYTES: int = 1 << 29
"""Default ram per worker bytes used by ``workers``."""
_ERR_INVALID_RAM_PER_WORKER: str = "RAM per worker must be a finite positive value."
"""
Error text for invalid ram per worker: ``RAM per worker must be a finite positive
value.``.
"""
_ERR_RAM_PER_WORKER_TOO_SMALL: str = "RAM per worker must be at least one byte."
"""
Error text for ram per worker too small: ``RAM per worker must be at least one
byte.``.
"""


class Workers(IWorkers):
    # Keep instances without per-object state.
    """Calculate worker counts from the current process and CPU environment."""

    __slots__ = ()
    """Keep instances without per-object state."""

    # Store the configured RAM budget in bytes.
    _ram_per_worker_bytes: int = _DEFAULT_RAM_PER_WORKER_BYTES

    @classmethod
    def setRamPerWorker(cls, ram_per_worker: float) -> None:
        """
        Update the RAM allocation per worker.

        Parameters
        ----------
        ram_per_worker : float
            New amount of RAM in GB to allocate for each worker.

        Returns
        -------
        None
            No return value.

        Notes
        -----
        Changing the RAM allocation per worker affects every subsequent call
        to calculate(). The update is reflected immediately.

        Raises
        ------
        ValueError
            If the budget is not finite, positive, or at least one byte.
        """
        if not math.isfinite(ram_per_worker) or ram_per_worker <= 0:
            raise ValueError(_ERR_INVALID_RAM_PER_WORKER)

        numerator, denominator = ram_per_worker.as_integer_ratio()
        ram_per_worker_bytes = numerator * _BYTES_PER_GB // denominator
        if ram_per_worker_bytes == 0:
            raise ValueError(_ERR_RAM_PER_WORKER_TOO_SMALL)

        cls._ram_per_worker_bytes = ram_per_worker_bytes

    @classmethod
    def calculate(cls) -> int:
        """
        Calculate the recommended maximum number of worker processes.

        Returns
        -------
        int
            The maximum number of worker processes that can be safely run in
            parallel, determined by the lesser of available CPU cores and memory
            capacity. Always returns at least 1.

        Notes
        -----
        Uses cached CPU and RAM values and a precomputed RAM budget so each
        invocation only needs integer arithmetic.
        """
        return (
            min(
                _CPU_COUNT,
                _RAM_TOTAL_BYTES // cls._ram_per_worker_bytes,
            )
            or 1
        )
