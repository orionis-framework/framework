from orionis.console.fluent.contracts.task import ITask
from orionis.container.contracts.facade import IFacade
from orionis.http.routes.contracts.router import IRouter

class Schedule(IRouter, IFacade):

    @classmethod
    def command(
        cls,
        signature: str,
        args: list[str] | None = None,
        purpose: str | None = None,
    ) -> ITask:
        ...
