from urllib.parse import quote, urlunsplit
from orionis.environment import Env
from orionis.foundation.config.validation import validate_integer, validate_string
from orionis.support.types.sentinel import MISSING

def http_origins(override_key: str) -> tuple[str, ...]:
    """Reuse explicit CORS origins without granting wildcard protocol access.

    Parameters
    ----------
    override_key : str
        Protocol-specific allowlist taking precedence over CORS defaults.

    Returns
    -------
    tuple[str, ...]
        Shared explicit origins suitable for protocol-specific validation.

    Raises
    ------
    TypeError
        If the shared allowlist is not a list or tuple of strings.
    """
    origins = Env.get(override_key, MISSING)
    shared = origins is MISSING
    if shared:
        origins = Env.get("CORS_ALLOW_ORIGINS", ())
    if not isinstance(origins, (list, tuple)) or any(
        not isinstance(origin, str) for origin in origins
    ):
        key = "CORS_ALLOW_ORIGINS" if shared else override_key
        message = f"{key} must be a list or tuple of strings"
        raise TypeError(message)
    return tuple(origin for origin in origins if not shared or "*" not in origin)

def redis_url(override_key: str) -> str:
    """Build a Redis URL from a service override or shared connection variables.

    Parameters
    ----------
    override_key : str
        Service-specific variable taking precedence over shared Redis settings.

    Returns
    -------
    str
        Redis URL with escaped credentials and bracketed IPv6 addresses.

    Raises
    ------
    TypeError
        If shared connection settings have invalid types.
    ValueError
        If a shared host, port or database index is invalid.
    """
    override = Env.get(override_key)
    if override is not None:
        validate_string(override, override_key)
        return override
    host = Env.get("REDIS_HOST", "127.0.0.1")
    port = Env.get("REDIS_PORT", 6379)
    database = Env.get("REDIS_DB", 0)
    credential = Env.get("REDIS_PASSWORD")
    validate_string(host, "redis host")
    validate_integer(port, "redis port", minimum=1, maximum=65535)
    validate_integer(database, "redis db")
    address = f"[{host}]" if ":" in host and not host.startswith("[") else host
    if credential is not None:
        validate_string(credential, "redis password", allow_empty=True)
        address = f":{quote(credential, safe='')}@{address}"
    return urlunsplit(("redis", f"{address}:{port}", f"/{database}", "", ""))
