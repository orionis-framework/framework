import os
from pathlib import Path

def mark_ready() -> None:
    """
    Publish the current worker's readiness marker when tracking is enabled.

    Returns
    -------
    None
        Create a marker under ``BENCHMARK_READY_DIR`` when it is configured.
    """
    # Use process-specific markers so the runner can verify every worker.
    directory = os.environ.get("BENCHMARK_READY_DIR")
    if directory:
        ready_directory = Path(directory)
        ready_directory.mkdir(parents=True, exist_ok=True)
        (ready_directory / str(os.getpid())).touch()
