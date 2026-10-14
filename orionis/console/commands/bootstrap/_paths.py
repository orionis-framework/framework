from pathlib import Path
from typing import TYPE_CHECKING
from orionis.foundation.core_paths import CORE_APP_PATHS

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

def application_path(app: IApplication, key: str) -> Path:
    """
    Resolve an effective application path with the framework default.

    Parameters
    ----------
    app : IApplication
        Configured application owning the path registry.
    key : str
        Centralized application path key.

    Returns
    -------
    Path
        Absolute destination honoring the effective application configuration.

    Raises
    ------
    TypeError
        If a configured path is not a filesystem path.
    """
    # Prefer effective paths before falling back to the centralized defaults.
    configured = app.path(key)
    if configured is None:
        configured = CORE_APP_PATHS[key]
    if not isinstance(configured, (str, Path)):
        error_msg = f"Application path '{key}' is not a filesystem path."
        raise TypeError(error_msg)
    return (app.basePath / configured).absolute()

def display_path(app: IApplication, path: Path) -> str:
    """
    Format a path relative to the application when possible.

    Parameters
    ----------
    app : IApplication
        Application providing the project root.
    path : Path
        Resource to display.

    Returns
    -------
    str
        Portable project-relative path or an absolute external path.
    """
    # Retain absolute paths when customized resources lie outside the project.
    try:
        return path.relative_to(app.basePath).as_posix()
    except ValueError:
        return path.as_posix()
