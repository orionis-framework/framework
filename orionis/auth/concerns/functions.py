from uuid import UUID
from orionis.auth.exceptions import AuthException

# Attribute used when the object does not expose ORM metadata.
_FALLBACK_PRIMARY_KEY: str = "id"
_MAX_KEY_LENGTH: int = 255

def authorizable_key(identity: object) -> tuple[str, str]:
    """Normalize a persisted identity's polymorphic authorization key.

    Parameters
    ----------
    identity : object
        Identity exposing getAuthorizableType and getAuthorizableId.

    Returns
    -------
    tuple[str, str]
        Stable owner type and canonical textual identifier.

    Raises
    ------
    AuthException
        If the identity has no valid persisted scalar key.
    """
    describe = getattr(identity, "getAuthorizableType", None)
    identify = getattr(identity, "getAuthorizableId", None)
    error_msg = "Authorization requires a persisted identity with a scalar key."
    if not callable(describe) or not callable(identify):
        raise AuthException(error_msg)
    kind = describe()
    identifier = identify()
    if (
        not isinstance(kind, str)
        or not kind
        or len(kind) > _MAX_KEY_LENGTH
        or not isinstance(identifier, (int, str, UUID))
        or isinstance(identifier, bool)
    ):
        raise AuthException(error_msg)
    key = str(identifier)
    if not key or len(key) > _MAX_KEY_LENGTH:
        raise AuthException(error_msg)
    return kind, key

def model_primary_key(instance: object) -> str:
    """Return the primary key attribute of a model instance.

    The lookup is duck typed on purpose: the authentication module must
    never import the ORM model class, so it only reads the metadata the
    ORM metaclass already publishes.

    Parameters
    ----------
    instance : object
        Object expected to expose ``__meta__.primary_key``.

    Returns
    -------
    str
        Name of the primary key attribute, falling back to ``"id"`` for
        objects without ORM metadata.
    """
    meta = getattr(type(instance), "__meta__", None)
    primary_key = getattr(meta, "primary_key", None)
    if isinstance(primary_key, str) and primary_key:
        return primary_key
    return _FALLBACK_PRIMARY_KEY
