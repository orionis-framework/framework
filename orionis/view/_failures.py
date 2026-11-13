# ruff: noqa: BLE001
# Observe inspection failures centrally while preserving the original service error.
"""Observe broken optional view services without reporting missing scopes."""

from orionis.failure.runtime import capture, get_runtime


async def capture_service_failure(
    error: Exception,
    contract: type,
    *,
    app: object | None = None,
) -> None:
    """
    Observe a view-service failure when its binding exists or cannot be checked.

    Ignore missing runtimes and unbound contracts. If binding inspection fails,
    observe its exception before the original service failure.

    Parameters
    ----------
    error : Exception
        Original failure raised while resolving an optional view service.
    contract : type
        Service contract to inspect for an explicit container binding.
    app : object or None, optional
        Application supplied to runtime lookup, or ``None`` for default lookup.

    Returns
    -------
    None
        No return value.
    """
    runtime = get_runtime(app)
    if runtime is None:
        return
    owner = runtime.app
    try:
        registered = owner.bound(contract)
    except Exception as inspection_error:
        await capture(
            inspection_error,
            runtime=runtime,
            flow="view",
            phase="service_inspection",
        )
        registered = True
    if registered:
        await capture(
            error,
            runtime=runtime,
            flow="view",
            phase="service",
            operation=contract.__name__,
        )
