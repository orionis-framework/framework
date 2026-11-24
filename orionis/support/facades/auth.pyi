from collections.abc import Iterable, Mapping
from datetime import datetime
from orionis.auth.contracts.authenticatable import IAuthenticatable
from orionis.auth.contracts.authorizable import IAuthorizable
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.auth.contracts.guard import IGuard
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.contracts.policy import IPolicy
from orionis.auth.contracts.snapshot import IAuthorizationSnapshot
from orionis.auth.entities.new_access_token import NewAccessToken
from orionis.container.facades.facade import Facade

class Auth(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IAuthManager]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IAuthManager: ...

    @classmethod
    def context(cls) -> IAuthenticationContext: ...

    @classmethod
    def user(cls) -> IAuthenticatable | None: ...

    @classmethod
    def identifier(cls) -> object | None: ...

    @classmethod
    def check(cls) -> bool: ...

    @classmethod
    def guest(cls) -> bool: ...

    @classmethod
    def guard(cls, name: str | None = None) -> IGuard: ...

    @classmethod
    async def attempt(
        cls,
        credentials: Mapping[str, object],
        *,
        remember: bool = False,
    ) -> bool: ...

    @classmethod
    async def login(cls, identity: IAuthenticatable) -> None: ...

    @classmethod
    async def logout(cls) -> None: ...

    @classmethod
    async def authorization(cls) -> IAuthorizationSnapshot: ...

    @classmethod
    async def can(cls, permission: str) -> bool: ...

    @classmethod
    async def cannot(cls, permission: str) -> bool: ...

    @classmethod
    async def canAny(cls, permissions: Iterable[str]) -> bool: ...

    @classmethod
    async def canAll(cls, permissions: Iterable[str]) -> bool: ...

    @classmethod
    async def hasRole(cls, role: str) -> bool: ...

    @classmethod
    async def authorize(cls, permission: str) -> None: ...

    @classmethod
    async def allows(cls, ability: str, resource: object) -> bool: ...

    @classmethod
    async def denies(cls, ability: str, resource: object) -> bool: ...

    @classmethod
    async def authorizeResource(cls, ability: str, resource: object) -> None: ...

    @classmethod
    def registerPolicy(cls, resource: type, policy: type[IPolicy]) -> None: ...

    @classmethod
    async def createToken(
        cls,
        name: str,
        *,
        tokenable: IAuthorizable | None = None,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken: ...

    @classmethod
    async def revokeCurrentToken(cls) -> bool: ...
