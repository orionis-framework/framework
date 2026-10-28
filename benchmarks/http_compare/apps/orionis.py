import asyncio
import os
from pathlib import Path
from shutil import copyfile
from benchmarks.http_compare.apps._ready import mark_ready
from orionis import Application, IApplication
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime

def _track_readiness(app: IApplication) -> None:
    """
    Publish native kernel readiness without an artificial startup delay.

    Parameters
    ----------
    app : IApplication
        Application whose public HTTP readiness flag is monitored.

    Returns
    -------
    None
        Schedule readiness polling when the runner enables worker tracking.
    """
    # Leave standalone application startup untouched when no runner is present.
    if not os.environ.get("BENCHMARK_READY_DIR"):
        return

    # Get the current event loop for scheduling readiness checks.
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

    def publish_when_ready() -> None:
        """
        Publish readiness once HTTP initialization completes.

        Returns
        -------
        None
            Create the marker or schedule another readiness check.
        """
        # Startup callbacks run before kernel initialization.
        if app.isHttpReady:
            mark_ready()
        else:
            loop.call_later(0.01, publish_when_ready)

    loop.call_soon(publish_when_ready)

def create_application() -> Application:
    """
    Build Orionis through its real route loader in an isolated directory.

    Returns
    -------
    Application
        Production-configured application shared by the RSGI and ASGI cases.
    """
    directory = Path.cwd()
    # Native route imports must stay inside the isolated root without collisions.
    route_file = directory / f"_orionis_http_benchmark_{os.getpid()}.py"
    copyfile(Path(__file__).with_name("routes") / "web.py", route_file)
    return (
        Application(base_path=directory)
        .withRouting(api=route_file.name)
        .withConfigApp(env="production", debug=False, maintenance=False)
        .on(Lifespan.STARTUP, _track_readiness, runtime=Runtime.HTTP)
        .create()
    )
