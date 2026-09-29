from typing import Any
from orionis.console.fluent.contracts.command import ICommand
from orionis.console.core.contracts.reactor import IReactor
from orionis.container.contracts.facade import IFacade

class Reactor(IReactor, IFacade):

    @classmethod
    def command(
        cls,
        signature: str,
        handler: list[type[Any] | str | None] | str,
    ) -> ICommand:
        ...

    @classmethod
    async def call(
        cls,
        signature: str,
        args: list[str] | None = None,
    ) -> int:
        ...

    @classmethod
    async def info(cls) -> list[dict]:
        ...
