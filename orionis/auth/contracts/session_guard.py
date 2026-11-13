# ruff: noqa: TC001, TC003
# Keep runtime annotations, guarded exits, and framework integration explicit.
"""Define the stateful operations supported by session authentication."""

from abc import abstractmethod
from orionis.auth.contracts.guard import IGuard

import orionis.http as _http
from collections.abc import Mapping
from orionis.auth.contracts.authenticatable import IAuthenticatable


class ISessionGuard(IGuard):
    """Define the stateful operations supported by session authentication."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def attempt(
        self,
        request: _http.Request,
        credentials: Mapping[str, object],
        *,
        remember: bool = False,
    ) -> IAuthenticatable | None:
        """
        Validate credentials and start an authenticated session.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming HTTP request owning the session.
        credentials : collections.abc.Mapping[str, object]
            Submitted credentials, typically the username and password.
        remember : bool, optional
            Issue a persistent login credential after verifying the password.

        Returns
        -------
        orionis.auth.contracts.IAuthenticatable | None
            Authenticated identity, or ``None`` when the credentials do
            not match any identity.
        """

    @abstractmethod
    def login(self, request: _http.Request, identity: IAuthenticatable) -> None:
        """
        Persist an identity in the session of the current request.

        The session identifier is rotated to close any session fixation
        window opened before the login.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming HTTP request owning the session.
        identity : orionis.auth.contracts.IAuthenticatable
            Identity to remember for subsequent requests.

        Returns
        -------
        None
            No return value.
        """

    @abstractmethod
    async def logout(self, request: _http.Request) -> None:
        """
        Drop the authenticated state from the session.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming HTTP request owning the session.

        Returns
        -------
        None
            No return value.
        """
