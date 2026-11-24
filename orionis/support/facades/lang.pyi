from orionis.container.facades.facade import Facade
from orionis.localization.contracts.translator import ITranslator
from orionis.localization.types import MissingKeyHandler

class Lang(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[ITranslator]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> ITranslator: ...

    @classmethod
    def get(cls, key: str, locale: str | None = None, **replace: object) -> str: ...

    @classmethod
    def has(
        cls,
        key: str,
        locale: str | None = None,
        *,
        fallback: bool = True,
    ) -> bool: ...

    @classmethod
    def choice(
        cls,
        key: str,
        count: int,
        locale: str | None = None,
        **replace: object,
    ) -> str: ...

    @classmethod
    def setLocale(cls, locale: str) -> None: ...

    @classmethod
    def getLocale(cls) -> str: ...

    @classmethod
    def availableLocales(cls) -> tuple[str, ...]: ...

    @classmethod
    def reload(cls, locale: str | None = None) -> None: ...

    @classmethod
    def forget(cls, locale: str) -> bool: ...

    @classmethod
    def flush(cls) -> None: ...

    @classmethod
    def missing(cls, handler: MissingKeyHandler | None) -> None: ...
