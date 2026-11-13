"""Enumerate authenticated AES modes and retained legacy identifiers."""

from enum import Enum


class Cipher(Enum):
    """
    Enumerate authenticated AES modes and retained legacy identifiers.

    Retain CBC identifiers for compatibility with key-generation utilities.
    Application encryption accepts only the authenticated GCM modes.

    Attributes
    ----------
    AES_128_CBC : str
        Legacy AES-128-CBC identifier; rejected by application encryption.
    AES_256_CBC : str
        Legacy AES-256-CBC identifier; rejected by application encryption.
    AES_128_GCM : str
        AES with a 128-bit key in Galois/Counter Mode (GCM).
    AES_256_GCM : str
        AES with a 256-bit key in Galois/Counter Mode (GCM).

    """

    AES_128_CBC = "AES-128-CBC"
    AES_256_CBC = "AES-256-CBC"
    AES_128_GCM = "AES-128-GCM"
    AES_256_GCM = "AES-256-GCM"


_AUTHENTICATED_CIPHERS = frozenset({Cipher.AES_128_GCM.value, Cipher.AES_256_GCM.value})
"""Canonical cipher names accepted for authenticated application encryption."""
