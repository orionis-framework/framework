from __future__ import annotations
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from orionis.http.responses import RedirectResponse

if TYPE_CHECKING:
    from orionis.http.default.contracts.responses import IDefaultResponses
    from orionis.http.request import Request
    from orionis.http.responses import Response
    from orionis.schemas.exceptions.validation import ValidationException

_DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}
_FIRST_PRINTABLE_CODE: int = 32
_DELETE_CODE: int = 127

def _url_origin(url: str) -> tuple[str, str | None, int | None]:
    """
    Extract the normalized scheme, hostname, and effective port of a URL.

    Parameters
    ----------
    url : str
        Absolute URL whose origin is compared with the application origin.

    Returns
    -------
    tuple[str, str | None, int | None]
        Scheme, lowercase hostname, and explicit or default port.

    Raises
    ------
    ValueError
        If the authority or port is malformed or contains user credentials.
    """
    parsed = urlsplit(url)
    if parsed.username is not None:
        error_msg = "Redirect references cannot contain user credentials."
        raise ValueError(error_msg)
    port = parsed.port
    return (
        parsed.scheme,
        parsed.hostname,
        _DEFAULT_PORTS.get(parsed.scheme) if port is None else port,
    )

def _is_local_reference(reference: str, base_url: str) -> bool:
    """
    Accept a local path or an absolute reference with the application origin.

    Parameters
    ----------
    reference : str
        Untrusted referrer supplied by the client.
    base_url : str
        Base URL of the current application request.

    Returns
    -------
    bool
        Whether the referrer is suitable for a same-origin redirect.
    """
    if "\\" in reference or any(
        ord(char) < _FIRST_PRINTABLE_CODE or ord(char) == _DELETE_CODE
        for char in reference
    ):
        return False
    if reference.startswith("/"):
        return not reference.startswith("//")
    try:
        return _url_origin(reference) == _url_origin(base_url)
    except ValueError:
        return False

async def validation_response(
    exc: ValidationException,
    request: Request,
    responses: IDefaultResponses,
) -> Response:
    """
    Translate a schema validation failure into an HTTP response.

    JSON and AJAX clients receive the structured ``422`` payload, while
    browsers are redirected back to the submitted form with the errors and
    the previous input flashed into the session.

    Parameters
    ----------
    exc : ValidationException
        Failure carrying every field error found in the payload.
    request : Request
        Incoming HTTP request.
    responses : IDefaultResponses
        Default response factory used to render the error payload.

    Returns
    -------
    Response
        A ``422`` response, or a ``302`` redirect back to the previous page.
    """
    if request.wantsJson() or request.isAjax():
        return responses.error(
            status_code=422,
            content=exc.error(),
            expects_json=True,
        )

    response = RedirectResponse(url=previous_url(request), status_code=302)
    response.withErrors(exc.errors)

    # Repopulate the form with the submitted values, minus credentials.
    try:
        submitted = await request.data()
    except Exception:  # noqa: BLE001
        submitted = None
    if submitted:
        response.withInput(submitted)

    return response

def previous_url(request: Request) -> str:
    """
    Resolve the page a failed submission should be redirected back to.

    Resolution order: the last page recorded by the session middleware, the
    referring URL when it belongs to this application, and finally the URL
    the form was submitted to.

    Parameters
    ----------
    request : Request
        Incoming HTTP request.

    Returns
    -------
    str
        Absolute URL or path to redirect back to.
    """
    session = getattr(request.state, "session", None)
    if session is not None:
        previous = session.getPreviousUrl()
        if previous:
            return previous

    referer = request.headers.get("referer")
    if referer and _is_local_reference(referer, request.baseUrl):
        return referer

    # Forms usually post to the page that renders them.
    return request.url
