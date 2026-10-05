from orionis.console.commands.make._base import MakeStubCommand

class MakeJob(MakeStubCommand):
    """Generate a serializable application job."""

    __slots__ = ()

    timestamps: bool = False
    signature: str = "make:job"
    description: str = "Create an asynchronous queue job."
    template_name: str = "job"
    path_key: str = "app_jobs"
    success_label: str = "Job"
    postfix: str | None = "Job"
