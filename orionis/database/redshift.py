from importlib import import_module
from importlib.util import find_spec

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
else:
    RedshiftConnectorDialect = None
    RedshiftDialect = None
