from abc import abstractmethod
from typing import TYPE_CHECKING
from orionis.auth.contracts.guard import IGuard

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.http.request import Request

class ISessionGuard(IGuard):
    """Define the stateful operations supported by session authentication."""

    __slots__ = ()

    @abstractmethod
    async def attempt(
        self,
        request: Request,
        credentials: Mapping[str, object],
    ) -> IAuthenticatable | None:
        """Validate credentials and start an authenticated session.

        Parameters
        ----------
        request : Request
            Incoming HTTP request owning the session.
        credentials : Mapping[str, object]
            Submitted credentials, typically the username and password.

        Returns
        -------
        IAuthenticatable | None
            Authenticated identity, or ``None`` when the credentials do
            not match any identity.
        """

    @abstractmethod
    def login(self, request: Request, identity: IAuthenticatable) -> None:
        """Persist an identity in the session of the current request.

        The session identifier is rotated to close any session fixation
        window opened before the login.

        Parameters
        ----------
        request : Request
            Incoming HTTP request owning the session.
        identity : IAuthenticatable
            Identity to remember for subsequent requests.

        Returns
        -------
        None
            The session is mutated as a side effect.
        """

    @abstractmethod
    def logout(self, request: Request) -> None:
        """Drop the authenticated state from the session.

        Parameters
        ----------
        request : Request
            Incoming HTTP request owning the session.

        Returns
        -------
        None
            The session is invalidated as a side effect.
        """
