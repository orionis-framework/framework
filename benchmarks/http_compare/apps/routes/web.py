from orionis.http import PlainTextResponse, response
from orionis.support.facades import Route

async def hello() -> PlainTextResponse:  # NOSONAR(S7503)
    """Keep native async dispatch without artificial I/O or thread offloading."""
    return response.text("Hello World")

Route.get("/", hello).public()
