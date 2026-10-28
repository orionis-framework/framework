from benchmarks.http_compare.apps._ready import WORKER_PATH, worker_id
from orionis.http import PlainTextResponse, response
from orionis.support.facades import Route

async def hello() -> PlainTextResponse: # NOSONAR
    """
    Construct the measured response through Orionis' public response factory.

    Returns
    -------
    PlainTextResponse
        HTTP 200 response containing exactly ``Hello World``.
    """
    return response.text("Hello World")

async def worker() -> PlainTextResponse: # NOSONAR
    """
    Identify the process serving an unmeasured preparation connection.

    Returns
    -------
    PlainTextResponse
        HTTP 200 response containing the current worker's process ID.
    """
    return response.text(worker_id())

Route.get("/", hello).public()
Route.get(WORKER_PATH, worker).public()
