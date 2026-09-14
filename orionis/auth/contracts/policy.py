from abc import ABC, abstractmethod

class IPolicy(ABC):
    """Define the contract shared by every resource policy.

    A permission answers "may this identity perform this capability?".
    A policy answers "may this identity perform this operation on *this*
    resource?", so it receives the resource together with the identity.
    """

    __slots__ = ()

    @abstractmethod
    async def before(self, identity: object, ability: str) -> bool | None:
        """Short circuit the policy before the ability method runs.

        Parameters
        ----------
        identity : object
            Authenticated identity being evaluated.
        ability : str
            Name of the ability requested on the resource.

        Returns
        -------
        bool | None
            ``True`` to allow and ``False`` to deny without calling the
            ability method, or ``None`` to continue the normal evaluation.
        """
