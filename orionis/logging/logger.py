import logging
from contextlib import suppress
from pathlib import Path
from threading import Lock
from typing import ClassVar
from orionis.foundation.config.logging.enums.levels import Level
from orionis.foundation.contracts.application import IApplication
from orionis.logging.contracts.logger import ILogger
from orionis.logging.handlers.rotating_handler_factory import RotatingHandlerFactory

class Logger(ILogger):

    # ruff: noqa: RUF012, TC001

    # Identify the standard logger channel.
    name: ClassVar[str] = "__orionis__"

    # Share formatters configured with the same message and date formats.
    _formatter_cache: dict[str, logging.Formatter] = {}

    def __init__(self, app: IApplication) -> None:
        """
        Initialize the Logger instance with ultra-fast optimization.

        Parameters
        ----------
        app : IApplication
            Application instance providing configuration.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__app: IApplication = app
        self.__config: dict = app.config("logging")
        self.__logger: logging.Logger | None = None
        self.__handlers_cache: dict[str, logging.Handler] = {}
        self.__init_lock = Lock()
        # Store the default formatter and logger settings.
        self.__log_format: str = "%(asctime)s [%(levelname)s]: %(message)s"
        self.__date_format: str = "%Y-%m-%d %H:%M:%S"
        self.__logger_name: str = "__orionis__"
        self.__default_level: int = logging.DEBUG

    def __initializeLogger(self) -> None:
        """
        Build the standard library logger for the default channel.

        Configure the shared logger, create the handler declared by the
        default channel and cache it. Fall back to a basic file handler when
        the default channel is not present in the configuration.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        RuntimeError
            If the logger cannot be initialized.
        """
        try:

            # Retrieve the standard logger by name.
            logger = logging.getLogger(self.__logger_name)

            # Close handlers left by an earlier logger instance.
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

            # Basic logger setup
            logger.setLevel(self.__default_level)
            logger.propagate = False

            # Retrieve the formatter for the default channel.
            formatter = self.__createFormatter()

            # Configure the handler selected by the default channel.
            default_channel_name = self.__config.get("default", "stack")
            channels = self.__config.get("channels", {})
            app_root = self.__app.path("root")

            if default_channel_name in channels:

                # Convert the configured logging level to an integer.
                channel_config: dict = self.__normalizeChannelConfig(
                    channels[default_channel_name],
                )

                # Create the stack channel's file handler.
                if default_channel_name == "stack":
                    log_path = f"{app_root}/{channel_config.get(
                        'path',
                        'storage/logs/stack.log'
                    )}"
                    # Ensure directory exists
                    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
                    handler = logging.FileHandler(log_path, encoding="utf-8")
                else:
                    # Use factory for complex handlers (rotating, etc.)
                    handler = RotatingHandlerFactory.createHandler(
                        channel_name=default_channel_name,
                        channel_config=channel_config,
                        app_root=app_root,
                    )

                # Configure and add handler if created successfully
                if handler:
                    handler.setFormatter(formatter)
                    handler.setLevel(channel_config.get("level", logging.INFO))
                    logger.addHandler(handler)
                    self.__handlers_cache[default_channel_name] = handler
            else:
                # Fallback: create basic file handler
                fallback_path = f"{app_root}/storage/logs/default.log"
                Path(fallback_path).parent.mkdir(parents=True, exist_ok=True)
                handler = logging.FileHandler(fallback_path, encoding="utf-8")
                handler.setFormatter(formatter)
                logger.addHandler(handler)
                self.__handlers_cache["fallback"] = handler

            self.__logger = logger

        except Exception as e:
            error_msg = f"Failed to initialize logger: {e!s}"
            raise RuntimeError(error_msg) from e

    def __createFormatter(self) -> logging.Formatter:
        """
        Create and return an optimized log formatter with caching.

        Returns
        -------
        logging.Formatter
            The configured formatter instance for log messages.
        """
        # Identify the formatter by its message and date formats.
        cache_key: str = f"{self.__log_format}|{self.__date_format}"

        # Return a formatter already configured with these formats.
        if cache_key in Logger._formatter_cache:
            return Logger._formatter_cache[cache_key]

        # Store the newly configured formatter.
        formatter: logging.Formatter = logging.Formatter(
            self.__log_format,
            datefmt=self.__date_format,
        )
        Logger._formatter_cache[cache_key] = formatter
        return formatter

    def __createChannelHandler(
        self,
        channel_name: str,
        channel_config: dict,
        app_root: str,
    ) -> logging.Handler | None:
        """
        Create a handler for a specific channel.

        Parameters
        ----------
        channel_name : str
            The name of the channel.
        channel_config : dict
            The configuration dictionary for the channel.
        app_root : str
            The root path of the application.

        Returns
        -------
        logging.Handler | None
            The configured handler instance, or None if creation fails.
        """
        try:
            # Normalize channel configuration for consistency
            normalized_config: dict = self.__normalizeChannelConfig(channel_config)
            # Create handler using the factory
            handler: logging.Handler | None = RotatingHandlerFactory.createHandler(
                channel_name=channel_name,
                channel_config=normalized_config,
                app_root=app_root,
            )
            return handler
        except (OSError, ValueError, RuntimeError):
            return None

    def __normalizeChannelConfig(self, config: dict) -> dict:
        """
        Normalize the channel configuration for logging.

        Parameters
        ----------
        config : dict
            Original channel configuration.

        Returns
        -------
        dict
            Normalized channel configuration with ensured defaults.
        """
        # Normalize a separate copy of the channel configuration.
        normalized: dict = dict(config)

        # Ensure the logging level is an integer value
        level = normalized.get("level")
        if isinstance(level, Level) or hasattr(level, "value"):
            normalized["level"] = level.value
        elif isinstance(level, str):
            normalized["level"] = getattr(logging, level.upper(), logging.INFO)
        elif level is None:
            normalized["level"] = logging.INFO

        return normalized

    def __ensureLoggerReady(self) -> None:
        """
        Ensure the logger is initialized and ready for use with ultra-fast lazy init.

        Uses optimized double-checked locking for maximum performance.

        Raises
        ------
        RuntimeError
            If the logger cannot be initialized.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Return when the logger has already been initialized.
        if self.__logger is not None:
            return

        # Initialize the logger once under the instance lock.
        with self.__init_lock:
            if self.__logger is None:
                self.__initializeLogger()

        # Final check to ensure logger is available
        if self.__logger is None:
            error_msg = "Logger could not be initialized"
            raise RuntimeError(error_msg)

    def info(self, message: str) -> None:
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
        # Initialize the logger before writing the first message.
        if self.__logger is None:
            self.__ensureLoggerReady()
        self.__logger.info(message)

    def error(self, message: str) -> None:
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
        if self.__logger is None:
            self.__ensureLoggerReady()
        self.__logger.error(message)

    def warning(self, message: str) -> None:
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
        if self.__logger is None:
            self.__ensureLoggerReady()
        self.__logger.warning(message)

    def debug(self, message: str) -> None:
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
        if self.__logger is None:
            self.__ensureLoggerReady()
        self.__logger.debug(message)

    def critical(self, message: str) -> None:
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
        if self.__logger is None:
            self.__ensureLoggerReady()
        self.__logger.critical(message)

    def getLogger(self) -> logging.Logger:
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
        self.__ensureLoggerReady()
        return self.__logger

    def reloadConfiguration(self) -> None:
        """
        Reload the logger configuration from the application.

        This method allows dynamic reloading of logger settings without restarting
        the application.

        Returns
        -------
        None
            This method does not return a value.
        """
        try:

            # Acquire lock to ensure thread safety during reload
            with self.__init_lock:

                # Close existing handlers and remove them from the logger.
                # Iterate over a copy: removeHandler mutates the same list.
                if self.__logger:
                    for handler in self.__logger.handlers[:]:
                        handler.close()
                        self.__logger.removeHandler(handler)

                # Clear the handler cache and reset the logger reference
                self.__handlers_cache.clear()
                self.__logger = None

                # Reload configuration from the application
                self.__config = self.__app.config("logging")

                # Reinitialize the logger with the new configuration
                self.__initializeLogger()
                self.info("Logger configuration reloaded successfully")

        except Exception as e:

            # Raise an error if reloading fails
            error_msg = f"Failed to reload logger configuration: {e}"
            raise RuntimeError(error_msg) from e

    def switchChannel(self, channel_name: str) -> bool:
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
        try:
            # Check if channel exists in configuration
            channels: dict = self.__config.get("channels", {})
            if channel_name not in channels:
                return False

            # Initialize outside the lock: __init_lock is not reentrant
            if self.__logger is None:
                self.__ensureLoggerReady()

            with self.__init_lock:

                # Close current handlers and remove from logger.
                # Iterate over a copy: removeHandler mutates the same list.
                for handler in self.__logger.handlers[:]:
                    handler.close()
                    self.__logger.removeHandler(handler)

                # Clear cached handlers
                for handler in self.__handlers_cache.values():
                    with suppress(OSError, RuntimeError, ValueError):
                        handler.close()
                self.__handlers_cache.clear()

                # Create new handler for the specified channel
                app_root: str = self.__app.path("root")
                channel_config: dict = channels[channel_name]
                formatter: logging.Formatter = self.__createFormatter()

                handler: logging.Handler | None = self.__createChannelHandler(
                    channel_name,
                    channel_config,
                    app_root,
                )

                if handler:
                    handler.setFormatter(formatter)
                    self.__logger.addHandler(handler)
                    self.__handlers_cache[channel_name] = handler
                    self.info(f"Successfully switched to channel: {channel_name}")
                    return True

                return False

        except (OSError, RuntimeError, ValueError):
            return False

    def close(self) -> None:
        """
        Close all handlers and release logger resources.

        This method should be called when the logger is no longer needed to
        ensure that all file handles and resources are properly released.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Suppress common exceptions to avoid errors during cleanup
        # and acquire lock for thread-safe cleanup
        with suppress(OSError, RuntimeError, ValueError), self.__init_lock:

            # Close and remove handlers from the main logger
            if self.__logger:

                # Close and remove all handlers from the logger.
                # Iterate over a copy: removeHandler mutates the same list.
                for handler in self.__logger.handlers[:]:
                    with suppress(OSError, RuntimeError, ValueError):
                        handler.close()
                    self.__logger.removeHandler(handler)

            # Close and clear cached handlers
            for handler in self.__handlers_cache.values():

                # Suppress exceptions during handler closure
                with suppress(OSError, RuntimeError, ValueError):
                    handler.close()

            # Clear the handlers cache and reset the logger reference
            self.__handlers_cache.clear()
            self.__logger = None

    def getActiveChannels(self) -> list[str]:
        """
        Return the names of active logging channels.

        Returns
        -------
        list[str]
            List containing the names of active logging channels.
        """
        # Return the keys from the handlers cache as the active channel names
        return list(self.__handlers_cache.keys())

    def getActiveChannel(self) -> str | None:
        """
        Return the name of the currently active logging channel.

        Returns
        -------
        str | None
            The name of the active channel, or None if no channel is active.
        """
        channels: list[str] = self.getActiveChannels()
        # Return the first active channel if available, otherwise None
        return channels[0] if channels else None

    def getAvailableChannels(self) -> list[str]:
        """
        Return all available logging channels from configuration.

        Returns
        -------
        list[str]
            List of all configured channel names.
        """
        # Extract channel names from configuration dictionary
        return list(self.__config.get("channels", {}).keys())

    def __del__(self) -> None:
        """
        Release resources when the logger is destroyed.

        Calls the `close` method to ensure all handlers and resources are
        properly released when the logger instance is garbage collected.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Suppress exceptions to avoid errors during garbage collection
        with suppress(Exception):
            self.close()
