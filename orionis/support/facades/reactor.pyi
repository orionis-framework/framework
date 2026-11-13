# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
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
        """Register a command and return its fluent configuration."""

    @classmethod
    async def call(
        cls,
        signature: str,
        args: list[str] | None = None,
    ) -> int:
        """Execute a command in an isolated failure-reporting context."""

    @classmethod
    async def info(cls) -> list[dict]:
        """Return cached metadata for non-internal commands."""
