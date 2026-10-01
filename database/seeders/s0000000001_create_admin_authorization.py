from app.models.user import User
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.database.seeders.seeder import Seeder
from orionis.support.facades import Hash

class CreateAdminAuthorizationSeeder(Seeder):

    __slots__ = ("__registrar",)

    def __init__(
        self,
        registrar: PermissionRegistrar,
    ) -> None:
        """
        Receive authorization and hashing services from the container.

        Parameters
        ----------
        registrar : PermissionRegistrar [Dependency Injection]
            Service for creating roles, permissions, and associations.
        """
        self.__registrar = registrar

    async def run(self) -> None:
        """
        Seed authorization using the application's real model and registrar.

        Returns
        -------
        None
            The administrator and authorization records are persisted.
        """
        await self.__registrar.createRole("admin")
        await self.__registrar.createPermission("full_access")
        await self.__registrar.grantToRole("admin", "full_access")

        administrator = await User.create({
            "name": "Orionis Admin",
            "email": "admin@example.com",
            "active": True,
            "password": await Hash.make("Orionis123*+"),
        })
        await self.__registrar.assignRole(administrator, "admin")
