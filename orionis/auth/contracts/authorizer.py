from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from orionis.auth.contracts.context import IAuthenticationContext
    from orionis.auth.contracts.policy import IPolicy

class IAuthorizer(ABC):
    """Define the component answering authorization questions.

    The authorizer never owns the current identity. It receives the
    request context on every call, which keeps it safe to register as a
    singleton.
    """

    __slots__ = ()

    @abstractmethod
    async def can(
        self,
        context: IAuthenticationContext,
        permission: str,
    ) -> bool:
        """Report whether the context grants a permission.

        Parameters
        ----------
        context : IAuthenticationContext
            Authentication context of the current request.
        permission : str
            Permission name to evaluate.

        Returns
        -------
        bool
            True when the permission is granted.
        """

    @abstractmethod
    async def canAny(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
        """Report whether the context grants at least one permission.

        Parameters
        ----------
        context : IAuthenticationContext
            Authentication context of the current request.
        permissions : Iterable[str]
            Permission names to evaluate.

        Returns
        -------
        bool
            True when at least one permission is granted.
        """

    @abstractmethod
    async def canAll(
        self,
        context: IAuthenticationContext,
        permissions: Iterable[str],
    ) -> bool:
        """Report whether the context grants every permission.

        Parameters
        ----------
        context : IAuthenticationContext
            Authentication context of the current request.
        permissions : Iterable[str]
            Permission names to evaluate.

        Returns
        -------
        bool
            True when every permission is granted.
        """

    @abstractmethod
    async def hasRole(
        self,
        context: IAuthenticationContext,
        role: str,
    ) -> bool:
        """Report whether the context owns a role.

        Parameters
        ----------
        context : IAuthenticationContext
            Authentication context of the current request.
        role : str
            Role name to evaluate.

        Returns
        -------
        bool
            True when the role is assigned to the identity.
        """

    @abstractmethod
    async def allows(
        self,
        context: IAuthenticationContext,
        ability: str,
        resource: object,
    ) -> bool:
        """Evaluate a policy ability against a concrete resource.

        Parameters
        ----------
        context : IAuthenticationContext
            Authentication context of the current request.
        ability : str
            Ability declared by the policy of the resource.
        resource : object
            Resource instance, or the resource class when the ability does
            not need an instance.

        Returns
        -------
        bool
            True when the policy allows the operation.

        Raises
        ------
        PolicyNotFoundException
            When no policy is registered for the resource type.
        """

    @abstractmethod
    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
        """Bind a policy class to a resource type.

        Parameters
        ----------
        resource : type
            Resource class protected by the policy.
        policy : type[IPolicy]
            Policy class implementing the abilities.

        Returns
        -------
        None
            The registry is updated as a side effect.
        """
