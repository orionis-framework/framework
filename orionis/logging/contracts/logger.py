from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self
from orionis.support.concurrency import complete_on_cancel

if TYPE_CHECKING:
    import logging

class ILogger(ABC):

    async def aclose(self: Self) -> None:
        """
        Drain and close the logger without blocking the application event loop.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        await complete_on_cancel(asyncio.to_thread(self.close))

    @property
    @abstractmethod
    def name(self: Self) -> str:
        """
        Return the name of the logger service.

        Returns
        -------
        str
            The name of the logger service.
        """

    @abstractmethod
    def info(self: Self, message: str) -> None:
        """
        Log an informational message.

        Parameters
        ----------
        message : str
            The message to log.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def error(self: Self, message: str) -> None:
        """
        Log an error message.

        Parameters
        ----------
        message : str
            Error message to log.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def warning(self: Self, message: str) -> None:
        """
        Log a warning message.

        Parameters
        ----------
        message : str
            Warning message to log.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def debug(self: Self, message: str) -> None:
        """
        Log a debug message.

        Parameters
        ----------
        message : str
            Debug message to log.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def critical(self: Self, message: str) -> None:
        """
        Log a critical message.

        Parameters
        ----------
        message : str
            Critical message to log.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def getLogger(self: Self) -> logging.Logger:
        """
        Return the internal logger instance for advanced usage.

        Returns
        -------
        logging.Logger
            The configured logger instance.

        Raises
        ------
        RuntimeError
            If the logger is not available.
        """

    @abstractmethod
    def reloadConfiguration(self: Self) -> None:
        """
        Reload the logger configuration from the application.

        This method allows dynamic reloading of logger settings without restarting
        the application.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def switchChannel(self: Self, channel_name: str) -> bool:
        """
        Switch to a different logging channel.

        Initialize the logger when needed, close current handlers, clear
        caches, and create a new handler for the specified channel. Only one
        channel is active at a time.

        Parameters
        ----------
        channel_name : str
            Name of the channel to switch to.

        Returns
        -------
        bool
            True if the switch was successful, False otherwise.
        """

    @abstractmethod
    def close(self: Self) -> None:
        """
        Close all handlers and release logger resources.

        This method should be called when the logger is no longer needed to
        ensure that all file handles and resources are properly released.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def getActiveChannels(self: Self) -> list[str]:
        """
        Return the names of active logging channels.

        Returns
        -------
        list[str]
            List containing the names of active logging channels.
        """

    @abstractmethod
    def getActiveChannel(self: Self) -> str | None:
        """
        Return the name of the currently active logging channel.

        Returns
        -------
        str | None
            The name of the active channel, or None if no channel is active.
        """

    @abstractmethod
    def getAvailableChannels(self: Self) -> list[str]:
        """
        Return all available logging channels from configuration.

        Returns
        -------
        list[str]
            List of all configured channel names.
        """
