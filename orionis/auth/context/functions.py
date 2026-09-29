import asyncio
from orionis.auth.context.context import GUEST_CONTEXT, AuthenticationContext
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.auth.exceptions import AuthException
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext

_AUTH_LOCK = object()

def authentication_lock() -> asyncio.Lock:
    """
    Return the lock serializing authentication transitions in this scope.

    Returns
    -------
    asyncio.Lock
        One lock shared by resolution, login, logout and token revocation.

    Raises
    ------
    AuthException
        If the owning scope is not active.
    """
    scope = ScopedContext.getCurrentScope()
    if not isinstance(scope, ScopeManager) or not scope.isActive:
        error_msg = "Authentication requires an active container scope."
        raise AuthException(error_msg)
    lock = scope[_AUTH_LOCK]
    if lock is None:
        lock = asyncio.Lock()
        scope[_AUTH_LOCK] = lock
    return lock

def current_auth_context() -> IAuthenticationContext:
    """
    Return the authentication context bound to the current scope.

    The context lives in the container scope the HTTP kernel opens for
    every request, which is backed by ``contextvars``. Code running
    outside a request, such as a console command, always sees the shared
    guest context.

    Returns
    -------
    IAuthenticationContext
        Context of the running request, or the shared guest context when
        no scope is active or nothing was bound yet.
    """
    scope = ScopedContext.getCurrentScope()
    if not isinstance(scope, ScopeManager) or not scope.isActive:
        return GUEST_CONTEXT

    context = scope[IAuthenticationContext]
    if context is None:
        return GUEST_CONTEXT
    return context

def bind_auth_context(context: IAuthenticationContext) -> None:
    """
    Bind an authentication context to the current scope.

    Parameters
    ----------
    context : IAuthenticationContext
        Context resolved for the running request.

    Returns
    -------
    None
        The scope is updated as a side effect.

    Raises
    ------
    AuthException
        When no container scope is active, which means the caller is not
        inside a request and has nowhere to store the context.
    """
    scope = ScopedContext.getCurrentScope()
    if not isinstance(scope, ScopeManager) or not scope.isActive:
        error_msg = (
            "No active container scope. An authentication context can "
            "only be bound inside a request."
        )
        raise AuthException(error_msg)

    if isinstance(context, AuthenticationContext) and context is not GUEST_CONTEXT:
        context._bindToScope(scope)  # noqa: SLF001
    scope[IAuthenticationContext] = context
