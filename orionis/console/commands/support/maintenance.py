from contextlib import suppress
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import sleep
from typing import ClassVar
from filelock import FileLock
from orionis.console.base.command import BaseCommand
from orionis.console.output.console import Console
from orionis.foundation.contracts.application import IApplication

_REPLACE_ATTEMPTS = 6


class MaintenanceModeCommand(BaseCommand):
    """Write a runtime-visible maintenance state for HTTP workers."""

    # ruff: noqa: TC001

    timestamps: bool = False
    state: ClassVar[str]
    status_message: ClassVar[str]

    def handle(self, app: IApplication, console: Console) -> int:
        """
        Atomically update the state periodically read by HTTP workers.

        Parameters
        ----------
        app : IApplication
            Application providing the framework storage directory.
        console : Console
            Console used to report the state change.

        Returns
        -------
        int
            Zero when the state is written; one when the write fails.
        """
        state_file = app.path("storage_framework") / "maintenance"
        temporary_file: Path | None = None
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix=".maintenance.",
                suffix=".tmp",
                dir=state_file.parent,
                delete=False,
            ) as temporary:
                temporary_file = Path(temporary.name)
                temporary.write(self.state)
            with FileLock(str(state_file.with_name(".maintenance.lock"))):
                for attempt in range(_REPLACE_ATTEMPTS):
                    try:
                        temporary_file.replace(state_file)
                    except PermissionError:
                        if attempt == _REPLACE_ATTEMPTS - 1:
                            raise
                        sleep(0.005 * (1 << attempt))
                    else:
                        break
        except OSError as error:
            if temporary_file is not None:
                with suppress(OSError):
                    temporary_file.unlink(missing_ok=True)
            console.error(
                f"Maintenance state could not be changed: {error}",
                timestamp=False,
            )
            return 1

        console.success(self.status_message, timestamp=False)
        return 0
