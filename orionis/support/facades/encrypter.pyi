from orionis.container.facades.facade import Facade
from orionis.encrypter.contracts.encrypter import IEncrypter

class Crypt(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IEncrypter]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IEncrypter: ...

    @classmethod
    def encrypt(cls, plaintext: str) -> str: ...

    @classmethod
    def decrypt(cls, payload: str) -> str: ...
