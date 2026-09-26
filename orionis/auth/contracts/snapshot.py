from abc import ABC, abstractmethod

class IAuthorizationSnapshot(ABC):
    """
    Define the immutable authorization picture of a single request.

    The snapshot is resolved at most once per request and answers every
    later ``can()`` call without touching the database again.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def permissions(self) -> frozenset[str]:
        """
        Return the permissions granted to the identity.

        Returns
        -------
        frozenset[str]
            Union of the direct permissions and the ones inherited from
            the roles of the identity.
        """

    @property
    @abstractmethod
    def roles(self) -> frozenset[str]:
        """
        Return the role names assigned to the identity.

        Returns
        -------
        frozenset[str]
            Role names, without any hierarchy or inheritance.
        """

    @property
    @abstractmethod
    def abilities(self) -> frozenset[str] | None:
        """
        Return the abilities restricting the current credential.

        Returns
        -------
        frozenset[str] | None
            Abilities carried by the access token, or ``None`` when the
            credential does not narrow the authorization of the identity.
        """

    @abstractmethod
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
            True when the identity owns the permission and the current
            credential is allowed to use it.
        """

    @abstractmethod
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
