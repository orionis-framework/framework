"""Define the contract for workers implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod


class IWorkers(ABC):
    """Define the contract for workers implementations."""

    @classmethod
    @abstractmethod
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
        to calculate(). No instantiation is required.

        Raises
        ------
        ValueError
            If the budget is not finite, positive, or at least one byte.
        """

    @classmethod
    @abstractmethod
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
        The calculation considers both CPU core count and available RAM.
        Ensures resources are not overcommitted. No instantiation is required.
        """
