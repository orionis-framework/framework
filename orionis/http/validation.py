from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.http.responses import RedirectResponse

if TYPE_CHECKING:
    from orionis.http.default.contracts.responses import IDefaultResponses
    from orionis.http.request import Request
    from orionis.http.responses import Response
    from orionis.schemas.exceptions.validation import ValidationException

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
    if referer:

        # Only same-origin referrers are trusted, avoiding open redirects.
        if referer.startswith(request.baseUrl):
            return referer
        if referer.startswith("/") and not referer.startswith("//"):
            return referer

    # Forms usually post to the page that renders them.
    return request.url
