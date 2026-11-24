# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from typing import Any
from orionis.console.entities.command import CommandInfo
from orionis.console.fluent.contracts.command import ICommand
from orionis.console.core.contracts.reactor import IReactor
from orionis.container.facades.facade import Facade

class Reactor(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """Return the container alias for the command reactor."""

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IReactor:
        """Resolve the command reactor from the container."""

    @classmethod
    def command(
        cls,
        signature: str,
        handler: list[type[Any] | str | None] | str,
    ) -> ICommand:
        """Register a command and return its fluent configuration."""

    @classmethod
    async def hasCommand(cls, signature: str) -> bool:
        """Check whether the command signature is registered."""

    @classmethod
    async def call(
        cls,
        signature: str,
        args: list[str] | None = None,
    ) -> int:
        """Execute a command in an isolated failure-reporting context."""

    @classmethod
    async def info(cls) -> list[CommandInfo]:
        """Return cached metadata for non-internal commands."""
