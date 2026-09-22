from orionis.http.adapters.request.asgi import ASGITransportAdapter

def make_adapter(
    headers: list[tuple[bytes, bytes]], method: str = "GET",
) -> ASGITransportAdapter:
    """
    Create a request transport carrying the supplied raw headers.

    Parameters
    ----------
    headers : list[tuple[bytes, bytes]]
        Encoded request header names and values.
    method : str, optional
        HTTP method exposed by the request scope.

    Returns
    -------
    ASGITransportAdapter
        A concrete adapter for middleware assertions.
    """
    return ASGITransportAdapter({
        "type": "http", "method": method, "path": "/", "headers": headers,
        "scheme": "http", "query_string": b"", "server": ("localhost", 80),
    })
