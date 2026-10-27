import asyncio
import os
from pathlib import Path
from benchmarks.http_compare.apps._ready import mark_ready
from orionis import Application, IApplication
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.http import PlainTextResponse, response

async def hello() -> PlainTextResponse: # NOSONAR
    """
    Construct the measured response through Orionis' public response factory.

    Returns
    -------
    PlainTextResponse
        HTTP 200 response containing exactly ``Hello World``.
    """
    # Measure the public response path rather than a cached transport response.
    return response.text("Hello World")

def _track_readiness(app: IApplication) -> None:
    """
    Schedule readiness tracking after the native HTTP startup callback.

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
    loop = asyncio.get_running_loop()

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
            loop.call_later(2, publish_when_ready)

    loop.call_soon(publish_when_ready)

def create_application() -> Application:
    """
    Build Orionis through its real route loader in an isolated directory.

    Returns
    -------
    Application
        Production-configured application shared by the RSGI and ASGI cases.
    """
    # Resolve application files inside the runner's isolated working directory.
    directory = Path.cwd()
    # Each worker owns its route module; no worker can import a partial write
    # from another process. Granian adds the isolated cwd to the import path.
    route_file = directory / f"_orionis_http_benchmark_{os.getpid()}.py"
    route_file.write_text(
        "from orionis.support.facades import Route\n"
        "from benchmarks.http_compare.apps.orionis import hello\n"
        "Route.get('/', hello).public()\n",
        encoding="utf-8",
    )
    return (
        Application(base_path=directory)
        .withRouting(api=route_file.name)
        .withConfigApp(env="production", debug=False, maintenance=False)
        .on(Lifespan.STARTUP, _track_readiness, runtime=Runtime.HTTP)
        .create()
    )
