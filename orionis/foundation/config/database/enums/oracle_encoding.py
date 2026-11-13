"""Enumerate Oracle database character encodings."""

from enum import Enum


class OracleEncoding(Enum):
    """
    Enumerate Oracle database character encodings.

    python-oracledb 26 uses UTF-8 for character data and no longer accepts
    connection-level ``encoding`` or ``nencoding`` overrides.

    Returns
    -------
    orionis.foundation.config.database.OracleEncoding
        An enumeration member representing an Oracle encoding.
    """

    AL32UTF8 = "AL32UTF8"  # python-oracledb's UTF-8 character encoding.
    """Al32 utf8 identifier: ``AL32UTF8``."""
