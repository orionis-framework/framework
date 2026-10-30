from typing import TYPE_CHECKING
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from starlette.requests import Request

async def hello(_request: Request) -> PlainTextResponse:  # NOSONAR(S7503)
    """Keep native async dispatch without artificial I/O or thread offloading."""
    return PlainTextResponse("Hello World")

def create_application() -> Starlette:
    """Create an application with only GET /."""
    return Starlette(routes=[Route("/", hello, methods=["GET"])])
