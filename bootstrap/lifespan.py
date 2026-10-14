from typing import TYPE_CHECKING
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

async def on_startup() -> None:
    """
    Handle application startup.

    Returns
    -------
    None
        Complete the callback without additional startup behavior.
    """
    # Add application startup behavior here.

async def on_shutdown() -> None:
    """
    Handle application shutdown.

    Returns
    -------
    None
        Complete the callback without additional shutdown behavior.
    """
    # Add application shutdown behavior here.

async def on_startup_cli() -> None:
    """
    Handle CLI startup.

    Returns
    -------
    None
        Complete the callback without additional CLI startup behavior.
    """
    # Add CLI startup behavior here.

async def on_shutdown_cli() -> None:
    """
    Handle CLI shutdown.

    Returns
    -------
    None
        Complete the callback without additional CLI shutdown behavior.
    """
    # Add CLI shutdown behavior here.

async def on_startup_http() -> None:
    """
    Handle HTTP startup.

    Returns
    -------
    None
        Complete the callback without additional HTTP startup behavior.
    """
    # Add HTTP startup behavior here.

async def on_shutdown_http() -> None:
    """
    Handle HTTP shutdown.

    Returns
    -------
    None
        Complete the callback without additional HTTP shutdown behavior.
    """
    # Add HTTP shutdown behavior here.

def register_lifespan_callbacks(app: IApplication) -> None:
    """
    Register application callbacks through the native lifecycle API.

    Parameters
    ----------
    app : IApplication
        Application receiving the generic and runtime-specific callbacks.

    Returns
    -------
    None
        Attach startup and shutdown callbacks to the application.
    """
    # Register generic callbacks before the runtime-specific callbacks.
    app.on(Lifespan.STARTUP, on_startup)
    app.on(Lifespan.SHUTDOWN, on_shutdown)
    app.on(Lifespan.STARTUP, on_startup_cli, runtime=Runtime.CLI)
    app.on(Lifespan.SHUTDOWN, on_shutdown_cli, runtime=Runtime.CLI)
    app.on(Lifespan.STARTUP, on_startup_http, runtime=Runtime.HTTP)
    app.on(Lifespan.SHUTDOWN, on_shutdown_http, runtime=Runtime.HTTP)
