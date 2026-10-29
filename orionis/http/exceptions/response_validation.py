class ResponseValidationException(RuntimeError):
    """
    Report an invalid schema returned by an HTTP handler.

    The original ``ValidationException`` is preserved as ``__cause__`` for
    application error reporting. Output validation failures follow ordinary
    server error handling, rather than the client input validation response.
    """
