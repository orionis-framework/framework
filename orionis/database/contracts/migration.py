from abc import ABC, abstractmethod

class Migration(ABC):
    """
    Abstract base class for all database migrations.

    This class defines the contract that every migration must implement.
    A migration represents a reversible set of schema changes that can be
    applied to or reverted from the database.

    Subclasses must implement the :meth:`up` and :meth:`down` methods to
    describe how the migration is applied and rolled back, respectively.

    Notes
    -----
    This class is intended to be executed by the migration manager rather
    than instantiated directly.

    See Also
    --------
    Migrator
        Executes and manages migration lifecycle operations.
    """

    __slots__ = ()

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
            This method does not return a value.

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

        This method should undo the changes performed by :meth:`up`,
        restoring the database schema to its previous state whenever
        possible.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        Exception
            Any exception raised during execution should indicate that the
            migration rollback could not be completed successfully.
        """
