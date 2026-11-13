"""Abstract base class for all database migrations."""

from abc import ABC, abstractmethod


class Migration(ABC):
    """
    Abstract base class for all database migrations.

    This class defines the contract that every migration must implement.
    A migration represents a reversible set of schema changes that can be
    applied to or reverted from the database.

    Subclasses must implement the :meth:`orionis.database.Migration.up` and
    :meth:`orionis.database.Migration.down` methods to
    describe how the migration is applied and rolled back, respectively.

    Notes
    -----
    This class is intended to be executed by the migration manager rather
    than instantiated directly.

    See Also
    --------
    orionis.database.migrations.Migrator
        Executes and manages migration lifecycle operations.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def up(self) -> None:
        """
        Apply the migration.

        This method is responsible for performing the database schema
        changes associated with the migration, such as creating or
        modifying tables, indexes, constraints, or other database objects.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        Exception
            Any exception raised during execution should indicate that the
            migration could not be applied successfully.
        """

    @abstractmethod
    async def down(self) -> None:
        """
        Revert the migration.

        This method should undo the changes performed by
        :meth:`orionis.database.Migration.up`,
        restoring the database schema to its previous state whenever
        possible.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        Exception
            Any exception raised during execution should indicate that the
            migration rollback could not be completed successfully.
        """
