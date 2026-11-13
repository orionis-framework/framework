# ruff: noqa: TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
"""Provide view globals operations through ``_global_app``."""

from __future__ import annotations

from collections.abc import Callable

from orionis.foundation.contracts.application import IApplication


def _global_app(app: IApplication) -> Callable[[], IApplication]:
    """
    Build the ``app`` template global.

    Parameters
    ----------
    app : orionis.IApplication
        Application container to expose in templates.

    Returns
    -------
    collections.abc.Callable
        Callable returning the application instance.
    """

    def application() -> IApplication:
        """
        Return the application instance.

        Returns
        -------
        orionis.IApplication
            The running application container.
        """
        return app

    return application
