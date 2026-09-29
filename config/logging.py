from __future__ import annotations
from dataclasses import dataclass, field
from datetime import time
from orionis.environment import Env
from orionis.foundation.config.logging import (
    Channels, Chunked, Daily, Hourly, Level, Logging,
    Monthly, Stack, Weekly,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapLogging(Logging):
    # ----------------------------------------------------------------------------------
    # default : str, optional
    # --- The default logging channel name.
    # --- Uses the LOG_CHANNEL env var or "stack" if not set.
    # ----------------------------------------------------------------------------------
    default: str = field(
        default_factory=lambda: Env.get("LOG_CHANNEL", "stack"),
    )

    # ----------------------------------------------------------------------------------
    # channels : Channels | dict, optional
    # --- Configure each channel's environment keys and fallback values here.
    # --- Shared LOG_PATH and LOG_RETENTION apply only to the selected channel.
    # --- Use Env.get with dedicated keys for independent channel settings.
    # ----------------------------------------------------------------------------------
    channels: Channels | dict = field(
        default_factory=lambda: Channels(
            # --------------------------------------------------------------------------
            # stack : Stack, optional
            # --- Log file for entries without time or size rotation.
            # --------------------------------------------------------------------------
            stack=Stack(
                path=Env.get("LOG_PATH", "storage/logs/stack.log"),
                level=Env.get("LOG_LEVEL", Level.INFO),
            ),
            # --------------------------------------------------------------------------
            # hourly : Hourly, optional
            # --- Hourly log rotation with retention measured in hours.
            # --------------------------------------------------------------------------
            hourly=Hourly(
                path=Env.get("LOG_PATH", "storage/logs/hourly_{suffix}.log"),
                level=Env.get("LOG_LEVEL", Level.INFO),
                retention_hours=Env.get("LOG_RETENTION", 24),
            ),
            # --------------------------------------------------------------------------
            # daily : Daily, optional
            # --- Daily log rotation with a configurable time and retention in days.
            # --------------------------------------------------------------------------
            daily=Daily(
                path=Env.get("LOG_PATH", "storage/logs/daily_{suffix}.log"),
                level=Env.get("LOG_LEVEL", Level.INFO),
                retention_days=Env.get("LOG_RETENTION", 7),
                at=Env.get("LOG_ROTATION_TIME", time(hour=0, minute=0, second=0)),
            ),
            # --------------------------------------------------------------------------
            # weekly : Weekly, optional
            # --- Weekly log rotation with retention measured in weeks.
            # --------------------------------------------------------------------------
            weekly=Weekly(
                path=Env.get("LOG_PATH", "storage/logs/weekly_{suffix}.log"),
                level=Env.get("LOG_LEVEL", Level.INFO),
                retention_weeks=Env.get("LOG_RETENTION", 4),
            ),
            # --------------------------------------------------------------------------
            # monthly : Monthly, optional
            # --- Monthly log rotation with retention measured in months.
            # --------------------------------------------------------------------------
            monthly=Monthly(
                path=Env.get("LOG_PATH", "storage/logs/monthly_{suffix}.log"),
                level=Env.get("LOG_LEVEL", Level.INFO),
                retention_months=Env.get("LOG_RETENTION", 12),
            ),
            # --------------------------------------------------------------------------
            # chunked : Chunked, optional
            # --- Rotation by file size, with a size limit and a retained file count.
            # --------------------------------------------------------------------------
            chunked=Chunked(
                path=Env.get("LOG_PATH", "storage/logs/chunked_{suffix}.log"),
                level=Env.get("LOG_LEVEL", Level.INFO),
                mb_size=Env.get("LOG_MB_SIZE", 10),
                files=Env.get("LOG_FILES", 5),
            ),
        ),
    )
