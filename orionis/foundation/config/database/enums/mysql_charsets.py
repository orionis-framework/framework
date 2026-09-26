from enum import Enum

class MySQLCharset(Enum):
    """
    Enumerate MySQL character sets usable by the configured connection drivers.

    The list follows MySQL 8.4 client-compatible character sets that map to
    Python codecs used by PyMySQL and aiomysql. It excludes server character
    sets without a matching Python codec and ``ucs2``, ``utf16``, ``utf16le``,
    and ``utf32``, which MySQL forbids as client connection character sets.

    Attributes
    ----------
    ASCII : str
        US ASCII.
    BIG5 : str
        Big5 Traditional Chinese.
    CP1250 : str
        Windows Central European.
    CP1251 : str
        Windows Cyrillic.
    CP1256 : str
        Windows Arabic.
    CP1257 : str
        Windows Baltic.
    CP850 : str
        DOS West European.
    CP852 : str
        DOS Central European.
    CP866 : str
        DOS Russian.
    CP932 : str
        SJIS for Windows Japanese.
    EUCKR : str
        EUC-KR Korean.
    GB18030 : str
        GB18030 Chinese national standard.
    GB2312 : str
        GB2312 Simplified Chinese.
    GBK : str
        GBK Simplified Chinese.
    GREEK : str
        ISO 8859-7 Greek.
    HEBREW : str
        ISO 8859-8 Hebrew.
    KOI8R : str
        KOI8-R Relcom Russian.
    KOI8U : str
        KOI8-U Ukrainian.
    LATIN1 : str
        cp1252 West European.
    LATIN2 : str
        ISO 8859-2 Central European.
    LATIN5 : str
        ISO 8859-9 Turkish.
    LATIN7 : str
        ISO 8859-13 Baltic.
    MACROMAN : str
        Mac West European.
    SJIS : str
        Shift-JIS Japanese.
    TIS620 : str
        TIS620 Thai.
    UJIS : str
        EUC-JP Japanese.
    UTF8 : str
        Deprecated MySQL alias for UTF8MB3; use UTF8MB4 for new connections.
    UTF8MB3 : str
        Deprecated UTF-8 Unicode limited to three bytes per character.
    UTF8MB4 : str
        UTF-8 Unicode with up to four bytes per character.

    Returns
    -------
    MySQLCharset
        The enumeration member representing a MySQL connection character set.
    """

    ASCII = "ascii"
    BIG5 = "big5"
    CP1250 = "cp1250"
    CP1251 = "cp1251"
    CP1256 = "cp1256"
    CP1257 = "cp1257"
    CP850 = "cp850"
    CP852 = "cp852"
    CP866 = "cp866"
    CP932 = "cp932"
    EUCKR = "euckr"
    GB18030 = "gb18030"
    GB2312 = "gb2312"
    GBK = "gbk"
    GREEK = "greek"
    HEBREW = "hebrew"
    KOI8R = "koi8r"
    KOI8U = "koi8u"
    LATIN1 = "latin1"
    LATIN2 = "latin2"
    LATIN5 = "latin5"
    LATIN7 = "latin7"
    MACROMAN = "macroman"
    SJIS = "sjis"
    TIS620 = "tis620"
    UJIS = "ujis"
    UTF8 = "utf8"
    UTF8MB3 = "utf8mb3"
    UTF8MB4 = "utf8mb4"
