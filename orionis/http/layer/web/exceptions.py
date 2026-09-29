from __future__ import annotations

class CSRFTokenMismatchException(Exception):
    """
    Raised when the CSRF token does not match the session token.

    Raised when the CSRF token submitted by the client does not match
    the token stored in the current session.

    This exception is thrown by ``CSRFTokenMiddleware`` on any unsafe
    HTTP method (POST, PUT, PATCH, DELETE) where CSRF validation fails.
    ``BaseExceptionHandler`` maps it to an HTTP 419 (Page Expired)
    response.
    """
