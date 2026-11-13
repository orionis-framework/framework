"""Enumerate certificate verification modes supported by the AWS connector."""

from enum import StrEnum


class RedshiftSSLMode(StrEnum):
    """Enumerate certificate verification modes supported by the AWS connector."""

    VERIFY_CA = "verify-ca"
    """Verify ca identifier: ``verify-ca``."""
    VERIFY_FULL = "verify-full"
    """Verify full identifier: ``verify-full``."""
