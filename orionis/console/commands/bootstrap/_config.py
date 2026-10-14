import hashlib
import json
from http import HTTPStatus
from http.client import HTTPException
from ntpath import isreserved
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from orionis.console.commands.bootstrap._paths import application_path, display_path

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

_TREE_URL = (
    "https://api.github.com/repos/orionis-framework/skeleton/"
    "git/trees/master?recursive=1"
)
_RAW_ROOT = "https://raw.githubusercontent.com/orionis-framework/skeleton/master/"
_TIMEOUT = 30
_SHA_LENGTH = 40

class ConfigBootstrapper:
    """Download and validate missing configuration before creating local files."""

    def __init__(self, app: IApplication) -> None:
        """
        Retain the application supplying the effective configuration path.

        Parameters
        ----------
        app : IApplication
            Application supplying effective configuration paths.

        Returns
        -------
        None
            Store the application for subsequent recovery operations.
        """
        # Retain the configured application without resolving paths early.
        self.app = app

    def bootstrap(self) -> list[tuple[str, str]]:
        """
        Restore the complete configuration subtree without replacing files.

        Returns
        -------
        list[tuple[str, str]]
            Created or existing resources, relative to the application root.

        Raises
        ------
        RuntimeError
            If GitHub cannot supply a complete, valid master configuration tree.
        OSError
            If a local path is unsafe or cannot be created.
        """
        # Resolve and validate resources before creating local files.
        root = application_path(self.app, "config")
        entries = self._entries()
        pending: dict[Path, bytes] = {}
        resources: list[tuple[Path, str]] = [(root, "tree")]
        for entry in entries:
            destination = root.joinpath(*PurePosixPath(entry["path"]).parts[1:])
            self._safeDestination(root, destination)
            self._validateLocalResource(destination, entry["type"])
            resources.append((destination, entry["type"]))
            if entry["type"] == "blob" and not destination.exists():
                pending[destination] = self._blob(entry)

        # All remote responses are validated before modifying the project.
        result: list[tuple[str, str]] = []
        for destination, kind in resources:
            self._safeDestination(root, destination)
            existed = self._createResource(destination, kind, pending)
            result.append((
                "EXISTS" if existed else "CREATED",
                display_path(self.app, destination),
            ))
        return result

    @staticmethod
    def _validateLocalResource(destination: Path, kind: str) -> None:
        """
        Reject a local resource whose type conflicts with the official tree.

        Parameters
        ----------
        destination : Path
            Local configuration resource to inspect.
        kind : str
            Expected Git tree entry type, either ``tree`` or ``blob``.

        Returns
        -------
        None
            Accept an absent resource or an existing resource of the expected type.
        """
        # Preserve existing files while rejecting incompatible filesystem types.
        if destination.exists() and (
            (kind == "tree" and not destination.is_dir())
            or (kind == "blob" and not destination.is_file())
        ):
            expected = "directory" if kind == "tree" else "regular file"
            error_msg = (
                f"Configuration resource '{destination}' is not a {expected}."
            )
            raise OSError(error_msg)

    @classmethod
    def _createResource(
        cls,
        destination: Path,
        kind: str,
        pending: dict[Path, bytes],
    ) -> bool:
        """
        Create one validated resource and report whether it existed.

        Parameters
        ----------
        destination : Path
            Local configuration file or directory to create.
        kind : str
            Expected Git tree entry type, either ``tree`` or ``blob``.
        pending : dict[Path, bytes]
            Validated contents indexed by missing file destinations.

        Returns
        -------
        bool
            Whether the resource already existed, including concurrent creation.
        """
        # Recheck the resource before creating it with exclusive file access.
        cls._validateLocalResource(destination, kind)
        existed = destination.exists()
        if kind == "tree":
            destination.mkdir(parents=True, exist_ok=True)
        elif not existed:
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                target = destination.open("xb")
            except FileExistsError:
                # A concurrent invocation may have created it since discovery.
                cls._validateLocalResource(destination, kind)
                return True
            try:
                with target:
                    target.write(pending[destination])
            except OSError:
                destination.unlink(missing_ok=True)
                raise
        return existed

    @classmethod
    def _blob(cls, entry: dict[str, Any]) -> bytes:
        """
        Download raw bytes and verify GitHub's size and Git object hash.

        Parameters
        ----------
        entry : dict[str, Any]
            Validated blob metadata from the official configuration tree.

        Returns
        -------
        bytes
            Unmodified file contents matching the advertised size and hash.
        """
        # Verify the Git blob identity before accepting downloaded content.
        content = cls._download(_RAW_ROOT + quote(entry["path"], safe="/"))
        digest = hashlib.sha1(
            f"blob {len(content)}\0".encode() + content,
            usedforsecurity=False,
        ).hexdigest()
        if len(content) != entry["size"] or digest != entry["sha"]:
            error_msg = (
                f"Invalid download for '{entry['path']}': blob verification failed."
            )
            raise RuntimeError(error_msg)
        return content

    @staticmethod
    def _download(url: str) -> bytes:
        """
        Read one successful GitHub response or identify the failed resource.

        Parameters
        ----------
        url : str
            HTTPS URL constructed from the official GitHub origins.

        Returns
        -------
        bytes
            Complete response body from an HTTP 200 response.
        """
        # Request the format expected by the tree or raw-content endpoint.
        request = Request(  # noqa: S310 - URLs are built from fixed HTTPS origins.
            url,
            headers={
                "Accept": (
                    "application/vnd.github+json"
                    if url == _TREE_URL
                    else "application/octet-stream"
                ),
                "User-Agent": "Orionis-Reactor-bootstrap",
            },
        )
        # Reject unsuccessful responses and identify transport failures.
        try:
            with urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310
                if response.status != HTTPStatus.OK:
                    error_msg = f"Cannot download '{url}': HTTP {response.status}."
                    raise RuntimeError(error_msg)
                return response.read()
        except (HTTPError, URLError, HTTPException, OSError) as error: # NOSONAR
            error_msg = f"Cannot download '{url}': {error}."
            raise RuntimeError(error_msg) from error

    @classmethod
    def _entries(cls) -> list[dict[str, Any]]: # NOSONAR
        """
        Validate the master tree and retain regular configuration entries.

        Returns
        -------
        list[dict[str, Any]]
            Valid configuration entries ordered with parent paths before children.
        """
        # Reject incomplete manifests before considering individual paths.
        try:
            manifest = json.loads(cls._download(_TREE_URL))
        except (ValueError, UnicodeError) as error: # NOSONAR
            error_msg = f"Invalid configuration tree from '{_TREE_URL}': {error}."
            raise RuntimeError(error_msg) from error
        if not isinstance(manifest, dict) or manifest.get("truncated") is not False:
            error_msg = "GitHub returned an incomplete configuration tree for master."
            raise RuntimeError(error_msg)
        tree = manifest.get("tree")
        if not isinstance(tree, list):
            error_msg = "GitHub returned an invalid configuration tree for master."
            raise RuntimeError(error_msg)  # noqa: TRY004 - Invalid remote response.
        entries: list[dict[str, Any]] = []
        seen: set[str] = set()
        # Validate portable paths, entry types, and blob metadata together.
        for entry in tree:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                error_msg = "GitHub returned an invalid configuration tree entry."
                # Report malformed remote data consistently with download errors.
                raise RuntimeError(error_msg)  # noqa: TRY004
            path = entry["path"]
            if not path.startswith("config/"):
                continue
            parts = path.split("/")
            if (
                any(part in {"", ".", ".."} for part in parts)
                or any(isreserved(part) for part in parts)
                or any(character in path for character in "\\:\0")
                or path.casefold() in seen
                or entry.get("type") not in {"tree", "blob"}
                or entry.get("mode") not in {"040000", "100644", "100755"}
            ):
                error_msg = f"Unsafe remote configuration path '{path}'."
                raise RuntimeError(error_msg)
            if entry["type"] == "blob" and (
                not isinstance(entry.get("size"), int)
                or entry["size"] < 0
                or not isinstance(entry.get("sha"), str)
                or len(entry["sha"]) != _SHA_LENGTH
                or any(
                    character not in "0123456789abcdef" for character in entry["sha"]
                )
            ):
                error_msg = (
                    f"Invalid metadata for remote configuration file '{path}'."
                )
                raise RuntimeError(error_msg)
            seen.add(path.casefold())
            entries.append(entry)
        if not entries:
            error_msg = "The official master branch contains no configuration files."
            raise RuntimeError(error_msg)
        return sorted(
            entries,
            key=cls._entryOrder,
        )

    @staticmethod
    def _entryOrder(entry: dict[str, Any]) -> tuple[int, str]:
        """
        Order configuration entries by depth and then by path.

        Parameters
        ----------
        entry : dict[str, Any]
            Validated configuration tree entry containing its repository path.

        Returns
        -------
        tuple[int, str]
            Path depth and repository path used for deterministic creation order.
        """
        # Place parent directories before their children.
        return entry["path"].count("/"), entry["path"]

    @staticmethod
    def _safeDestination(root: Path, destination: Path) -> None:
        """
        Reject links and traversal before writing any configuration resource.

        Parameters
        ----------
        root : Path
            Effective configuration root containing all permitted destinations.
        destination : Path
            Local resource path to validate before writing.

        Returns
        -------
        None
            Accept a destination contained within the root and free of links.
        """
        # Inspect every ancestor to prevent writes through links or junctions.
        current = destination
        while True:
            if current.is_symlink() or current.is_junction():
                error_msg = (
                    f"Unsafe configuration path '{current}': "
                    "symbolic links are not supported."
                )
                raise OSError(error_msg)
            if current != destination and current.exists() and not current.is_dir():
                error_msg = f"Configuration parent '{current}' is not a directory."
                raise OSError(error_msg)
            if current == root:
                break
            current = current.parent
        if not destination.resolve().is_relative_to(root.resolve()):
            error_msg = f"Configuration path '{destination}' escapes '{root}'."
            raise OSError(error_msg)
