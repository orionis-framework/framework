from orionis.auth.authorization.policy import Policy
from orionis.auth.authorization.registry import PolicyRegistry
from orionis.auth.authorization.snapshot import (
    EMPTY_SNAPSHOT,
    AuthorizationSnapshot,
)

# ``Authorizer``, ``DatabasePermissionRepository`` and
# ``PermissionRegistrar`` are deliberately not re-exported here: they pull
# the ORM and the container in, and this package is imported very early
# through ``orionis.support.facades``.

__all__ = [
    "EMPTY_SNAPSHOT",
    "AuthorizationSnapshot",
    "Policy",
    "PolicyRegistry",
]
