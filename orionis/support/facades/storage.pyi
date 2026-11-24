from collections.abc import Callable
from orionis.container.facades.facade import Facade
from orionis.http.payload.contracts.uploaded_file import (
    IUploadedFile as IHttpUploadedFile,
)
from orionis.storage.contracts.disk import IDisk
from orionis.storage.contracts.driver import IStorageDriver
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.contracts.uploaded_file import IUploadedFile

class Storage(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IStorageManager]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IStorageManager: ...

    @classmethod
    def disk(cls, name: str | None = None) -> IDisk: ...

    @classmethod
    def default(cls) -> IDisk: ...

    @classmethod
    def extend(
        cls,
        driver: str,
        factory: Callable[[object], IStorageDriver],
    ) -> None: ...

    @classmethod
    def uploaded(cls, source: IHttpUploadedFile) -> IUploadedFile: ...
