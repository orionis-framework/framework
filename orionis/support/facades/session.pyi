# ruff: noqa: ANN401, N815
# Match the session's property names and its arbitrary stored values.
from collections.abc import Mapping
from typing import Any, ClassVar
from orionis.container.facades.facade import ScopedFacade
from orionis.session.contracts.session import ISession

class Session(ScopedFacade):

    id: ClassVar[str | None]
    started: ClassVar[bool]
    dirty: ClassVar[bool]
    invalidated: ClassVar[bool]
    isNew: ClassVar[bool]
    wantsRegenerate: ClassVar[bool]

    @classmethod
    def getFacadeAccessor(cls) -> type[ISession]: ...

    @classmethod
    def scopedInstance(cls) -> ISession: ...

    @classmethod
    async def resolve(cls, *_args: object, **_kwargs: object) -> ISession: ...

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any: ...

    @classmethod
    def put(cls, key: str, value: Any) -> None: ...

    @classmethod
    def has(cls, key: str) -> bool: ...

    @classmethod
    def forget(cls, key: str) -> None: ...

    @classmethod
    def clear(cls) -> None: ...

    @classmethod
    def flash(cls, key: str, value: Any) -> None: ...

    @classmethod
    def getFlash(cls, key: str, default: Any = None) -> Any: ...

    @classmethod
    def flashInput(cls, values: Mapping[str, Any]) -> None: ...

    @classmethod
    def getOldInput(cls, key: str, default: Any = None) -> Any: ...

    @classmethod
    def flashErrors(cls, errors: Mapping[str, Any] | Exception) -> None: ...

    @classmethod
    def getErrors(cls) -> dict[str, list[str]]: ...

    @classmethod
    def setPreviousUrl(cls, url: str) -> None: ...

    @classmethod
    def getPreviousUrl(cls, default: str | None = None) -> str | None: ...

    @classmethod
    def regenerate(cls) -> None: ...

    @classmethod
    def invalidate(cls) -> None: ...

    @classmethod
    def all(cls) -> dict[str, Any]: ...
