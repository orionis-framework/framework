from __future__ import annotations
from typing import TYPE_CHECKING, Self
from orionis.database.exceptions import QueryException
from orionis.orm.query.expressions import SelectPlan

if TYPE_CHECKING:
    import asyncio
    from orionis.database.contracts.connection import IConnection
    from orionis.orm.schema.table import TableDefinition

class _DatabaseStorage:
    """Share concurrent schema bootstrap for queue and failed-job storage."""

    __slots__ = ("_ready",)
    _connection: IConnection
    _definition: TableDefinition
    _ready: bool
    _ready_lock: asyncio.Lock

    async def _ensureSchema(self: Self) -> None:
        """
        Create the queue table on first use.

        Returns
        -------
        None
            Ensure the queue storage exists.
        """
        if self._ready:
            return
        async with self._ready_lock:
            if not self._ready:
                try:
                    await self._connection.createTable(self._definition)
                except QueryException:
                    if self._connection.inTransaction():
                        raise
                    # Verify another worker created the complete table concurrently.
                    await self._connection.select(
                        SelectPlan(
                            table=self._definition,
                            columns=self._definition.columnNames(),
                            limit_value=0,
                        ),
                    )
                self._ready = not self._connection.inTransaction()
