from enum import Enum

class Cipher(Enum):
    """
    Enumerate supported AES cipher modes.

    This enum defines various Advanced Encryption Standard (AES) cipher modes and
    key sizes commonly used for encryption and decryption operations.

    Attributes
    ----------
    AES_128_CBC : str
        AES with a 128-bit key in Cipher Block Chaining (CBC) mode.
    AES_256_CBC : str
        AES with a 256-bit key in Cipher Block Chaining (CBC) mode.
    AES_128_GCM : str
        AES with a 128-bit key in Galois/Counter Mode (GCM).
    AES_256_GCM : str
        AES with a 256-bit key in Galois/Counter Mode (GCM).

    Returns
    -------
    None
        This class is an enumeration and does not return a value.
    """

    AES_128_CBC = "AES-128-CBC"
    AES_256_CBC = "AES-256-CBC"
    AES_128_GCM = "AES-128-GCM"
    AES_256_GCM = "AES-256-GCM"
