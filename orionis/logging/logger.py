# ruff: noqa: BLE001, SLF001, TC001
# Attempt every owned sink on cleanup, annotate cooperating handlers, and retain
# the application contract for runtime dependency injection.
"""Resolve logging channels and dispatch structured log records."""

import asyncio
import logging
import orionis.failure.runtime as failure_runtime
from contextlib import suppress
from pathlib import Path
from threading import Lock
from functools import partial
from typing import ClassVar, Self
from orionis.foundation.config.logging.enums.levels import Level
from orionis.foundation.contracts.application import IApplication
from orionis.logging.contracts.logger import ILogger
from orionis.logging.handlers.queued import (
    BoundedQueueHandler,
    LoggingDeliveryError,
    observe_sink_error,
)
from orionis.logging.handlers.rotating_handler_factory import RotatingHandlerFactory
from orionis.support.concurrency import complete_on_cancel


class Logger(ILogger):
    # Identify the standard logger channel.
    """Resolve logging channels and dispatch structured log records."""

    name: ClassVar[str] = "__orionis__"

    # Share formatters configured with the same message and date formats.
    _formatter_cache: ClassVar[dict[str, logging.Formatter]] = {}
    """Share formatters configured with the same message and date formats."""

    def __init__(self: Self, app: IApplication) -> None:
        """
        Retain logging configuration for lazy handler initialization.

        Parameters
        ----------
        app : orionis.IApplication
            Application instance providing configuration.

        Returns
        -------
        None
            No return value.
        """
        self.__app: IApplication = app
        """Application instance providing configuration."""
        self.__config: dict = app.config("logging")
        """Validated configuration used to construct and operate the service."""
        self.__logger: logging.Logger | None = None
        """Logging implementation used to emit records."""
        self.__handlers_cache: dict[str, logging.Handler] = {}
        """Previously constructed logging handlers indexed by channel."""
        self.__init_lock = Lock()
        """Synchronization primitive controlling access to init lock."""
        # Store the default formatter and logger settings.
        self.__log_format: str = "%(asctime)s [%(levelname)s]: %(message)s"
        """Store the default formatter and logger settings."""
        self.__date_format: str = "%Y-%m-%d %H:%M:%S"
        """Date format identifier: ``%Y-%m-%d %H:%M:%S``."""
        self.__logger_name: str = "__orionis__"
        """Logger name identifier: ``__orionis__``."""
        self.__default_level: int = logging.DEBUG
        """Default level obtained from ``logging.DEBUG``."""

    def __initializeLogger(self: Self) -> None:
        """
        Build the standard library logger for the default channel.

        Configure the shared logger, create the handler declared by the
        default channel and cache it. Fall back to a basic file handler when
        the default channel is not present in the configuration.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        RuntimeError
            If the logger cannot be initialized.
        """
        pending_handler: logging.Handler | None = None
        try:
            # Retrieve the standard logger by name.
            logger = logging.getLogger(self.__logger_name)

            self.__closeConfigurationHandlers(logger)

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
                    log_path = Path(app_root) / channel_config.get(
                        "path",
                        "storage/logs/stack.log",
                    )
                    # Ensure directory exists
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    handler = logging.FileHandler(log_path, encoding="utf-8")
                else:
                    # Use factory for complex handlers (rotating, etc.)
                    handler = RotatingHandlerFactory.createHandler(
                        channel_name=default_channel_name,
                        channel_config=channel_config,
                        app_root=app_root,
                    )
                pending_handler = handler

                # Configure and add handler if created successfully
                if handler:
                    handler.setFormatter(formatter)
                    handler.setLevel(channel_config.get("level", logging.INFO))
                    handler = self.__queueHandler(handler)
                    pending_handler = handler
                    logger.addHandler(handler)
                    self.__handlers_cache[default_channel_name] = handler
                    pending_handler = None
            else:
                # Fallback: create basic file handler
                fallback_path = f"{app_root}/storage/logs/default.log"
                Path(fallback_path).parent.mkdir(parents=True, exist_ok=True)
                handler = logging.FileHandler(fallback_path, encoding="utf-8")
                pending_handler = handler
                handler.setFormatter(formatter)
                handler = self.__queueHandler(handler)
                pending_handler = handler
                logger.addHandler(handler)
                self.__handlers_cache["fallback"] = handler
                pending_handler = None

            self.__logger = logger

        except Exception as e:
            error_msg = f"Failed to initialize logger: {e!s}"
            raise RuntimeError(error_msg) from e
        finally:
            if pending_handler is not None:
                logger.removeHandler(pending_handler)
                self.__handlers_cache.clear()
                self.__discardUnpublishedHandler(pending_handler, phase="configuration")

    def __discardUnpublishedHandler(
        self,
        handler: logging.Handler,
        *,
        phase: str,
    ) -> None:
        """Close an unpublished sink without replacing the configuration failure.

        Parameters
        ----------
        handler : logging.Handler
            Newly created sink whose configuration did not complete.
        phase : str
            Lifecycle operation reported to the failure runtime.

        Returns
        -------
        None
            No return value.
        """
        try:
            handler.close()
        except Exception as error:
            observed = isinstance(handler, BoundedQueueHandler) and isinstance(
                error,
                LoggingDeliveryError,
            )
            if not observed:
                failure_runtime.capture_nowait(
                    error,
                    app=self.__app,
                    flow="logging",
                    phase=phase,
                    operation="close",
                )

    def __closeConfigurationHandlers(self, logger: logging.Logger | None) -> None:
        """Detach and close previous sinks while holding the lifecycle lock.

        Parameters
        ----------
        logger : logging.Logger | None
            Standard logger containing active sinks, or ``None`` before use.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        Exception
            The first cleanup failure after all handlers have been attempted.
        """
        handlers = dict.fromkeys(self.__handlers_cache.values())
        if logger is not None:
            handlers.update(dict.fromkeys(logger.handlers))
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
        self.__handlers_cache.clear()
        self.__logger = None
        errors: list[Exception] = []
        for handler in handlers:
            try:
                handler.close()
            except Exception as error:
                errors.append(error)
                observed = isinstance(handler, BoundedQueueHandler) and isinstance(
                    error,
                    LoggingDeliveryError,
                )
                if len(errors) > 1 and not observed:
                    failure_runtime.capture_nowait(
                        error,
                        app=self.__app,
                        flow="logging",
                        phase="configuration",
                        operation="close",
                    )
        if errors:
            raise errors[0]

    def __queueHandler(self: Self, handler: logging.Handler) -> logging.Handler:
        """
        Enable bounded asynchronous emission only when explicitly configured.

        Parameters
        ----------
        handler : ``logging.Handler``
            Owned handler to wrap when queued logging is enabled.

        Returns
        -------
        ``logging.Handler``
            Queued wrapper when enabled, otherwise the original handler.
        """
        capacity = self.__config.get("queue_capacity", 0)
        handler._orionis_failure_app = self.__app
        if capacity:
            return BoundedQueueHandler(handler, capacity, app=self.__app)
        handler.handleError = partial(
            observe_sink_error,
            app=self.__app,
            original=handler.handleError,
        )
        return handler

    def __createFormatter(self: Self) -> logging.Formatter:
        """
        Return the formatter shared by matching message and date formats.

        Returns
        -------
        ``logging.Formatter``
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
        self: Self,
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
        ``logging.Handler`` | None
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
        except (OSError, ValueError, RuntimeError) as error:
            failure_runtime.capture_nowait(
                error,
                app=self.__app,
                flow="logging",
                phase="configuration",
            )
            return None

    def __normalizeChannelConfig(self: Self, config: dict) -> dict:
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
            normalized["level"] = logging.getLevelNamesMapping().get(
                level.upper(),
                logging.INFO,
            )
        elif level is None:
            normalized["level"] = logging.INFO

        return normalized

    def __ensureLoggerReady(self: Self) -> logging.Logger:
        """
        Return the initialized logger while retaining a stable reference.

        Initialize once under the instance lock and retain the selected logger
        even if another thread closes the service after this method returns.

        Raises
        ------
        RuntimeError
            If the logger cannot be initialized.

        Returns
        -------
        logging.Logger
            Initialized standard logger selected by this call.
        """
        # Return when the logger has already been initialized.
        logger = self.__logger
        if logger is not None:
            return logger

        # Initialize the logger once under the instance lock.
        with self.__init_lock:
            if self.__logger is None:
                self.__initializeLogger()
            logger = self.__logger

        # Final check to ensure logger is available
        if logger is None:
            error_msg = "Logger could not be initialized"
            raise RuntimeError(error_msg)
        return logger

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
            No return value.
        """
        # Initialize the logger before writing the first message.
        logger = self.__logger
        if logger is None:
            logger = self.__ensureLoggerReady()
        logger.info(message)

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
            No return value.
        """
        logger = self.__logger
        if logger is None:
            logger = self.__ensureLoggerReady()
        logger.error(message)

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
            No return value.
        """
        logger = self.__logger
        if logger is None:
            logger = self.__ensureLoggerReady()
        logger.warning(message)

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
            No return value.
        """
        logger = self.__logger
        if logger is None:
            logger = self.__ensureLoggerReady()
        logger.debug(message)

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
            No return value.
        """
        logger = self.__logger
        if logger is None:
            logger = self.__ensureLoggerReady()
        logger.critical(message)

    def getLogger(self: Self) -> logging.Logger:
        """
        Return the internal logger instance for advanced usage.

        Returns
        -------
        ``logging.Logger``
            The configured logger instance.

        Raises
        ------
        RuntimeError
            If the logger is not available.
        """
        return self.__ensureLoggerReady()

    def reloadConfiguration(self: Self) -> None:
        """
        Reload the logger configuration from the application.

        This method allows dynamic reloading of logger settings without restarting
        the application. Every previous handler is detached and closed before
        rebuilding. The first cleanup failure is preserved as the cause of the
        public error; further failures are observed by the failure runtime.

        Returns
        -------
        None
            No return value.
        """
        try:
            # Acquire lock to ensure thread safety during reload
            with self.__init_lock:
                self.__closeConfigurationHandlers(self.__logger)

                # Reload configuration from the application
                self.__config = self.__app.config("logging")

                # Reinitialize the logger with the new configuration
                self.__initializeLogger()
                self.info("Logger configuration reloaded successfully")

        except Exception as e:
            # Raise an error if reloading fails
            error_msg = f"Failed to reload logger configuration: {e}"
            raise RuntimeError(error_msg) from e

    def switchChannel(self: Self, channel_name: str) -> bool:
        """
        Switch to a different logging channel.

        Initialize the logger when needed, close current handlers, clear
        caches, and create a new handler for the specified channel. Attempt every
        old handler once; reject the switch if an active handler fails to close.
        Only one channel is active at a time.

        Parameters
        ----------
        channel_name : str
            Name of the channel to switch to.

        Returns
        -------
        bool
            True if the switch was successful, False otherwise.
        """
        pending_handler: logging.Handler | None = None
        try:
            # Check if channel exists in configuration
            channels: dict = self.__config.get("channels", {})
            if channel_name not in channels:
                return False

            # Initialize outside the lock: __init_lock is not reentrant
            logger = self.__ensureLoggerReady()

            with self.__init_lock:
                # A close between readiness and locking must not discard the
                # standard logger selected for this explicit channel switch.
                self.__logger = logger
                active_handlers = dict.fromkeys(self.__logger.handlers)
                handlers = dict.fromkeys(self.__handlers_cache.values())
                handlers.update(active_handlers)
                # Detach first so a failed close cannot leave a partial sink active.
                for handler in active_handlers:
                    self.__logger.removeHandler(handler)
                failed = False
                for handler in handlers:
                    try:
                        handler.close()
                    except Exception as error:
                        failed |= handler in active_handlers
                        queued = isinstance(handler, BoundedQueueHandler)
                        observed = queued and isinstance(error, LoggingDeliveryError)
                        if not observed:
                            failure_runtime.capture_nowait(
                                error,
                                app=self.__app,
                                flow="logging",
                                phase="switch_channel",
                                operation="close",
                            )
                self.__handlers_cache.clear()
                if failed:
                    self.__logger = None
                    return False

                # Create new handler for the specified channel
                app_root: str = self.__app.path("root")
                channel_config: dict = channels[channel_name]
                formatter: logging.Formatter = self.__createFormatter()

                handler: logging.Handler | None = self.__createChannelHandler(
                    channel_name,
                    channel_config,
                    app_root,
                )
                pending_handler = handler

                if handler:
                    handler.setFormatter(formatter)
                    handler = self.__queueHandler(handler)
                    pending_handler = handler
                    self.__logger.addHandler(handler)
                    self.__handlers_cache[channel_name] = handler
                    pending_handler = None
                    self.info(f"Successfully switched to channel: {channel_name}")
                    return True

                return False

        except (OSError, RuntimeError, ValueError) as error:
            failure_runtime.capture_nowait(
                error,
                app=self.__app,
                flow="logging",
                phase="switch_channel",
            )
            return False
        finally:
            self.__discardChannelHandler(pending_handler, channel_name)

    def __discardChannelHandler(
        self,
        handler: logging.Handler | None,
        channel_name: str,
    ) -> None:
        """Remove an unpublished channel sink without disturbing another switch.

        Parameters
        ----------
        handler : logging.Handler | None
            Pending sink, or ``None`` after successful ownership transfer.
        channel_name : str
            Channel associated with the pending sink.

        Returns
        -------
        None
            No return value.
        """
        if handler is None:
            return
        with self.__init_lock:
            logger = self.__logger
            if logger is not None:
                logger.removeHandler(handler)
            if self.__handlers_cache.get(channel_name) is handler:
                self.__handlers_cache.pop(channel_name)
            self.__discardUnpublishedHandler(handler, phase="switch_channel")

    def close(self: Self) -> None:
        """
        Close all handlers and release logger resources.

        This method should be called when the logger is no longer needed to
        ensure that all file handles and resources are properly released. Attempt
        every handler before propagating an unexpected or queued delivery failure.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        LoggingDeliveryError
            If the first retained failure belongs to queued log delivery.
        Exception
            If another close error is outside the historically recovered
            ``OSError``, ``RuntimeError``, and ``ValueError`` types.
        """
        errors = []
        with self.__init_lock:
            handlers = dict.fromkeys(self.__handlers_cache.values())
            if self.__logger is not None:
                handlers.update(dict.fromkeys(self.__logger.handlers))
                for handler in self.__logger.handlers[:]:
                    self.__logger.removeHandler(handler)
            for handler in handlers:
                try:
                    handler.close()
                except LoggingDeliveryError as error:
                    if not isinstance(handler, BoundedQueueHandler):
                        failure_runtime.capture_nowait(
                            error,
                            app=self.__app,
                            flow="logging",
                            phase="cleanup",
                        )
                    errors.append(error)
                except (OSError, RuntimeError, ValueError) as error:
                    # Preserve synchronous handler cleanup compatibility.
                    failure_runtime.capture_nowait(
                        error,
                        app=self.__app,
                        flow="logging",
                        phase="cleanup",
                    )
                except Exception as error:
                    failure_runtime.capture_nowait(
                        error,
                        app=self.__app,
                        flow="logging",
                        phase="cleanup",
                    )
                    errors.append(error)
            self.__handlers_cache.clear()
            self.__logger = None
        if not errors:
            return
        if not isinstance(errors[0], LoggingDeliveryError):
            raise errors[0]
        error_msg = "One or more background logging sinks failed during shutdown."
        raise LoggingDeliveryError(error_msg) from errors[0]

    async def aclose(self: Self) -> None:
        """
        Drain queued records and close handlers without blocking the event loop.

        Returns
        -------
        None
            No return value.
        """
        await complete_on_cancel(asyncio.to_thread(self.close))

    def getActiveChannels(self: Self) -> list[str]:
        """
        Return the names of active logging channels.

        Returns
        -------
        list[str]
            List containing the names of active logging channels.
        """
        # Return the keys from the handlers cache as the active channel names
        return list(self.__handlers_cache.keys())

    def getActiveChannel(self: Self) -> str | None:
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

    def getAvailableChannels(self: Self) -> list[str]:
        """
        Return all available logging channels from configuration.

        Returns
        -------
        list[str]
            List of all configured channel names.
        """
        # Extract channel names from configuration dictionary
        return list(self.__config.get("channels", {}).keys())

    def __del__(self: Self) -> None:
        """
        Release resources when the logger is destroyed.

        Calls the ``close`` method to ensure all handlers and resources are
        properly released when the logger instance is garbage collected.

        Returns
        -------
        None
            No return value.
        """
        # Suppress exceptions to avoid errors during garbage collection
        with suppress(Exception):
            self.close()
