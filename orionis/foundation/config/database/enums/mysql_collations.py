from enum import Enum

class MySQLCollation(Enum):
    """
    Enumerate common MySQL collations.

    This enum provides connection-compatible collation names for the UTF-8,
    Latin1, ASCII, and GB18030 character sets. The selected collation must
    match the configured connection character set.

    Attributes
    ----------
    UTF8_GENERAL_CI : str
        UTF-8, case-insensitive, general collation.
    UTF8_UNICODE_CI : str
        UTF-8, case-insensitive, Unicode collation.
    UTF8_BIN : str
        UTF-8, binary collation.
    UTF8MB4_GENERAL_CI : str
        UTF-8MB4, case-insensitive, general collation.
    UTF8MB4_UNICODE_CI : str
        UTF-8MB4, case-insensitive, Unicode collation.
    UTF8MB4_BIN : str
        UTF-8MB4, binary collation.
    LATIN1_SWEDISH_CI : str
        Latin1, case-insensitive, Swedish collation.
    LATIN1_GENERAL_CI : str
        Latin1, case-insensitive, general collation.
    LATIN1_BIN : str
        Latin1, binary collation.
    ASCII_GENERAL_CI : str
        ASCII, case-insensitive, general collation.
    ASCII_BIN : str
        ASCII, binary collation.
    GB18030_CHINESE_CI : str
        GB18030 default Chinese collation.
    GB18030_BIN : str
        GB18030 binary collation.
    GB18030_UNICODE_520_CI : str
        GB18030 Unicode 5.2 collation.
    """

    UTF8_GENERAL_CI = "utf8_general_ci"
    UTF8_UNICODE_CI = "utf8_unicode_ci"
    UTF8_BIN = "utf8_bin"
    UTF8MB4_GENERAL_CI = "utf8mb4_general_ci"
    UTF8MB4_UNICODE_CI = "utf8mb4_unicode_ci"
    UTF8MB4_BIN = "utf8mb4_bin"
    LATIN1_SWEDISH_CI = "latin1_swedish_ci"
    LATIN1_GENERAL_CI = "latin1_general_ci"
    LATIN1_BIN = "latin1_bin"
    ASCII_GENERAL_CI = "ascii_general_ci"
    ASCII_BIN = "ascii_bin"
    GB18030_CHINESE_CI = "gb18030_chinese_ci"
    GB18030_BIN = "gb18030_bin"
    GB18030_UNICODE_520_CI = "gb18030_unicode_520_ci"
