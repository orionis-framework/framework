from typing import ClassVar

from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.commands.queue._signals import WorkerSignals
from orionis.console.enums.actions import ArgumentAction
from orionis.queues.contracts.manager import IQueueManager  # noqa: TC001
from orionis.queues.exceptions import QueueError


class QueueWorkCommand(BaseCommand):
    """Run an asynchronous worker over prioritized logical queues."""

    __slots__ = ()

    timestamps: bool = False
    signature: str = "queue:work"
    description: str = "Consume queued jobs with retries and graceful shutdown."
    arguments: ClassVar[list[Argument]] = [
        Argument(name_or_flags="connection", type_=str, nargs="?", default=None),
        Argument(name_or_flags="--queue", type_=str, default=None),
        Argument(name_or_flags="--concurrency", type_=int, default=None),
        Argument(name_or_flags="--max-jobs", type_=int, default=None, dest="max_jobs"),
        Argument(
            name_or_flags="--stop-when-empty",
            action=ArgumentAction.STORE_TRUE,
            default=False,
            dest="stop_when_empty",
        ),
    ]

    async def handle(self, manager: IQueueManager) -> int:
        """Consume jobs until shutdown or a requested stopping condition.

        Parameters
        ----------
        manager : IQueueManager
            Queue manager resolved from the current application container.

        Returns
        -------
        int
            Zero after a clean stop or one for invalid queue settings.
        """
        queue_argument = self.getArgument("queue")
        queues = (
            tuple(name.strip() for name in queue_argument.split(","))
            if queue_argument is not None else None
        )
        try:
            worker = await manager.worker(
                connection=self.getArgument("connection"),
                queues=queues,
                concurrency=self.getArgument("concurrency"),
            )
            with WorkerSignals(worker):
                processed = await worker.run(
                    stop_when_empty=self.getArgument("stop_when_empty", default=False),
                    max_jobs=self.getArgument("max_jobs"),
                )
        except QueueError as error:
            self.error(str(error), timestamp=False)
            return 1
        self.success(f"Worker stopped after {processed} attempt(s).", timestamp=False)
        return 0
