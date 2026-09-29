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
_RAM_TOTAL_BYTES: int = psutil.virtual_memory().total
_BYTES_PER_GB: int = 1 << 30
_DEFAULT_RAM_PER_WORKER_BYTES: int = 1 << 29
_ERR_INVALID_RAM_PER_WORKER: str = "RAM per worker must be a finite positive value."
_ERR_RAM_PER_WORKER_TOO_SMALL: str = "RAM per worker must be at least one byte."

class Workers(IWorkers):
    # Keep instances without per-object state.
    __slots__ = ()

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
            This method updates the class-level RAM allocation and returns nothing.

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

        ram_per_worker_bytes = int(ram_per_worker * _BYTES_PER_GB)
        if ram_per_worker_bytes == 0:
            raise ValueError(_ERR_RAM_PER_WORKER_TOO_SMALL)

        cls._ram_per_worker_bytes = ram_per_worker_bytes

    @classmethod
    def calculate(cls) -> int:
        """
        Calculate the recommended maximum number of worker processes.

        Parameters
        ----------
        None

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
