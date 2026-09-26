from typing import TYPE_CHECKING, ClassVar
from orionis.auth.context.functions import current_auth_context
from orionis.auth.contracts.authorizer import IAuthorizer
from orionis.auth.exceptions import (
    AuthConfigurationException,
    AuthenticationException,
    AuthorizationException,
)
from orionis.http.middleware import BaseMiddleware

if TYPE_CHECKING:
    from orionis.http.layer.contracts.middleware import NextCallable
    from orionis.http.request import Request
    from orionis.http.responses import Response

class RequirePolicyMiddleware(BaseMiddleware):
    """
    Gate a route behind a policy ability declared on a resource class.

    The middleware evaluates the ability against the resource **class**,
    which covers the gates that do not need a loaded row, such as
    ``viewAny`` or ``create``::

        class CanCreatePosts(RequirePolicyMiddleware):
            ability = "create"
            resource = Post

    Abilities that depend on a concrete row belong in the controller,
    where the instance already exists::

        await Auth.authorizeResource("update", post)
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("_authorizer",)

    # Ability declared by the policy of the resource.
    ability: ClassVar[str] = ""

    # Resource class protected by the policy.
    resource: ClassVar[type | None] = None

    def __init__(self, authorizer: IAuthorizer) -> None:
        """
        Initialise the middleware with the authorizer.

        Parameters
        ----------
        authorizer : IAuthorizer
            Component resolving and running the policy.

        Returns
        -------
        None
            The middleware keeps no per request state.
        """
        self._authorizer = authorizer

    async def handle(
        self,
        request: Request,  # noqa: ARG002
        call_next: NextCallable,
    ) -> Response:
        """
        Evaluate the policy and continue when it allows the operation.

        Parameters
        ----------
        request : Request
            Incoming HTTP request, unused by this middleware.
        call_next : NextCallable
            Callable advancing to the next layer.

        Returns
        -------
        Response
            Response produced by the rest of the pipeline.

        Raises
        ------
        AuthConfigurationException
            When the subclass declares no ability or no resource.
        AuthenticationException
            When the request carries no authenticated identity.
        AuthorizationException
            When the policy denies the operation.
        """
        ability = self.ability
        resource = self.resource
        if not ability or resource is None:
            error_msg = (
                f"{type(self).__name__} must declare both an 'ability' and "
                f"a 'resource'."
            )
            raise AuthConfigurationException(error_msg)

        context = current_auth_context()
        if context.isGuest:
            error_msg = "Unauthenticated."
            raise AuthenticationException(error_msg)

        allowed = await self._authorizer.allows(context, ability, resource)
        if not allowed:
            error_msg = "This action is unauthorized."
            raise AuthorizationException(error_msg)

        return await call_next()
