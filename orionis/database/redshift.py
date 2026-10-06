try:
    from sqlalchemy_redshift.dialect import (
        RedshiftDialect_redshift_connector as RedshiftConnectorDialect,
    )
except ImportError:
    RedshiftConnectorDialect = None

class RedshiftDialect(RedshiftConnectorDialect):
    """
    Retain the official connector dialect without PostgreSQL-only capabilities.

    Amazon Redshift does not implement DML RETURNING or PostgreSQL sequences.
    Server-generated IDENTITY values are not returned by the connector; callers
    needing a model key immediately must provide a client-generated primary key.
    This module is imported only when a Redshift engine is first constructed.
    """

    __slots__ = ()

    insert_returning = False
    update_returning = False
    delete_returning = False
    preexecute_autoincrement_sequences = False
    postfetch_lastrowid = False
    supports_statement_cache = False
