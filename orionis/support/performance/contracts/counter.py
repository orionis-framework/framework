from __future__ import annotations
from abc import ABC, abstractmethod

class IPerformanceCounter(ABC):
    __slots__ = ()

    @abstractmethod
    def start(self) -> IPerformanceCounter:
        """
        Start the performance counter.

        Records the current high-resolution time as the start time.

        Returns
        -------
        IPerformanceCounter
            This instance for method chaining.
        """

    @abstractmethod
    async def astart(self) -> IPerformanceCounter:
        """
        Start the performance counter asynchronously.

        Records the current high-resolution time for an asynchronous measurement.

        Returns
        -------
        IPerformanceCounter
            The current instance for method chaining.
        """

    @abstractmethod
    def stop(self) -> IPerformanceCounter:
        """
        Stop the performance counter and compute elapsed time.

        Records the current high-resolution time as the end time and computes the
        elapsed time since `start()` was called.

        Returns
        -------
        IPerformanceCounter
            The current instance for method chaining.

        Raises
        ------
        RuntimeError
            If called after asynchronous start.
        ValueError
            If called before start.
        """

    @abstractmethod
    async def astop(self) -> IPerformanceCounter:
        """
        Stop the performance counter asynchronously.

        Records the current high-resolution time as the end time and computes the
        elapsed time since `astart()` was called.

        Returns
        -------
        IPerformanceCounter
            This instance for method chaining.

        Raises
        ------
        RuntimeError
            If called after synchronous start.
        """

    @abstractmethod
    def elapsedTime(self) -> float:
        """
        Return the elapsed time in seconds between the last start and stop calls.

        Raises
        ------
        ValueError
            If the counter has not been started and stopped properly.

        Returns
        -------
        float
            Elapsed time in seconds as a float.
        """

    @abstractmethod
    async def aelapsedTime(self) -> float:
        """
        Return the elapsed time in seconds asynchronously.

        Returns
        -------
        float
            Elapsed time in seconds as a float.

        Raises
        ------
        ValueError
            If the counter has not been started and stopped properly.
        """

    @abstractmethod
    def getMicroseconds(self) -> float:
        """
        Return the elapsed time in microseconds.

        Converts the elapsed time in seconds to microseconds.

        Returns
        -------
        float
            Elapsed time in microseconds.
        """

    @abstractmethod
    async def agetMicroseconds(self) -> float:
        """
        Return the elapsed time in microseconds asynchronously.

        Returns
        -------
        float
            Elapsed time in microseconds as a float.
        """

    @abstractmethod
    def getMilliseconds(self) -> float:
        """
        Return the elapsed time in milliseconds.

        Converts the elapsed time in seconds to milliseconds.

        Returns
        -------
        float
            Elapsed time in milliseconds as a float.
        """

    @abstractmethod
    async def agetMilliseconds(self) -> float:
        """
        Return the elapsed time in milliseconds asynchronously.

        Returns
        -------
        float
            Elapsed time in milliseconds as a float.
        """

    @abstractmethod
    def getSeconds(self) -> float:
        """
        Return the elapsed time in seconds.

        Returns
        -------
        float
            Elapsed time in seconds as a float.
        """

    @abstractmethod
    async def agetSeconds(self) -> float:
        """
        Return the elapsed time in seconds asynchronously.

        Returns
        -------
        float
            Elapsed time in seconds as a float.
        """

    @abstractmethod
    def getMinutes(self) -> float:
        """
        Return the elapsed time in minutes.

        Returns
        -------
        float
            Elapsed time in minutes as a float.
        """

    @abstractmethod
    async def agetMinutes(self) -> float:
        """
        Return the elapsed time in minutes asynchronously.

        Returns
        -------
        float
            Elapsed time in minutes as a float.
        """

    @abstractmethod
    def restart(self) -> IPerformanceCounter:
        """
        Restart the performance counter.

        Resets internal timing attributes and starts the counter again. Useful for
        measuring a new interval without creating a new instance.

        Returns
        -------
        IPerformanceCounter
            This instance for method chaining.
        """

    @abstractmethod
    async def arestart(self) -> IPerformanceCounter:
        """
        Restart the performance counter asynchronously.

        Resets internal timing attributes and starts the counter again in async
        mode.

        Returns
        -------
        IPerformanceCounter
            This instance for method chaining.
        """
