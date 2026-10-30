from fastapi import FastAPI
from fastapi.responses import PlainTextResponse # pyright: ignore[reportMissingImports]

async def hello() -> PlainTextResponse:  # NOSONAR(S7503)
    """Keep native async dispatch without artificial I/O or thread offloading."""
    return PlainTextResponse("Hello World")

def create_application() -> FastAPI:
    """Create an application with only GET /."""
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    app.get("/")(hello)
    return app
