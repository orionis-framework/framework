from enum import Enum

class PGSQLSSLMode(Enum):
    """
    Define SSL modes for PostgreSQL connections.

    This enumeration corresponds to the 'sslmode' parameter in libpq. The values
    determine the level of SSL enforcement and validation for PostgreSQL
    connections.

    Attributes
    ----------
    DISABLE : str
        No SSL (not secure).
    ALLOW : str
        Attempt SSL, silently fall back if unavailable.
    PREFER : str
        Use SSL if available (common default).
    REQUIRE : str
        Require SSL (no certificate validation).
    VERIFY_CA : str
        Validate the server certificate against the CA.
    VERIFY_FULL : str
        Validate both the certificate and the host name (most secure).

    Returns
    -------
    PGSQLSSLMode
        An enumeration member representing the SSL mode.
    """

    DISABLE = "disable"          # No SSL (not secure)
    ALLOW = "allow"              # Attempts SSL, silently falls back if unavailable
    PREFER = "prefer"            # Uses SSL if available (common default)
    REQUIRE = "require"          # Requires SSL (no certificate validation)
    VERIFY_CA = "verify-ca"      # Validates the server certificate against the CA
    VERIFY_FULL = "verify-full"  # Validates both the certificate and the host name
