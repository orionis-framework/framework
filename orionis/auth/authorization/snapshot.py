from typing import TYPE_CHECKING
from orionis.auth.contracts.snapshot import IAuthorizationSnapshot

if TYPE_CHECKING:
    from collections.abc import Iterable

class AuthorizationSnapshot(IAuthorizationSnapshot):
    """
    Hold the immutable authorization picture of a single request.

    Effective authorization is the intersection of what the identity owns
    and what the presented credential is allowed to use::

        effective = identity permissions ∩ credential abilities

    A credential without abilities (``None``) never narrows the identity,
    and abilities alone can never grant a permission the identity lacks.

    Concurrency
    -----------
    Instances are fully immutable once built, so they can be shared by
    every coroutine handling the same request without synchronisation.
    """

    __slots__ = ("__abilities", "__permissions", "__roles")

    def __init__(
        self,
        permissions: Iterable[str],
        roles: Iterable[str],
        abilities: Iterable[str] | None = None,
    ) -> None:
        """
        Build a snapshot from the resolved authorization sources.

        Parameters
        ----------
        permissions : Iterable[str]
            Permission names owned by the identity, direct ones and the
            ones inherited from its roles.
        roles : Iterable[str]
            Role names assigned to the identity.
        abilities : Iterable[str] | None, optional
            Abilities restricting the presented credential.

        Returns
        -------
        None
            The snapshot is initialised with immutable collections.
        """
        self.__permissions: frozenset[str] = frozenset(permissions)
        self.__roles: frozenset[str] = frozenset(roles)
        self.__abilities: frozenset[str] | None = (
            None if abilities is None else frozenset(abilities)
        )

    @property
    def permissions(self) -> frozenset[str]:
        """
        Return the permissions owned by the identity.

        Returns
        -------
        frozenset[str]
            Direct permissions plus the ones inherited from roles.
        """
        return self.__permissions

    @property
    def roles(self) -> frozenset[str]:
        """
        Return the roles assigned to the identity.

        Returns
        -------
        frozenset[str]
            Role names, without hierarchy or inheritance.
        """
        return self.__roles

    @property
    def abilities(self) -> frozenset[str] | None:
        """
        Return the abilities restricting the presented credential.

        Returns
        -------
        frozenset[str] | None
            Abilities of the credential, or ``None`` when unrestricted.
        """
        return self.__abilities

    def can(self, permission: str) -> bool:
        """
        Report whether the effective authorization grants a permission.

        Parameters
        ----------
        permission : str
            Permission name to evaluate.

        Returns
        -------
        bool
            True when the identity owns the permission and the presented
            credential is allowed to use it.
        """
        # A credential can only narrow what the identity already owns.
        if permission not in self.__permissions:
            return False
        abilities = self.__abilities
        return abilities is None or permission in abilities

    def hasRole(self, role: str) -> bool:
        """
        Report whether the identity owns a role.

        Parameters
        ----------
        role : str
            Role name to evaluate.

        Returns
        -------
        bool
            True when the role is assigned to the identity.
        """
        return role in self.__roles

    def __repr__(self) -> str:
        """
        Return a debugging representation of the snapshot.

        Returns
        -------
        str
            Compact description with the collection sizes only.
        """
        abilities = (
            "unrestricted"
            if self.__abilities is None
            else str(len(self.__abilities))
        )
        return (
            f"AuthorizationSnapshot(permissions={len(self.__permissions)}, "
            f"roles={len(self.__roles)}, abilities={abilities})"
        )

# Shared snapshot handed to guest requests: no permissions, no roles.
EMPTY_SNAPSHOT: AuthorizationSnapshot = AuthorizationSnapshot(
    permissions=(),
    roles=(),
)
