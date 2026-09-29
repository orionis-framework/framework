from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

@dataclass(frozen=True, slots=True, kw_only=True)
class MigrationEvents:
    """
    Progress callbacks reported while migrations run.

    Grouping the callbacks keeps the migrator free of any dependency on
    the console layer: the caller decides how each event is rendered.

    Attributes
    ----------
    on_start : callable or None
        Invoked with the migration name right before it runs.
    on_success : callable or None
        Invoked with the migration name and elapsed seconds once it
        completes successfully.
    on_error : callable or None
        Invoked with the migration name and elapsed seconds when it
        fails, right before the exception propagates.
    """

    on_start: Callable[[str], None] | None = None
    on_success: Callable[[str, float], None] | None = None
    on_error: Callable[[str, float], None] | None = None

    def started(self, name: str) -> None:
        """
        Report that a migration is about to run.

        Parameters
        ----------
        name : str
            Migration name.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self.on_start is not None:
            self.on_start(name)

    def succeeded(self, name: str, elapsed: float) -> None:
        """
        Report that a migration completed successfully.

        Parameters
        ----------
        name : str
            Migration name.
        elapsed : float
            Seconds the migration took.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self.on_success is not None:
            self.on_success(name, elapsed)

    def failed(self, name: str, elapsed: float) -> None:
        """
        Report that a migration failed.

        Parameters
        ----------
        name : str
            Migration name.
        elapsed : float
            Seconds elapsed before the failure.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self.on_error is not None:
            self.on_error(name, elapsed)


# Shared instance used when the caller reports no progress at all.
NO_EVENTS: MigrationEvents = MigrationEvents()
