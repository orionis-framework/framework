from typing import TYPE_CHECKING
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# Register callbacks for the generic startup event.
async def on_startup() -> None:
    """
    Handle the generic application startup event.

    Returns
    -------
    None
        Completes without registering additional startup behavior.
    """

# Register callbacks for the generic shutdown event.
async def on_shutdown() -> None:
    """
    Handle the generic application shutdown event.

    Returns
    -------
    None
        Completes without registering additional shutdown behavior.
    """

# Register callbacks for CLI startup.
async def on_startup_cli() -> None:
    """
    Handle the CLI startup event.

    Returns
    -------
    None
        Completes without registering additional CLI startup behavior.
    """

# Register callbacks for CLI shutdown.
async def on_shutdown_cli() -> None:
    """
    Handle the CLI shutdown event.

    Returns
    -------
    None
        Completes without registering additional CLI shutdown behavior.
    """

# Register callbacks for HTTP startup.
async def on_startup_http() -> None:
    """
    Handle the HTTP startup event.

    Returns
    -------
    None
        Completes without registering additional HTTP startup behavior.
    """

# Register callbacks for HTTP shutdown.
async def on_shutdown_http() -> None:
    """
    Handle the HTTP shutdown event.

    Returns
    -------
    None
        Completes without registering additional HTTP shutdown behavior.
    """

# Register all application lifespan callbacks.
def register_lifespan_callbacks(app: IApplication) -> None:
    """
    Register callbacks for application lifespan events.

    Parameters
    ----------
    app : IApplication
        Application instance that receives the lifespan callbacks.

    Returns
    -------
    None
        Registers generic, CLI, and HTTP startup and shutdown callbacks.
    """
    app.on(Lifespan.STARTUP, on_startup)
    app.on(Lifespan.SHUTDOWN, on_shutdown)
    app.on(Lifespan.STARTUP, on_startup_cli, runtime=Runtime.CLI)
    app.on(Lifespan.SHUTDOWN, on_shutdown_cli, runtime=Runtime.CLI)
    app.on(Lifespan.STARTUP, on_startup_http, runtime=Runtime.HTTP)
    app.on(Lifespan.SHUTDOWN, on_shutdown_http, runtime=Runtime.HTTP)
