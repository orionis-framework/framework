from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.auth.entities.guard_result import GuardResult
    from orionis.http.request import Request

class IGuard(ABC):
    """
    Define how an authenticated identity is extracted from a request.

    A guard answers exactly one question: given the current HTTP context,
    is there an authenticated identity and which one is it?
    """

    __slots__ = ()

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
    async def resolve(self, request: Request) -> GuardResult | None:
        """
        Resolve the identity backing the incoming request.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.

        Returns
        -------
        GuardResult | None
            Resolved identity together with the abilities of the presented
            credential, or ``None`` when the request is anonymous.
        """
