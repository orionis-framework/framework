import importlib
from typing import Any
from pwdlib.exceptions import HasherNotAvailable
from orionis.hashing.exceptions import MissingHashDependencyException

# ruff: noqa: ANN401

def import_hasher_backend(module: str, attribute: str, package: str) -> Any:
    """
    Import the backend class of a hashing driver on demand.

    Parameters
    ----------
    module : str
        Fully qualified module exposing the backend class.
    attribute : str
        Name of the backend class inside ``module``.
    package : str
        Distribution name reported to the user when the import fails.

    Returns
    -------
    Any
        The backend class ready to be instantiated.

    Raises
    ------
    MissingHashDependencyException
        If the backend package is not installed.
    """
    try:
        imported = importlib.import_module(module)
    except (ImportError, HasherNotAvailable) as exc:
        error_msg = (
            f"The '{package}' package is required by this hashing driver. "
            f"Install it with: pip install {package}"
        )
        raise MissingHashDependencyException(error_msg) from exc

    return getattr(imported, attribute)
