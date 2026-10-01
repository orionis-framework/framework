from typing import Any, Self
from app.models.user import User
from orionis.orm.factories import Factory

class UserFactory(Factory[User]):
    """
    Generate user attributes, accepting a password hash at creation time.

    The User schema requires a password. Pass a hash produced by Orionis's
    async hasher to ``create(password=password_hash)`` before persisting.
    """

    __slots__ = ()

    model = User

    def definition(self) -> dict[str, Any]:
        """
        Define public user attributes without automatic database columns.

        Returns
        -------
        dict of str to Any
            Name, instance-unique email and active status.
        """
        return {
            "name": self.fake.name(),
            "email": self.fake.unique.email(),
            "active": True,
        }

    def inactive(self) -> Self:
        """
        Configure inactive users for subsequent generation.

        Returns
        -------
        Self
            This factory with the inactive state appended.
        """
        return self.state({"active": False})
