"""Generate a serializable application job."""

from orionis.console.commands.make._base import MakeStubCommand

class MakeJob(MakeStubCommand):
    """Generate a serializable application job."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeJob``."""
    signature: str = "make:job"
    """Signature identifier: ``make:job``."""
    description: str = "Create an asynchronous queue job."
    """Description identifier: ``Create an asynchronous queue job.``."""
    template_name: str = "job"
    """Template name identifier: ``job``."""
    path_key: str = "app_jobs"
    """Path key identifier: ``app_jobs``."""
    success_label: str = "Job"
    """Success label identifier: ``Job``."""
    postfix: str | None = "Job"
    """Postfix identifier: ``Job``."""
