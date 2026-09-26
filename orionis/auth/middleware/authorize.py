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

class RequirePermissionMiddleware(BaseMiddleware):
    """
    Require one or more permissions before reaching the controller.

    The Orionis router attaches middleware classes, not parameterised
    instances, so the required permissions are declared by subclassing::

        class CanManageUsers(RequirePermissionMiddleware):
            permissions = ("users.view", "users.update")

        Route.get("/users", [UserController, "index"]).middleware(CanManageUsers)

    Declaring the requirement as a real class keeps the compiled route
    cache valid, which a dynamically generated class could not do.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("_authorizer",)

    # Permissions the identity must hold.
    permissions: ClassVar[tuple[str, ...]] = ()

    # Whether every permission is required, or just one of them.
    requires_all: ClassVar[bool] = True

    def __init__(self, authorizer: IAuthorizer) -> None:
        """
        Initialise the middleware with the authorizer.

        Parameters
        ----------
        authorizer : IAuthorizer
            Component evaluating the permissions of the request context.

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
        Evaluate the permissions and continue when they are granted.

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
            When the subclass declares no permission at all.
        AuthenticationException
            When the request carries no authenticated identity, which the
            handler turns into a ``401`` response.
        AuthorizationException
            When the identity is authenticated but not authorized, which
            the handler turns into a ``403`` response.
        """
        required = self.permissions
        if not required:
            error_msg = (
                f"{type(self).__name__} must declare at least one "
                f"permission in its 'permissions' attribute."
            )
            raise AuthConfigurationException(error_msg)

        context = current_auth_context()
        if context.isGuest:
            error_msg = "Unauthenticated."
            raise AuthenticationException(error_msg)

        if self.requires_all:
            granted = await self._authorizer.canAll(context, required)
        else:
            granted = await self._authorizer.canAny(context, required)

        if not granted:
            error_msg = "This action is unauthorized."
            raise AuthorizationException(error_msg)

        return await call_next()

class RequireRoleMiddleware(BaseMiddleware):
    """
    Require one or more roles before reaching the controller.

    Roles are a grouping of permissions, so prefer
    :class:`RequirePermissionMiddleware` whenever the route protects a
    concrete capability. Declare the requirement by subclassing::

        class MustBeAdmin(RequireRoleMiddleware):
            roles = ("admin",)
    """

    __slots__ = ("_authorizer",)

    # Roles the identity must hold.
    roles: ClassVar[tuple[str, ...]] = ()

    # Whether every role is required, or just one of them.
    requires_all: ClassVar[bool] = False

    def __init__(self, authorizer: IAuthorizer) -> None:
        """
        Initialise the middleware with the authorizer.

        Parameters
        ----------
        authorizer : IAuthorizer
            Component evaluating the roles of the request context.

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
        Evaluate the roles and continue when they are granted.

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
            When the subclass declares no role at all.
        AuthenticationException
            When the request carries no authenticated identity.
        AuthorizationException
            When the identity does not hold the required roles.
        """
        required = self.roles
        if not required:
            error_msg = (
                f"{type(self).__name__} must declare at least one role in "
                f"its 'roles' attribute."
            )
            raise AuthConfigurationException(error_msg)

        context = current_auth_context()
        if context.isGuest:
            error_msg = "Unauthenticated."
            raise AuthenticationException(error_msg)

        if context.abilities is not None:
            error_msg = "Restricted credentials require capability authorization."
            raise AuthorizationException(error_msg)

        granted = await self.__evaluate(context, required)
        if not granted:
            error_msg = "This action is unauthorized."
            raise AuthorizationException(error_msg)

        return await call_next()

    async def __evaluate(
        self,
        context: object,
        required: tuple[str, ...],
    ) -> bool:
        """
        Report whether the context satisfies the role requirement.

        Parameters
        ----------
        context : object
            Authentication context of the current request.
        required : tuple[str, ...]
            Roles declared by the subclass.

        Returns
        -------
        bool
            True when the requirement is satisfied.
        """
        for role in required:
            holds = await self._authorizer.hasRole(context, role)
            if holds and not self.requires_all:
                return True
            if not holds and self.requires_all:
                return False
        return self.requires_all
