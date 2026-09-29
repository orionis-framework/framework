from enum import Enum

class SQLServerCharset(Enum):
    """
    Enumerate SQLCHAR encodings documented for SQL Server ODBC on Linux and macOS.

    Availability depends on the installed driver and platform. Narrow SQLCHAR
    data follows the process locale; SQLWCHAR data uses UTF-16LE.

    Attributes
    ----------
    UTF8, CP437, CP850, CP874, CP932, CP936, CP949, CP950, CP1250-CP1258,
    ISO_8859_1-ISO_8859_9, ISO_8859_13, ISO_8859_15 : str
        Names of the documented ODBC client encodings.
    """

    UTF8 = "UTF-8"
    CP437 = "CP437"
    CP850 = "CP850"
    CP874 = "CP874"
    CP932 = "CP932"
    CP936 = "CP936"
    CP949 = "CP949"
    CP950 = "CP950"
    CP1250 = "CP1250"
    CP1251 = "CP1251"
    CP1252 = "CP1252"
    CP1253 = "CP1253"
    CP1254 = "CP1254"
    CP1255 = "CP1255"
    CP1256 = "CP1256"
    CP1257 = "CP1257"
    CP1258 = "CP1258"
    ISO_8859_1 = "ISO-8859-1"
    ISO_8859_2 = "ISO-8859-2"
    ISO_8859_3 = "ISO-8859-3"
    ISO_8859_4 = "ISO-8859-4"
    ISO_8859_5 = "ISO-8859-5"
    ISO_8859_6 = "ISO-8859-6"
    ISO_8859_7 = "ISO-8859-7"
    ISO_8859_8 = "ISO-8859-8"
    ISO_8859_9 = "ISO-8859-9"
    ISO_8859_13 = "ISO-8859-13"
    ISO_8859_15 = "ISO-8859-15"
