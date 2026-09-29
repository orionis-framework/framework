from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401

def _global_app(app: IApplication) -> Any:
    """
    Build the ``app`` template global.

    Parameters
    ----------
    app : IApplication
        Application container to expose in templates.

    Returns
    -------
    Any
        Callable returning the application instance.
    """
    def application() -> IApplication:
        """
        Return the application instance.

        Returns
        -------
        IApplication
            The running application container.
        """
        return app

    return application
