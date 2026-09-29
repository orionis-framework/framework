from enum import Enum

class OracleEncoding(Enum):
    """
    Enumerate Oracle database character encodings.

    python-oracledb 26 uses UTF-8 for character data and no longer accepts
    connection-level ``encoding`` or ``nencoding`` overrides.

    Returns
    -------
    OracleEncoding
        An enumeration member representing an Oracle encoding.
    """

    AL32UTF8 = "AL32UTF8"  # python-oracledb's UTF-8 character encoding.
