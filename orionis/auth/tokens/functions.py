import hashlib
import secrets

def generate_token_secret(size: int) -> str:
    """
    Generate the plain text secret of a personal access token.

    Parameters
    ----------
    size : int
        Number of random bytes backing the secret. The returned string is
        longer because it is URL-safe base64 encoded.

    Returns
    -------
    str
        Cryptographically secure random string. ``secrets`` is used on
        purpose: ``random`` is not suitable for credentials.
    """
    return secrets.token_urlsafe(size)

def hash_token_secret(secret: str) -> str:
    """
    Derive the value persisted for a personal access token.

    Only this digest reaches the database, so a leaked row never exposes
    a usable credential. SHA-256 is appropriate here because the input is
    already high entropy random data, unlike a user chosen password.

    Parameters
    ----------
    secret : str
        Plain text token presented by the client.

    Returns
    -------
    str
        Hexadecimal SHA-256 digest of the secret, 64 characters long.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()
