import os
from pathlib import Path
from orionis import Application
from orionis.http import PlainTextResponse

async def hello_world() -> PlainTextResponse:  # NOSONAR
    """
    Return the fixed payload through the framework's HTTP response adapter.

    Returns
    -------
    PlainTextResponse
        HTTP 200 plain-text response containing exactly eleven bytes.
    """
    # Keep serialization out of the measured response path.
    return PlainTextResponse(b"Hello World")

def create_application() -> Application:
    """
    Build the benchmark application and publish its worker readiness marker.

    Returns
    -------
    Application
        Configured application serving the benchmark runner's public route.
    """
    # Match the public routing and production settings used by the load test.
    app = (
        Application(base_path=Path.cwd())
        .withRouting(api="routes/benchmark.py")
        .withConfigApp(debug=False)
        .create()
    )
    # Publish readiness only after this worker finishes framework setup.
    (Path.cwd() / "worker-ready" / str(os.getpid())).touch()
    return app
