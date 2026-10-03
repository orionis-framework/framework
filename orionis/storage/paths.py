from __future__ import annotations
from orionis.storage.exceptions import StoragePathException

def normalize_path(path: str) -> str:
    """
    Normalize a storage path into a canonical root-relative form.

    Converts backslashes to forward slashes, removes empty and ``.``
    segments, resolves ``..`` segments logically, and rejects any path
    that would escape the disk root or contains forbidden characters.
    The returned path never has a leading or trailing slash; the empty
    string represents the disk root.

    Parameters
    ----------
    path : str
        Raw storage path as supplied by the caller.

    Returns
    -------
    str
        Canonical relative path using ``/`` as separator, or an empty
        string when the path resolves to the disk root.

    Raises
    ------
    StoragePathException
        If the path contains a null byte, a ``:`` character, or a
        ``..`` sequence that escapes the disk root.
    """
    # Reject null bytes early: they are never valid in storage paths.
    if "\x00" in path:
        error_msg = "Storage paths must not contain null bytes."
        raise StoragePathException(error_msg)

    # Walk the segments resolving relative components logically.
    segments: list[str] = []
    for segment in path.replace("\\", "/").split("/"):
        # Skip empty and current-directory segments.
        if segment in ("", "."):
            continue
        # Resolve parent references without touching the filesystem.
        if segment == "..":
            if not segments:
                error_msg = f"Storage path [{path}] escapes the disk root."
                raise StoragePathException(error_msg)
            segments.pop()
            continue
        # Block drive-letter and stream separators (e.g. 'C:', 'file:x').
        if ":" in segment:
            error_msg = (
                f"Storage path segment [{segment}] contains a forbidden "
                "character."
            )
            raise StoragePathException(error_msg)
        segments.append(segment)

    return "/".join(segments)

def normalize_file_path(path: str) -> str:
    """
    Normalize a storage path and require it to reference a file.

    Apply :func:`normalize_path` and additionally reject the empty
    result, since the disk root can never be treated as a file.

    Parameters
    ----------
    path : str
        Raw storage path as supplied by the caller.

    Returns
    -------
    str
        Canonical, non-empty relative path using ``/`` as separator.

    Raises
    ------
    StoragePathException
        If the path is invalid or resolves to the disk root.
    """
    # Reuse the shared normalization rules for consistency.
    normalized = normalize_path(path)

    # A file operation always requires a concrete target path.
    if not normalized:
        error_msg = "A non-empty file path is required for this operation."
        raise StoragePathException(error_msg)

    return normalized

_LEGACY_EXPORTS = {
    "normalizePath": normalize_path,
    "normalizeFilePath": normalize_file_path,
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a legacy path function name.

    Parameters
    ----------
    name : str
        Attribute requested from this module.

    Returns
    -------
    object
        Existing path function bound to the requested name.

    Raises
    ------
    AttributeError
        If the requested name is not a compatibility export.
    """
    try:
        value = _LEGACY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    globals()[name] = value
    return value
