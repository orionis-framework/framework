from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.auth.contracts.authorizable import IAuthorizable

class IPermissionRepository(ABC):
    """Define how the effective permissions of an identity are loaded."""

    __slots__ = ()

    @abstractmethod
    async def loadFor(
        self,
        authorizable: IAuthorizable,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Load the permissions and roles owned by an identity.

        Parameters
        ----------
        authorizable : IAuthorizable
            Identity whose authorization must be resolved.

        Returns
        -------
        tuple[frozenset[str], frozenset[str]]
            Pair holding the effective permission names first and the role
            names second. Permissions already include the ones inherited
            from the roles of the identity.
        """
