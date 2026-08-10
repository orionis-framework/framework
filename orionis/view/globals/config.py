from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401

def _global_config(app: IApplication) -> Any:
    """
    Build the ``config`` template global bound to the application.

    Parameters
    ----------
    app : IApplication
        Application container providing configuration access.

    Returns
    -------
    Any
        Callable that retrieves a dot-separated configuration key.
    """
    def config(key: str, default: Any = None) -> Any:
        """
        Retrieve an application configuration value.

        Parameters
        ----------
        key : str
            Dot-separated configuration key (e.g. ``'app.name'``).
        default : Any, optional
            Value returned when the key is absent.

        Returns
        -------
        Any
            Configuration value or *default*.
        """
        cnf_value = app.config(key)
        return cnf_value if cnf_value is not None else default

    return config
