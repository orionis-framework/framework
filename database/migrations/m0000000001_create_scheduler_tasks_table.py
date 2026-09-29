from database.schemas.scheduler_tasks_v1 import SCHEDULER_TASKS_V1
from orionis.database import Migration
from orionis.support.facades import Schema

class CreateSchedulerTasksTable(Migration):

    async def up(self) -> None:
        """
        Create the ``scheduler_tasks`` table used to persist scheduled jobs.

        Returns
        -------
        None
            The table is created as a side effect.
        """
        await Schema.createFromDefinition(SCHEDULER_TASKS_V1)

    async def down(self) -> None:
        """
        Drop the ``scheduler_tasks`` table, reverting the ``up`` migration.

        Returns
        -------
        None
            The table is dropped as a side effect.
        """
        await Schema.drop(SCHEDULER_TASKS_V1.name)
