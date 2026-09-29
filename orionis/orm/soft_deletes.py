from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

class SoftDeletesMixin:
    """
    Soft delete behavior shared by every model.

    A model opts in by declaring ``soft_deletes = True`` together with a
    ``deleted_at`` column. Deleting then stamps that column instead of
    removing the row, queries exclude stamped rows by default, and the
    row can be brought back with :meth:`restore`.
    """

    __slots__ = ()

    def trashed(self) -> bool:
        """
        Report whether the instance is currently soft deleted.

        Returns
        -------
        bool
            ``True`` when the soft delete column carries a timestamp.
        """
        column = self.__meta__.deleted_column
        return column is not None and self._attributes.get(column) is not None

    async def restore(self) -> bool:
        """
        Bring a soft deleted row back by clearing its delete stamp.

        Returns
        -------
        bool
            ``True`` when the row was restored, ``False`` when the model
            does not soft delete, was never persisted, or a listener
            vetoed the operation.

        Raises
        ------
        QueryException
            If the statement fails to execute.
        """
        column = self.__meta__.deleted_column
        if column is None or not self._exists:
            return False
        if not await self.fireEvent("restoring"):
            return False

        self._attributes[column] = None
        restored = await self._performUpdate()
        await self.fireEvent("restored")
        return restored

    async def forceDelete(self) -> bool:
        """
        Delete the row permanently, ignoring soft deletes.

        Returns
        -------
        bool
            ``True`` when a row was removed, ``False`` for unsaved
            models or when a listener vetoed the operation.

        Raises
        ------
        QueryException
            If the statement fails to execute.
        """
        if not self._exists:
            return False
        if not await self.fireEvent("deleting"):
            return False

        deleted = await self._performForceDelete()
        await self.fireEvent("deleted")
        return deleted

    async def _performSoftDelete(self, timestamp: datetime) -> bool:
        """
        Stamp the soft delete column of the persisted row.

        Parameters
        ----------
        timestamp : datetime
            Value written into the soft delete column.

        Returns
        -------
        bool
            ``True`` when the row was stamped.

        Raises
        ------
        QueryException
            If the statement fails to execute.
        """
        self._attributes[self.__meta__.deleted_column] = timestamp
        return await self._performUpdate()
