from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orionis.database.migrations.events import MigrationEvents

class IMigrator(ABC):
    """
    Contract for the database migration runner.

    Implementations discover migration files under the application's
    ``database/migrations`` directory, track which ones have already been
    applied, and apply or revert them in chronological order against any
    configured connection.
    """

    __slots__ = ()

    @abstractmethod
    async def migrate(
        self,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Apply every migration that has not been run yet.

        Parameters
        ----------
        connection : str or None, optional
            Named connection to migrate, or ``None`` for the default one.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations applied, in the order they ran. Empty
            when there is nothing pending.

        Raises
        ------
        Exception
            Any exception raised by a migration's ``up`` method aborts
            the run and propagates to the caller.
        """

    @abstractmethod
    async def rollback(
        self,
        steps: int = 1,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Revert the most recently applied migration batches.

        Parameters
        ----------
        steps : int, optional
            Number of batches to roll back, starting from the most
            recent one. Defaults to ``1``.
        connection : str or None, optional
            Named connection to roll back, or ``None`` for the default.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations reverted, most recent first. Empty
            when there is nothing to revert.

        Raises
        ------
        ValueError
            If ``steps`` is not a positive integer.
        MigrationNotFoundException
            If a recorded migration has no matching migration file.
        """

    @abstractmethod
    async def reset(
        self,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Revert every migration recorded on the connection.

        Parameters
        ----------
        connection : str or None, optional
            Named connection to reset, or ``None`` for the default one.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations reverted, most recent first.

        Raises
        ------
        MigrationNotFoundException
            If a recorded migration has no matching migration file.
        """

    @abstractmethod
    async def refresh(
        self,
        steps: int | None = None,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Roll back migrations and immediately apply them again.

        Parameters
        ----------
        steps : int or None, optional
            Number of batches to roll back first; ``None`` rolls back
            every recorded migration.
        connection : str or None, optional
            Named connection to refresh, or ``None`` for the default.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations re-applied, in the order they ran.

        Raises
        ------
        ValueError
            If ``steps`` is not a positive integer.
        """

    @abstractmethod
    async def fresh(
        self,
        *,
        connection: str | None = None,
        events: MigrationEvents | None = None,
    ) -> list[str]:
        """
        Drop the tracking table and apply every migration from scratch.

        Parameters
        ----------
        connection : str or None, optional
            Named connection to rebuild, or ``None`` for the default.
        events : MigrationEvents or None, optional
            Progress callbacks reported for each migration.

        Returns
        -------
        list of str
            Names of the migrations applied, in the order they ran.
        """

    @abstractmethod
    async def status(
        self,
        *,
        connection: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Report which migrations are applied and which are pending.

        Parameters
        ----------
        connection : str or None, optional
            Named connection to inspect, or ``None`` for the default.

        Returns
        -------
        list of dict
            One entry per discovered migration with ``migration``,
            ``ran`` and ``batch`` keys, in chronological order.
        """
