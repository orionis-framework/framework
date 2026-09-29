from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Float, LargeBinary, Unicode

SCHEDULER_TASKS_V1 = TableDefinition(
    name="scheduler_tasks",
    columns={
        "id": Unicode(191).primary().comment("Job ID"),
        "next_run_time": Float().nullable().index().comment("Next Run Time"),
        "job_state": LargeBinary().comment("Job State"),
    },
    comment="Table to store scheduled jobs (tasks).",
)
