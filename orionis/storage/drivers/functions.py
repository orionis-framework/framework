from __future__ import annotations
import importlib
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from orionis.storage.exceptions import (
    MissingStorageDependencyException,
    UnsupportedStorageOperationException,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from types import ModuleType

# Binary modes accepted by driver open() implementations.
_ALLOWED_MODES: frozenset[str] = frozenset(
    {"rb", "wb", "ab", "rb+", "wb+", "ab+"},
)

def importDriverDependency(module: str, package: str, extra: str) -> ModuleType:
    """
    Import an optional SDK module required by a storage driver.

    Cloud drivers rely on the official SDK of each platform, which is
    **not** installed with the framework. This helper performs the
    import lazily and converts a missing package into a descriptive
    storage exception with installation instructions.

    Parameters
    ----------
    module : str
        Dotted module path to import (e.g. ``'boto3'``).
    package : str
        PyPI package that provides the module (e.g. ``'boto3'``).
    extra : str
        Orionis extra that pulls the package (e.g. ``'s3'``), used to
        suggest ``pip install orionis[extra]``.

    Returns
    -------
    ModuleType
        The imported module.

    Raises
    ------
    MissingStorageDependencyException
        If the package is not installed in the active environment.
    """
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        error_msg = (
            f"The [{extra}] storage driver requires the optional package "
            f"[{package}]. Install it with 'pip install {package}' or "
            f"'pip install orionis[{extra}]'."
        )
        raise MissingStorageDependencyException(error_msg) from exc

def assertBinaryMode(mode: str) -> None:
    """
    Validate a stream mode against the supported binary modes.

    Parameters
    ----------
    mode : str
        Mode requested by the caller.

    Returns
    -------
    None

    Raises
    ------
    UnsupportedStorageOperationException
        If *mode* is not one of ``'rb'``, ``'wb'``, ``'ab'``,
        ``'rb+'``, ``'wb+'``, or ``'ab+'``.
    """
    if mode not in _ALLOWED_MODES:
        error_msg = f"Unsupported stream mode [{mode}]."
        raise UnsupportedStorageOperationException(error_msg)

def resolveDownloadTarget(normalized: str, destination: str | Path) -> Path:
    """
    Resolve the local target path for a download operation.

    When *destination* points to an existing directory, the file keeps
    its original name inside that directory. Missing parent
    directories are created.

    Parameters
    ----------
    normalized : str
        Canonical root-relative path of the remote file.
    destination : str | Path
        Local target file or existing directory.

    Returns
    -------
    Path
        Local path where the file must be written.
    """
    target = Path(destination)

    # Keep the original name when the destination is a directory.
    if target.is_dir():
        target = target / PurePosixPath(normalized).name
    target.parent.mkdir(parents=True, exist_ok=True)
    return target

def filterFiles(
    keys: Iterable[str],
    base: str,
    *,
    recursive: bool,
) -> list[str]:
    """
    Select the object keys that represent files under *base*.

    Keys ending with ``/`` are treated as directory markers and are
    always excluded.

    Parameters
    ----------
    keys : Iterable[str]
        Object keys, relative to the disk root.
    base : str
        Canonical directory path acting as the listing root. The
        empty string denotes the disk root.
    recursive : bool
        When ``True``, include files from all nested prefixes.

    Returns
    -------
    list[str]
        Sorted file keys under *base*.
    """
    prefix = f"{base}/" if base else ""
    results: list[str] = []
    for key in keys:
        # Skip directory markers and keys outside the listing root.
        if key.endswith("/") or not key.startswith(prefix):
            continue
        remainder = key[len(prefix):]
        if not remainder:
            continue
        if recursive or "/" not in remainder:
            results.append(key)
    results.sort()
    return results

def _directoryAncestors(key: str, base: str) -> Iterator[str]:
    """
    Yield every directory prefix implied by *key* down to *base*.

    Markers (keys ending with ``/``) name a directory directly, while
    file keys imply their parent chain.

    Parameters
    ----------
    key : str
        Object key, relative to the disk root.
    base : str
        Canonical directory path acting as the traversal floor.

    Yields
    ------
    str
        Directory paths between *key* and *base*, exclusive.
    """
    if key.endswith("/"):
        candidate = key.rstrip("/")
    else:
        candidate = key.rsplit("/", 1)[0] if "/" in key else ""

    # Walk the ancestor chain without ever crossing the listing root.
    while candidate and candidate != base:
        yield candidate
        candidate = candidate.rsplit("/", 1)[0] if "/" in candidate else ""

def deriveDirectories(
    keys: Iterable[str],
    base: str,
    *,
    recursive: bool,
) -> list[str]:
    """
    Derive the directory paths implied by object keys under *base*.

    Object stores have no physical directories: prefixes are inferred
    from the stored keys, and keys ending with ``/`` act as explicit
    directory markers.

    Parameters
    ----------
    keys : Iterable[str]
        Object keys, relative to the disk root.
    base : str
        Canonical directory path acting as the listing root. The
        empty string denotes the disk root.
    recursive : bool
        When ``True``, include all nested directories.

    Returns
    -------
    list[str]
        Sorted directory paths under *base*.
    """
    prefix = f"{base}/" if base else ""
    found: set[str] = set()
    for key in keys:
        if key.startswith(prefix):
            found.update(_directoryAncestors(key, base))

    results = [entry for entry in found if entry.startswith(prefix)]
    if not recursive:
        results = [
            entry for entry in results if "/" not in entry[len(prefix):]
        ]
    results.sort()
    return results
