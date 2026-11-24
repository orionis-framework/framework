import logging
from typing import ClassVar
from orionis.container.facades.facade import Facade
from orionis.logging.contracts.logger import ILogger

class Log(Facade):

    name: ClassVar[str]

    @classmethod
    def getFacadeAccessor(cls) -> str: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> ILogger: ...

    @classmethod
    def info(cls, message: str) -> None: ...

    @classmethod
    def error(cls, message: str) -> None: ...

    @classmethod
    def warning(cls, message: str) -> None: ...

    @classmethod
    def debug(cls, message: str) -> None: ...

    @classmethod
    def critical(cls, message: str) -> None: ...

    @classmethod
    def getLogger(cls) -> logging.Logger: ...

    @classmethod
    def reloadConfiguration(cls) -> None: ...

    @classmethod
    def switchChannel(cls, channel_name: str) -> bool: ...

    @classmethod
    def close(cls) -> None: ...

    @classmethod
    async def aclose(cls) -> None: ...

    @classmethod
    def getActiveChannels(cls) -> list[str]: ...

    @classmethod
    def getActiveChannel(cls) -> str | None: ...

    @classmethod
    def getAvailableChannels(cls) -> list[str]: ...
