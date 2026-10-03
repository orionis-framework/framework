from __future__ import annotations
from hashlib import sha1
from pathlib import Path
from jinja2.bccache import Bucket, FileSystemBytecodeCache

# Extensions stripped before building the cache filename
_TEMPLATE_EXTENSIONS: tuple[str, ...] = (
    ".html", ".htm", ".jinja", ".jinja2", ".j2",
)

# Digest characters appended to the readable stem to keep keys unique
_DIGEST_LENGTH: int = 8

class OrionisBytecodeCache(FileSystemBytecodeCache):

    def getCacheKey(self, name: str, filename: str | None = None) -> str: # noqa: ARG002
        """
        Convert a template name into a human-readable cache key.

        Flattening separators and dropping the extension is a lossy
        transformation, so distinct templates such as ``mail/welcome.html``
        and ``mail/welcome.j2`` would share a single cache file.  A short
        digest of the untouched name is appended to keep the mapping
        injective while the stem stays readable.

        Parameters
        ----------
        name : str
            Template identifier (e.g. ``'users/index.html'``).
        filename : str or None, optional
            Absolute path on disk; unused here.

        Returns
        -------
        str
            Sanitised key used as the cache filename stem.
        """
        key: str = name.replace("/", ".").replace("\\", ".")
        for ext in _TEMPLATE_EXTENSIONS:
            if key.endswith(ext):
                key = key[: -len(ext)]
                break
        digest: str = sha1(
            name.encode("utf-8"), usedforsecurity=False,
        ).hexdigest()[:_DIGEST_LENGTH]
        return f"{key}.{digest}"

    # Expose the key builder through Jinja2's method name.
    get_cache_key = getCacheKey

    def _getCacheFilename(self, bucket: Bucket) -> str:
        """
        Return the absolute path to the cache file for *bucket*.

        Parameters
        ----------
        bucket : Bucket
            Jinja2 bucket whose ``key`` is the sanitised template name.

        Returns
        -------
        str
            Absolute path of the form
            ``<cache_dir>/<template_name>.<digest>.cache``.
        """
        return str(Path(self.directory) / f"{bucket.key}.cache")

    # Expose the filename builder through Jinja2's method name.
    _get_cache_filename = _getCacheFilename
