from __future__ import annotations
from logging import FileHandler
from pathlib import Path
from typing import TYPE_CHECKING
from orionis.logging.handlers.advanced_rotating_file_handler import (
    AdvancedRotatingFileHandler,
)
from orionis.logging.handlers.chunked_suffix_resolver import ChunkedSuffixResolver
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.hourly_suffix_resolver import HourlySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver

if TYPE_CHECKING:
    from collections.abc import Callable
    from logging import Handler

def _create_stack(
    _channel_config: dict, app_root: str, path_template: str, level: int,
) -> Handler:
    """
    Create a non-rotating file handler for the stack channel.

    Parameters
    ----------
    _channel_config : dict
        Channel configuration dictionary (unused for this handler type).
    app_root : str
        Root path of the application.
    path_template : str
        Relative or absolute log file path template.
    level : int
        Logging level to apply to the handler.

    Returns
    -------
    Handler
        Configured ``FileHandler`` instance.
    """
    full_path: Path = Path(app_root) / path_template
    full_path.parent.mkdir(parents=True, exist_ok=True)
    handler = FileHandler(str(full_path), encoding="utf-8", delay=True)
    handler.setLevel(level)
    return handler

def _create_hourly(
    channel_config: dict, app_root: str, path_template: str, level: int,
) -> Handler:
    """
    Create an hourly rotating file handler.

    Parameters
    ----------
    channel_config : dict
        Channel configuration dictionary. Supports ``retention_hours`` to
        control backup retention.
    app_root : str
        Root path of the application.
    path_template : str
        Relative or absolute log file path template.
    level : int
        Logging level to apply to the handler.

    Returns
    -------
    Handler
        Configured ``AdvancedRotatingFileHandler`` instance using an hourly
        suffix resolver.
    """
    resolver = HourlySuffixResolver()
    retention_hours = channel_config.get("retention_hours", 24)
    handler = AdvancedRotatingFileHandler(
        path_template=path_template,
        suffix_resolver=resolver,
        backup_count=retention_hours,
        app_root=app_root,
    )
    handler.setLevel(level)
    return handler

def _create_daily(
    channel_config: dict, app_root: str, path_template: str, level: int,
) -> Handler:
    """
    Create a daily rotating file handler.

    Parameters
    ----------
    channel_config : dict
        Channel configuration dictionary. Supports ``at`` for rotation time
        and ``retention_days`` to control backup retention.
    app_root : str
        Root path of the application.
    path_template : str
        Relative or absolute log file path template.
    level : int
        Logging level to apply to the handler.

    Returns
    -------
    Handler
        Configured ``AdvancedRotatingFileHandler`` instance using a daily
        suffix resolver.
    """
    at_time = channel_config.get("at")
    resolver = DailySuffixResolver(at_time)
    retention_days = channel_config.get("retention_days", 7)
    handler = AdvancedRotatingFileHandler(
        path_template=path_template,
        suffix_resolver=resolver,
        backup_count=retention_days,
        app_root=app_root,
    )
    handler.setLevel(level)
    return handler

def _create_weekly(
    channel_config: dict, app_root: str, path_template: str, level: int,
) -> Handler:
    """
    Create a weekly rotating file handler.

    Parameters
    ----------
    channel_config : dict
        Channel configuration dictionary. Supports ``at`` for rotation time
        and ``retention_weeks`` to control backup retention.
    app_root : str
        Root path of the application.
    path_template : str
        Relative or absolute log file path template.
    level : int
        Logging level to apply to the handler.

    Returns
    -------
    Handler
        Configured ``AdvancedRotatingFileHandler`` instance using a weekly
        suffix resolver.
    """
    at_time = channel_config.get("at")
    resolver = WeeklySuffixResolver(at_time)
    retention_weeks = channel_config.get("retention_weeks", 4)
    handler = AdvancedRotatingFileHandler(
        path_template=path_template,
        suffix_resolver=resolver,
        backup_count=retention_weeks,
        app_root=app_root,
    )
    handler.setLevel(level)
    return handler

def _create_monthly(
    channel_config: dict, app_root: str, path_template: str, level: int,
) -> Handler:
    """
    Create a monthly rotating file handler.

    Parameters
    ----------
    channel_config : dict
        Channel configuration dictionary. Supports ``at`` for rotation time
        and ``retention_months`` to control backup retention.
    app_root : str
        Root path of the application.
    path_template : str
        Relative or absolute log file path template.
    level : int
        Logging level to apply to the handler.

    Returns
    -------
    Handler
        Configured ``AdvancedRotatingFileHandler`` instance using a monthly
        suffix resolver.
    """
    at_time = channel_config.get("at")
    resolver = MonthlySuffixResolver(at_time)
    retention_months = channel_config.get("retention_months", 4)
    handler = AdvancedRotatingFileHandler(
        path_template=path_template,
        suffix_resolver=resolver,
        backup_count=retention_months,
        app_root=app_root,
    )
    handler.setLevel(level)
    return handler

def _create_chunked(
    channel_config: dict, app_root: str, path_template: str, level: int,
) -> Handler:
    """Create a size-based rotating file handler.

    Parameters
    ----------
    channel_config : dict
        Channel settings containing optional ``mb_size`` and ``files`` values.
    app_root : str
        Root path of the application.
    path_template : str
        Relative or absolute log file path template.
    level : int
        Logging level to apply to the handler.

    Returns
    -------
    Handler
        Configured ``AdvancedRotatingFileHandler`` instance using chunked
        rotation and compressed rotated files.
    """
    resolver = ChunkedSuffixResolver()
    mb_size = channel_config.get("mb_size", 10)
    max_bytes = mb_size * 1024 * 1024
    files = channel_config.get("files", 5)
    handler = AdvancedRotatingFileHandler(
        path_template=path_template,
        suffix_resolver=resolver,
        max_bytes=max_bytes,
        backup_count=files,
        app_root=app_root,
        compress_rotated=True,
    )
    handler.setLevel(level)
    return handler

# Mapping of channel types to their respective handler creation functions
_CHANNEL_CREATORS: dict[str, Callable[[dict, str, str, int], Handler]] = {
    "stack": _create_stack,
    "hourly": _create_hourly,
    "daily": _create_daily,
    "weekly": _create_weekly,
    "monthly": _create_monthly,
    "chunked": _create_chunked,
}

class RotatingHandlerFactory:

    @staticmethod
    def createHandler(
        channel_name: str,
        channel_config: dict,
        app_root: str,
    ) -> Handler | None:
        """
        Create and return a log handler based on the channel configuration.

        Parameters
        ----------
        channel_name : str
            Name of the channel (e.g., stack, hourly, daily).
        channel_config : dict
            Channel configuration dictionary.
        app_root : str
            Root path of the application.

        Returns
        -------
        Handler | None
            Configured log handler instance, or None if the type is unsupported.
        """
        # Resolve log file path and log level from configuration
        path_template: str = channel_config.get("path", "storage/logs/default.log")
        level: int = channel_config.get("level", 20)  # Default to INFO

        # O(1) dict lookup replaces linear if-chain (M4)
        creator = _CHANNEL_CREATORS.get(channel_name)
        if creator is None:
            return None
        return creator(channel_config, app_root, path_template, level)
