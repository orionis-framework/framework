import inspect
from typing import TYPE_CHECKING
from orionis.auth.authorization.registry import PolicyRegistry
from orionis.auth.contracts.authorizer import IAuthorizer
from orionis.auth.exceptions import PolicyNotFoundException
from orionis.foundation.contracts.application import IApplication

if TYPE_CHECKING:
    from collections.abc import Iterable
    from orionis.auth.contracts.context import IAuthenticationContext
    from orionis.auth.contracts.policy import IPolicy

class Authorizer(IAuthorizer):
    """Answer authorization questions for a given request context.

    The authorizer never stores the current identity: every method takes
    the request context as its first argument. That keeps the service
    stateless and therefore safe as a container singleton shared by every
    concurrent request.

    Concurrency
    -----------
    Only policy classes are cached. Each evaluation builds a fresh policy
    in the caller's container scope, so injected request dependencies and
    mutable policy state are never retained by this singleton.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("__app", "__registry")

    def __init__(self, app: IApplication) -> None:
        """Initialise the authorizer with the application container.

        Parameters
        ----------
        app : IApplication
            Container used to build policy instances with their own
            dependencies injected.

        Returns
        -------
        None
            The registry starts empty and is filled during boot.
        """
        self.__app = app
        self.__registry = PolicyRegistry()

    def registry(self) -> PolicyRegistry:
        """Return the policy registry backing this authorizer.

        Returns
        -------
        PolicyRegistry
            Registry holding the resource to policy bindings.
        """
        return self.__registry

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
        self.__registry.register(resource, policy)

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
        # A guest never owns permissions, so skip the snapshot entirely.
        if context.isGuest:
            return False
        snapshot = await context.authorization()
        return context.isAuthenticated and snapshot.can(permission)

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
        if context.isGuest:
            return False
        snapshot = await context.authorization()
        return context.isAuthenticated and any(
            snapshot.can(permission) for permission in permissions
        )

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
        if context.isGuest:
            return False
        snapshot = await context.authorization()
        return context.isAuthenticated and all(
            snapshot.can(permission) for permission in permissions
        )

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
        if context.isGuest:
            return False
        snapshot = await context.authorization()
        return context.isAuthenticated and snapshot.hasRole(role)

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
            Resource instance, or the resource class when the ability
            does not need an instance.

        Returns
        -------
        bool
            True only when the policy explicitly allows the operation
            and the credential permits the named ability. Hooks cannot
            override credential restrictions.

        Raises
        ------
        PolicyNotFoundException
            When the resource type has no policy, or the policy does not
            declare the requested ability.
        """
        identity = context.identity
        if identity is None:
            return False

        if not ability.isidentifier() or ability.startswith("_") or ability == "before":
            return False
        abilities = context.abilities
        if abilities is not None and ability not in abilities:
            return False

        resource_type = resource if isinstance(resource, type) else type(resource)
        policy_class = self.__registry.policyFor(resource_type)
        if policy_class is None:
            error_msg = (
                f"No policy is registered for '{resource_type.__name__}'."
            )
            raise PolicyNotFoundException(error_msg)

        policy = await self.__app.build(policy_class)

        # A ``before`` hook may grant or deny without running the ability.
        verdict = await policy.before(identity, ability)
        if verdict is not None:
            return verdict is True and context.identity is identity

        handler = getattr(policy, ability, None)
        if handler is None or not callable(handler):
            error_msg = (
                f"Policy '{policy_class.__name__}' does not declare the "
                f"ability '{ability}'."
            )
            raise PolicyNotFoundException(error_msg)

        result = handler(identity, resource)
        if inspect.isawaitable(result):
            result = await result
        return result is True and context.identity is identity
