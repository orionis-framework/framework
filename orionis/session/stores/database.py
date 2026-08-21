import asyncio
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
import msgspec
import msgspec.json as _msgjson
from orionis.database.exceptions import QueryException
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, String, Text
from orionis.session.contracts.store import ISessionStore
from orionis.session.entities.record import SessionRecord

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection

# Default table name used when the session config does not override it.
_DEFAULT_TABLE = "sessions"

# Codecs built once: msgspec resolves its internal state at construction time
# instead of on every encode/decode call.
_ENCODER = _msgjson.Encoder()
_DECODER = _msgjson.Decoder()

def _build_sessions_table(table: str) -> TableDefinition:
    """
    Build the table definition for the sessions table.

    Parameters
    ----------
    table : str
        Logical table name for session records.

    Returns
    -------
    TableDefinition
        Definition with ``id`` (primary key), ``payload`` (JSON data)
        and ``expires_at`` (epoch seconds) columns.
    """
    id_column = String(255).primary()
    id_column.name = "id"

    payload_column = Text()
    payload_column.name = "payload"

    expires_column = BigInteger()
    expires_column.name = "expires_at"

    return TableDefinition(
        name=table,
        columns={
            "id": id_column,
            "payload": payload_column,
            "expires_at": expires_column,
        },
        primary_key="id",
    )

