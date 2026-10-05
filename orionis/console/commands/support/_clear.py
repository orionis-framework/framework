from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

def clear_files(
    directory: Path,
    suffix: str | tuple[str, ...],
) -> tuple[int, list[str]]:
    """
    Remove files with the given suffixes from a dedicated directory.

    Parameters
    ----------
    directory : Path
        Directory searched recursively.
    suffix : str | tuple[str, ...]
        File suffix or suffixes to remove, including each leading dot.

    Returns
    -------
    tuple[int, list[str]]
        Number of files removed and filesystem errors encountered.
    """
    if not directory.is_dir():
        return 0, []

    errors: list[str] = []
    removed_count = 0
    cache_root = directory.resolve()
    for root, _, filenames in cache_root.walk(
        on_error=lambda error: errors.append(str(error)),
    ):
        for filename in filenames:
            if not filename.endswith(suffix):
                continue
            cache_file = root / filename
            try:
                cache_file.unlink()
            except FileNotFoundError:
                continue
            except OSError as error:
                errors.append(f"{cache_file}: {error}")
            else:
                removed_count += 1

    return removed_count, errors
