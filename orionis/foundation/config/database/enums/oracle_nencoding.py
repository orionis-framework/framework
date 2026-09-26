from enum import Enum

class OracleNencoding(Enum):
    """
    Represent Oracle national character sets supported by Oracle Database.

    Oracle Database permits ``AL16UTF16`` or ``UTF8`` as the national
    character set. python-oracledb does not expose an ``nencoding`` override.

    Attributes
    ----------
    AL16UTF16 : str
        UTF-16 big-endian national character set.
    UTF8 : str
        CESU-8 national character set.

    Returns
    -------
    OracleNencoding
        An enumeration member representing the Oracle encoding type.
    """

    AL16UTF16 = "AL16UTF16"
    UTF8 = "UTF8"
