from __future__ import annotations
from importlib import import_module
from importlib.util import find_spec
from typing import TYPE_CHECKING
from sqlalchemy import text
from sqlalchemy.engine import reflection

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

if find_spec("sqlalchemy_redshift") is not None:
    RedshiftConnectorDialect = import_module(
        "sqlalchemy_redshift.dialect",
    ).RedshiftDialect_redshift_connector

    class RedshiftDialect(RedshiftConnectorDialect):
        """
        Retain the connector dialect without PostgreSQL-only capabilities.

        Amazon Redshift does not implement DML RETURNING or PostgreSQL sequences.
        Server-generated IDENTITY values are not returned by the connector;
        callers needing a model key immediately must provide a client-generated
        primary key. This module is imported only when a Redshift engine is first
        constructed.
        """

        __slots__ = ()

        insert_returning = False
        update_returning = False
        delete_returning = False
        preexecute_autoincrement_sequences = False
        postfetch_lastrowid = False
        supports_statement_cache = False
        # The official connector's executemany loops over individual network
        # calls. Core can page supported multi-value INSERTs without RETURNING.
        use_insertmanyvalues_wo_returning = True

        @reflection.cache
        def has_table(
            self, connection: Connection, table_name: str,
            schema: str | None = None, **_kw: object,
        ) -> bool:
            """
            Check catalog membership with bound schema and table names.

            The upstream reflection helper interpolates these identifiers into
            SQL string literals. CREATE TABLE's checkfirst path must keep them
            as values even when quoted identifiers contain apostrophes.

            Parameters
            ----------
            connection : Connection
                Core connection used by SQLAlchemy's reflection dispatch.
            table_name : str
                Exact table identifier to find.
            schema : str | None, optional
                Explicit namespace, or the current schema when omitted.
            **_kw : object
                Reflection options accepted by the SQLAlchemy interface.

            Returns
            -------
            bool
                Whether the visible catalog contains this exact table.
            """
            self._ensure_has_table_connection(connection)
            return bool(connection.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM svv_tables
                    WHERE table_catalog = current_database()
                      AND table_schema = COALESCE(:schema, current_schema())
                      AND table_name = :table_name
                )
            """), {"schema": schema, "table_name": table_name}).scalar())
else:
    RedshiftConnectorDialect = None
    RedshiftDialect = None
