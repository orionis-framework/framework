# ruff: noqa: TC001
# Keep runtime annotations, guarded exits, and framework integration explicit.
"""Define how an authenticated identity is extracted from a request."""

from abc import ABC, abstractmethod

import orionis.http as _http
from orionis.auth.entities.guard_result import GuardResult


class IGuard(ABC):
    """
    Define how an authenticated identity is extracted from a request.

    A guard answers exactly one question: given the current HTTP context,
    is there an authenticated identity and which one is it?
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the configuration name of this guard.

        Returns
        -------
        str
            Name used by the configuration and stored in the context.
        """

    @abstractmethod
    async def resolve(self, request: _http.Request) -> GuardResult | None:
        """
        Resolve the identity backing the incoming request.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming HTTP request.

        Returns
        -------
        orionis.auth.entities.GuardResult | None
            Resolved identity together with the abilities of the presented
            credential, or ``None`` when the request is anonymous.
        """
