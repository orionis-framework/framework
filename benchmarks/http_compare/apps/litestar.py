from litestar import Litestar, MediaType, Response, get # pyright: ignore[reportMissingImports]

async def hello() -> Response[str]:  # NOSONAR(S7503)
    """Keep native async dispatch without artificial I/O or thread offloading."""
    return Response("Hello World", media_type=MediaType.TEXT)

def create_application() -> Litestar:
    """Create an application with only GET /."""
    return Litestar(
        route_handlers=[get("/", media_type=MediaType.TEXT)(hello)],
        openapi_config=None,
    )
