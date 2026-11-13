# ruff: noqa: PLC0415, TC001, TC003
# Load failure observation only when schema creation needs recovery.
# Keep inherited storage annotations resolvable at runtime.
"""Share concurrent schema bootstrap for queue and failed-job storage."""

from __future__ import annotations
import asyncio
from typing import Self
from orionis.database.contracts.connection import IConnection
from orionis.database.exceptions import QueryException
from orionis.orm.query.expressions import SelectPlan
from orionis.orm.schema.table import TableDefinition


class _DatabaseStorage:
    """Share concurrent schema bootstrap for queue and failed-job storage."""

    __slots__ = ("_ready",)
    """Declare the instance attribute slots reserved by this class."""
    _connection: IConnection
    """Configured connection used to store or dispatch the operation."""
    _definition: TableDefinition
    """Original declaration from which runtime metadata was compiled."""
    _ready: bool
    """Whether backend initialization has completed."""
    _ready_lock: asyncio.Lock
    """Lock coordinating one-time initialization of the backend."""

    async def _ensureSchema(self: Self) -> None:
        """
        Create the queue table on first use.

        Returns
        -------
        None
            Ensure the queue storage exists.

        Raises
        ------
        orionis.database.QueryException
            If creation fails and recovery cannot confirm a complete table.
            Preserve the creation error and observe a failed recovery read.
        """
        if self._ready:
            return
        async with self._ready_lock:
            if not self._ready:
                try:
                    await self._connection.createTable(self._definition)
                except QueryException as error:
                    if self._connection.inTransaction():
                        raise
                    from orionis.failure.runtime import capture

                    # Verify another worker created the complete table concurrently.
                    try:
                        await self._connection.select(
                            SelectPlan(
                                table=self._definition,
                                columns=self._definition.columnNames(),
                                limit_value=0,
                            ),
                        )
                    except QueryException as recovery_error:
                        await capture(
                            recovery_error,
                            flow="queue",
                            phase="recovery",
                            operation="database.schema.lookup",
                        )
                        raise error from error.__cause__
                    await capture(
                        error,
                        flow="queue",
                        phase="recovery",
                        operation="database.schema",
                        expected=True,
                    )
                self._ready = not self._connection.inTransaction()
