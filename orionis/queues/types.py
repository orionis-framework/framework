from collections.abc import Awaitable, Callable
from orionis.queues.job import BaseJob

type DispatchCallback = Callable[
    [BaseJob, str | None, str | None, float], Awaitable[str],
]
