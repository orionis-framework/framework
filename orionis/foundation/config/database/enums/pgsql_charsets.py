from enum import Enum

class PGSQLCharset(Enum):
    """
    Enumerate PostgreSQL encodings supported for database storage.

    PostgreSQL converts between the database encoding and the UTF-8 client
    protocol used by ``asyncpg``. This enum contains server-side encodings
    with built-in UTF-8 conversion, excluding client-only encodings,
    ``MULE_INTERNAL``, and ``SQL_ASCII``.

    Attributes
    ----------
    EUC_CN : str
        Extended Unix Code for Simplified Chinese.
    EUC_JP : str
        Extended Unix Code for Japanese.
    EUC_JIS_2004 : str
        Japanese EUC encoding for JIS X 0213.
    EUC_KR : str
        Extended Unix Code for Korean.
    EUC_TW : str
        Extended Unix Code for Traditional Chinese.
    ISO_8859_5 : str
        ISO 8859-5 Cyrillic encoding.
    ISO_8859_6 : str
        ISO 8859-6 Arabic encoding.
    ISO_8859_7 : str
        ISO 8859-7 Greek encoding.
    ISO_8859_8 : str
        ISO 8859-8 Hebrew encoding.
    KOI8R : str
        KOI8-R Russian encoding.
    KOI8U : str
        KOI8-U Ukrainian encoding.
    LATIN1 : str
        ISO 8859-1 Western European encoding.
    LATIN2 : str
        ISO 8859-2 Central European encoding.
    LATIN3 : str
        ISO 8859-3 South European encoding.
    LATIN4 : str
        ISO 8859-4 North European encoding.
    LATIN5 : str
        ISO 8859-9 Turkish encoding.
    LATIN6 : str
        ISO 8859-10 Nordic encoding.
    LATIN7 : str
        ISO 8859-13 Baltic Rim encoding.
    LATIN8 : str
        ISO 8859-14 Celtic encoding.
    LATIN9 : str
        ISO 8859-15 Western European encoding with Euro.
    LATIN10 : str
        ISO 8859-16 South-Eastern European encoding.
    UTF8 : str
        Unicode UTF-8 encoding.
    WIN866 : str
        Windows code page 866 (Cyrillic).
    WIN874 : str
        Windows code page 874 (Thai).
    WIN1250 : str
        Windows code page 1250 (Central European).
    WIN1251 : str
        Windows code page 1251 (Cyrillic).
    WIN1252 : str
        Windows code page 1252 (Western European).
    WIN1253 : str
        Windows code page 1253 (Greek).
    WIN1254 : str
        Windows code page 1254 (Turkish).
    WIN1255 : str
        Windows code page 1255 (Hebrew).
    WIN1256 : str
        Windows code page 1256 (Arabic).
    WIN1257 : str
        Windows code page 1257 (Baltic).
    WIN1258 : str
        Windows code page 1258 (Vietnamese).

    Returns
    -------
    PGSQLCharset
        The enumeration member representing a PostgreSQL database encoding.
    """

    EUC_CN = "EUC_CN"
    EUC_JP = "EUC_JP"
    EUC_JIS_2004 = "EUC_JIS_2004"
    EUC_KR = "EUC_KR"
    EUC_TW = "EUC_TW"
    ISO_8859_5 = "ISO_8859_5"
    ISO_8859_6 = "ISO_8859_6"
    ISO_8859_7 = "ISO_8859_7"
    ISO_8859_8 = "ISO_8859_8"
    KOI8R = "KOI8R"
    KOI8U = "KOI8U"
    LATIN1 = "LATIN1"
    LATIN2 = "LATIN2"
    LATIN3 = "LATIN3"
    LATIN4 = "LATIN4"
    LATIN5 = "LATIN5"
    LATIN6 = "LATIN6"
    LATIN7 = "LATIN7"
    LATIN8 = "LATIN8"
    LATIN9 = "LATIN9"
    LATIN10 = "LATIN10"
    UTF8 = "UTF8"
    WIN866 = "WIN866"
    WIN874 = "WIN874"
    WIN1250 = "WIN1250"
    WIN1251 = "WIN1251"
    WIN1252 = "WIN1252"
    WIN1253 = "WIN1253"
    WIN1254 = "WIN1254"
    WIN1255 = "WIN1255"
    WIN1256 = "WIN1256"
    WIN1257 = "WIN1257"
    WIN1258 = "WIN1258"
