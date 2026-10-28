from litestar import Litestar, MediaType, Response, get # pyright: ignore[reportMissingImports]
from benchmarks.http_compare.apps._ready import WORKER_PATH, mark_ready, worker_id

async def hello() -> Response[str]: # NOSONAR
    """
    Construct a fresh plain-text response for the measured request.

    Returns
    -------
    Response[str]
        HTTP 200 response containing exactly ``Hello World``.
    """
    # Allocate each response inside the handler to avoid cached-response bias.
    return Response("Hello World", status_code=200, media_type=MediaType.TEXT)

async def worker() -> Response[str]: # NOSONAR
    """
    Identify the process serving an unmeasured preparation connection.

    Returns
    -------
    Response[str]
        HTTP 200 response containing the current worker's process ID.
    """
    return Response(worker_id(), status_code=200, media_type=MediaType.TEXT)

def create_application() -> Litestar:
    """
    Build the comparison application through Litestar's public routing API.

    Returns
    -------
    Litestar
        Application with the measured route and an unmeasured worker probe.
    """
    # Keep routing and response handling native while disabling OpenAPI routes.
    route = get("/", media_type=MediaType.TEXT)(hello)
    worker_route = get(WORKER_PATH, media_type=MediaType.TEXT)(worker)
    return Litestar(
        route_handlers=[route, worker_route],
        openapi_config=None,
        on_startup=[mark_ready],
    )