class DatabaseSessionStore(ISessionStore):
    """
    Session store that persists each session as a row in a database table.

    Mirrors :class:`orionis.cache.stores.database.DatabaseCacheBackend`:
    records live in a dedicated table (``id`` / ``payload`` /
    ``expires_at``) resolved through the ``session.connection``
    configuration, using upsert-by-retry semantics so no dialect-specific
    ``ON CONFLICT`` syntax is required.

    Unlike the cache backend, a plain SQL table has no native TTL, so
    expired rows are evicted lazily on :meth:`read` and can be swept in
    bulk via :meth:`gc`.

    Parameters
    ----------
    connection : IConnection
        Database connection used to persist session records.
    table : str, optional
        Table name used to store session records.  Defaults to
        ``'sessions'``.
    """

    __slots__ = (
        "_connection",
        "_ready",
        "_ready_lock",
        "_sql_delete",
        "_sql_gc",
        "_sql_insert",
        "_sql_select",
        "_sql_update",
        "_table",
    )

    def __init__(self, connection: IConnection, table: str = _DEFAULT_TABLE) -> None:
        """
        Bind the store to *connection* and the target *table*.

        Parameters
        ----------
        connection : IConnection
            Database connection used to persist session records.
        table : str, optional
            Table name used to store session records.

        Returns
        -------
        None
        """
        self._connection = connection
        self._table = table
        self._ready = False
        self._ready_lock = asyncio.Lock()

        # Statements only depend on the table name: build them once instead of
        # formatting a new SQL string on every session operation.
        self._sql_select: str = (
            f"SELECT payload, expires_at FROM {table} WHERE id = :id"  # noqa: S608
        )
        self._sql_update: str = (
            f"UPDATE {table} SET payload = :p, expires_at = :e WHERE id = :id"  # noqa: S608
        )
        self._sql_insert: str = (
            f"INSERT INTO {table} (id, payload, expires_at) "  # noqa: S608
            "VALUES (:id, :p, :e)"
        )
        self._sql_delete: str = f"DELETE FROM {table} WHERE id = :id"  # noqa: S608
        self._sql_gc: str = f"DELETE FROM {table} WHERE expires_at <= :now"  # noqa: S608

    # ── Schema bootstrap ─────────────────────────────────────────────────────

    async def _ensureSchema(self) -> None:
        """
        Create the sessions table on first use, if missing.

        Returns
        -------
        None
        """
        if self._ready:
            return
        async with self._ready_lock:
            if self._ready:
                return
            await self._connection.createTable(_build_sessions_table(self._table))
            self._ready = True

    # ── ISessionStore ────────────────────────────────────────────────────────

    async def read(self, session_id: str) -> SessionRecord | None:
        """
        Return the stored record for *session_id*, or ``None``.

        Parameters
        ----------
        session_id : str
            Unique session identifier to look up.

        Returns
        -------
        SessionRecord | None
            The stored record, or ``None`` when absent, expired or
            corrupted.
        """
        await self._ensureSchema()
        rows = await self._connection.select(
            self._sql_select,
            {"id": session_id},
        )
        if not rows:
            return None

        row = rows[0]
        expiration = row.get("expires_at")
        if expiration is None or expiration <= time.time():
            await self.delete(session_id)
            return None

        data = self.__decode(row.get("payload"))
        if data is None:
            return None

        return SessionRecord(
            id=session_id,
            data=data,
            expires_at=datetime.fromtimestamp(expiration, tz=UTC),
        )

    async def write(self, record: SessionRecord) -> None:
        """
        Insert or replace the record keyed by its identifier.

        A record that has already expired is deleted instead of written.

        Parameters
        ----------
        record : SessionRecord
            The record to persist.

        Returns
        -------
        None
        """
        expiration = int(record.expires_at.timestamp())

        if expiration <= time.time():
            await self.delete(record.id)
            return

        await self._ensureSchema()
        payload = self.__encode(record.data)

        updated = await self._connection.execute(
            self._sql_update,
            {"p": payload, "e": expiration, "id": record.id},
        )
        if not updated:
            await self.__insertOrRetryUpdate(record.id, payload, expiration)

    async def __insertOrRetryUpdate(
        self,
        session_id: str,
        payload: str,
        expiration: int,
    ) -> None:
        """
        Insert a new session row, falling back to an update on conflict.

        Parameters
        ----------
        session_id : str
            Unique session identifier.
        payload : str
            JSON-encoded session data already serialized by :meth:`write`.
        expiration : int
            Absolute expiration timestamp (whole epoch seconds).

        Returns
        -------
        None
        """
        try:
            await self._connection.execute(
                self._sql_insert,
                {"id": session_id, "p": payload, "e": expiration},
            )
        except QueryException:
            # Another writer inserted the row first; retry as an update.
            await self._connection.execute(
                self._sql_update,
                {"p": payload, "e": expiration, "id": session_id},
            )

    async def delete(self, session_id: str) -> None:
        """
        Remove the record for *session_id* (no-op when absent).

        Parameters
        ----------
        session_id : str
            Unique session identifier to remove.

        Returns
        -------
        None
        """
        await self._ensureSchema()
        await self._connection.execute(
            self._sql_delete,
            {"id": session_id},
        )

    async def gc(self) -> None:
        """
        Remove all rows whose ``expires_at`` is in the past.

        Unlike a native TTL-backed cache, a SQL table never evicts stale
        rows on its own, so this performs a single bulk ``DELETE``.

        Returns
        -------
        None
        """
        await self._ensureSchema()
        await self._connection.execute(
            self._sql_gc,
            {"now": int(time.time())},
        )

    # ── Serialization helpers ────────────────────────────────────────────────

    def __encode(self, data: dict[str, Any]) -> str:
        """
        Serialize *data* to a JSON string suitable for storage.

        Parameters
        ----------
        data : dict[str, Any]
            Session data payload to encode.

        Returns
        -------
        str
            UTF-8 decoded JSON payload.
        """
        return _ENCODER.encode(data).decode()

    def __decode(self, raw: str | bytes | None) -> dict[str, Any] | None:
        """
        Deserialize a stored JSON payload back into a Python dict.

        Parameters
        ----------
        raw : str | bytes | None
            Raw payload read from the ``payload`` column.

        Returns
        -------
        dict[str, Any] | None
            Decoded data, or ``None`` when *raw* is missing or invalid.
        """
        if raw is None:
            return None
        data = raw.encode() if isinstance(raw, str) else raw
        try:
            return _DECODER.decode(data)
        except msgspec.DecodeError:
            return None
