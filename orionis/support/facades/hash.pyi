from orionis.container.facades.facade import Facade
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.contracts.hasher import IHasher

class Hash(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IHashManager]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IHashManager: ...

    @classmethod
    def driver(cls, name: str | None = None) -> IHasher: ...

    @classmethod
    def getDefaultDriver(cls) -> str: ...

    @classmethod
    async def make(
        cls,
        value: str,
        *,
        rounds: int | None = None,
        memory: int | None = None,
        threads: int | None = None,
    ) -> str: ...

    @classmethod
    async def check(cls, value: str, hashed: str) -> bool: ...

    @classmethod
    def needsRehash(cls, hashed: str) -> bool: ...

    @classmethod
    def getAlgorithm(cls) -> str: ...

    @classmethod
    def setRounds(cls, rounds: int) -> IHashManager: ...
