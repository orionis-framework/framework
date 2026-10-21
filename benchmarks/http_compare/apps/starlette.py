from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from starlette.applications import Starlette # pyright: ignore[reportMissingImports]
from starlette.responses import PlainTextResponse # pyright: ignore[reportMissingImports]
from starlette.routing import Route # pyright: ignore[reportMissingImports]
from benchmarks.http_compare.apps._ready import mark_ready

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from starlette.requests import Request # pyright: ignore[reportMissingImports]

@asynccontextmanager
async def _lifespan(_app: Starlette) -> AsyncIterator[None]:
    """
    Signal worker readiness within Starlette's startup lifecycle.

    Parameters
    ----------
    _app : Starlette
        Application owning the lifecycle context, unused by this callback.

    Yields
    ------
    None
        Keep the application lifecycle active until server shutdown.
    """
    # Publish the marker during startup, not while the module is being imported.
    mark_ready()
    yield

async def hello(_request: Request) -> PlainTextResponse: # NOSONAR
    """
    Construct a fresh plain-text response for the measured request.

    Parameters
    ----------
    _request : Request
        Incoming request, unused by this fixed-payload handler.

    Returns
    -------
    PlainTextResponse
        HTTP 200 response containing exactly ``Hello World``.
    """
    # Allocate each response inside the handler to avoid cached-response bias.
    return PlainTextResponse("Hello World", status_code=200)

def create_application() -> Starlette:
    """
    Build the comparison application through Starlette's public routing API.

    Returns
    -------
    Starlette
        Application with one text route and worker readiness tracking.
    """
    # Keep the route on Starlette's native router with lifecycle-based readiness.
    return Starlette(
        routes=[Route("/", hello, methods=["GET"])], lifespan=_lifespan,
    )
