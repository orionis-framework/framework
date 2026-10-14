from __future__ import annotations
import hashlib
import json
import unittest
from http.client import IncompleteRead
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import patch
from urllib.error import URLError
from orionis.console.commands.bootstrap._config import (
    _RAW_ROOT,
    _TREE_URL,
    ConfigBootstrapper,
)

if TYPE_CHECKING:
    from urllib.request import Request

class _Response(BytesIO):
    """Provide the response interface consumed by urllib's context manager."""

    status = 200

def _file(path: str, content: bytes) -> dict[str, object]:
    """Construct GitHub's exact blob metadata for a fixture's byte content.

    Parameters
    ----------
    path : str
        Repository path advertised by the fixture.
    content : bytes
        Exact raw file contents to describe.

    Returns
    -------
    dict[str, object]
        Git blob metadata describing the supplied fixture bytes.
    """
    # Describe fixture bytes using the Git blob hashing format.
    return {
        "path": path,
        "type": "blob",
        "mode": "100644",
        "size": len(content),
        "sha": hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest(),
    }

def _tree(entries: list[dict[str, object]]) -> bytes:
    """Serialize a complete GitHub tree response.

    Parameters
    ----------
    entries : list[dict[str, object]]
        Repository entries to include in the complete manifest.

    Returns
    -------
    bytes
        Encoded JSON manifest with the supplied entries.
    """
    # Advertise a complete tree without making network requests.
    return json.dumps({"truncated": False, "tree": entries}).encode()

class TestConfigBootstrapper(unittest.TestCase):
    """Exercise master downloads, idempotence, errors, and destination security."""

    def setUp(self) -> None:
        """Create a disposable slim application and an isolated HTTP recorder.

        Returns
        -------
        None
            Initialize a disposable application and mocked HTTP responses.
        """
        # Isolate filesystem changes and intercept all GitHub requests.
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.app = SimpleNamespace(basePath=self.base, path=self._defaultPath)
        self.urls: list[str] = []
        self.responses: dict[str, bytes | Exception] = {}
        self.remote = patch(
            "orionis.console.commands.bootstrap._config.urlopen",
            side_effect=self._request,
        )
        self.remote.start()
        self.addCleanup(self.remote.stop)

    @staticmethod
    def _defaultPath(_key: str) -> None:
        """Keep the application double on its default configuration path.

        Parameters
        ----------
        _key : str
            Requested application path key.

        Returns
        -------
        None
            Defer path resolution to the framework's defaults.
        """
        # Represent an application with no loaded path overrides.
        return

    def _request(self, request: Request, *, timeout: int) -> _Response:
        """Respond only to registered fixtures while recording exact URLs.

        Parameters
        ----------
        request : Request
            Outgoing GitHub request supplied by the bootstrapper.
        timeout : int
            Configured connection and response timeout in seconds.

        Returns
        -------
        _Response
            In-memory response containing the registered fixture bytes.
        """
        # Serve only explicitly registered responses and record each URL.
        self.assertEqual(timeout, 30)
        self.urls.append(request.full_url)
        response = self.responses[request.full_url]
        if isinstance(response, Exception):
            raise response
        return _Response(response)

    def _fixtures(self, files: dict[str, bytes]) -> None:
        """Advertise fixtures and add their raw-content download responses.

        Parameters
        ----------
        files : dict[str, bytes]
            Repository paths mapped to their exact raw file contents.

        Returns
        -------
        None
            Register the manifest and raw-content responses for the fixtures.
        """
        # Use the same fixture bytes for metadata and response bodies.
        entries = [_file(path, content) for path, content in files.items()]
        self.responses[_TREE_URL] = _tree(entries)
        for path, content in files.items():
            self.responses[_RAW_ROOT + path] = content

    def test_downloads_only_config_from_master_and_preserves_byte_content(self) -> None:
        """Restore nested configuration and exclude unrelated files.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Include unrelated repository entries to verify subtree filtering.
        files = {
            "config/app.py": b"# Official\r\nAPP = 'orionis'\r\n",
            "config/cache/drivers.json": b'{"enabled":true}\n',
            "config/empty.txt": b"",
            "README.md": b"must not be downloaded",
            "app/controllers/example.py": b"must not be downloaded",
        }
        self._fixtures(files)
        manifest = json.loads(self.responses[_TREE_URL])
        manifest["tree"].append(
            {"path": "config/cache", "type": "tree", "mode": "040000"},
        )
        self.responses[_TREE_URL] = json.dumps(manifest).encode()

        result = ConfigBootstrapper(self.app).bootstrap()

        self.assertEqual(self.urls[0], _TREE_URL)
        self.assertTrue(all("/master/" in url for url in self.urls[1:]))
        self.assertEqual(len(self.urls), 4)
        self.assertIn(("CREATED", "config/cache"), result)
        for path, content in files.items():
            if path.startswith("config/"):
                self.assertEqual((self.base / path).read_bytes(), content)
            else:
                self.assertFalse((self.base / path).exists())
        self.assertEqual({path.name for path in self.base.iterdir()}, {"config"})

    def test_preserves_existing_files_and_second_run_only_lists_tree(self) -> None:
        """Keep developer changes and avoid redundant blob requests or writes.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Track content and timestamps across repeated recovery runs.
        self._fixtures(
            {"config/app.py": b"official", "config/database.py": b"database"},
        )
        config = self.base / "config"
        config.mkdir()
        existing = config / "app.py"
        existing.write_bytes(b"custom")
        original_mtime = existing.stat().st_mtime_ns

        first = ConfigBootstrapper(self.app).bootstrap()
        self.assertNotIn(_RAW_ROOT + "config/app.py", self.urls)
        self.assertIn(("EXISTS", "config/app.py"), first)
        created_mtime = (config / "database.py").stat().st_mtime_ns
        self.urls.clear()
        second = ConfigBootstrapper(self.app).bootstrap()

        self.assertEqual(self.urls, [_TREE_URL])
        self.assertTrue(all(status == "EXISTS" for status, _ in second))
        self.assertEqual(existing.read_bytes(), b"custom")
        self.assertEqual(existing.stat().st_mtime_ns, original_mtime)
        self.assertEqual((config / "database.py").stat().st_mtime_ns, created_mtime)

    def test_respects_effective_custom_config_path(self) -> None:
        """Use the application's loaded path instead of hardcoding config/.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Override the effective directory without changing the project root.
        self._fixtures({"config/app.py": b"custom destination"})
        destination = self.base / "settings" / "runtime"

        def custom_path(key: str) -> Path | None:
            """Resolve the overridden configuration path for the test application.

            Parameters
            ----------
            key : str
                Requested application path key.

            Returns
            -------
            Path | None
                Custom configuration destination, or no override for other keys.
            """
            # Override only the configuration directory.
            return destination if key == "config" else None

        self.app.path = custom_path

        result = ConfigBootstrapper(self.app).bootstrap()

        self.assertEqual((destination / "app.py").read_bytes(), b"custom destination")
        self.assertIn(("CREATED", "settings/runtime/app.py"), result)
        self.assertFalse((self.base / "config").exists())

    def test_resolves_relative_custom_path_against_application_base(self) -> None:
        """Interpret relative effective paths from the project root.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Leave path resolution relative to the application base.
        self._fixtures({"config/app.py": b"relative destination"})

        def custom_path(_key: str) -> Path:
            """Return the relative configuration directory for the test application.

            Parameters
            ----------
            _key : str
                Requested application path key.

            Returns
            -------
            Path
                Relative directory to resolve against the application root.
            """
            # Exercise relative effective paths without resolving them early.
            return Path("settings")

        self.app.path = custom_path

        ConfigBootstrapper(self.app).bootstrap()

        self.assertTrue((self.base / "settings" / "app.py").is_file())

    def test_network_failure_keeps_project_unchanged(self) -> None:
        """Preserve the project when the master tree cannot be downloaded.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Fail the manifest request before creating local resources.
        error_msg = "offline"
        self.responses[_TREE_URL] = URLError(error_msg)

        with self.assertRaisesRegex(RuntimeError, "offline"): # NOSONAR
            ConfigBootstrapper(self.app).bootstrap()

        self.assertEqual(list(self.base.iterdir()), [])

    def test_blob_failure_does_not_write_previously_downloaded_files(self) -> None:
        """Stage all remote responses before making filesystem changes.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Fail a later download after an earlier file has been staged.
        self._fixtures({"config/app.py": b"app", "config/database.py": b"database"})
        error_msg = "missing blob"
        self.responses[_RAW_ROOT + "config/database.py"] = URLError(error_msg)

        with self.assertRaisesRegex(RuntimeError, "database.py"): # NOSONAR
            ConfigBootstrapper(self.app).bootstrap()

        self.assertEqual(list(self.base.iterdir()), [])

    def test_invalid_http_status_is_an_error(self) -> None:
        """Reject HTTP responses even when a response body is available.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Return a body with a failing HTTP status to verify status checks.
        response = _Response(b"not found")
        response.status = 404
        with patch( # NOSONAR
            "orionis.console.commands.bootstrap._config.urlopen", return_value=response,
        ), self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            ConfigBootstrapper(self.app).bootstrap()
        self.assertFalse((self.base / "config").exists())

    def test_incorrect_blob_bytes_are_rejected(self) -> None:
        """Check size and Git object digest to reject corrupt success responses.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Keep manifest metadata valid while corrupting raw response bytes.
        self._fixtures({"config/app.py": b"valid"})
        self.responses[_RAW_ROOT + "config/app.py"] = b"wrong"

        with self.assertRaisesRegex(RuntimeError, "verification failed"): # NOSONAR
            ConfigBootstrapper(self.app).bootstrap()

        self.assertFalse((self.base / "config").exists())

    def test_interrupted_response_identifies_failed_resource(self) -> None:
        """Translate interrupted HTTP body reads into a handled download error.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Interrupt the HTTP body after response handling starts.
        error_msg = b"partial"
        with ( # NOSONAR
            patch(
                "orionis.console.commands.bootstrap._config.urlopen",
                side_effect=IncompleteRead(error_msg, 100),
            ),
            self.assertRaisesRegex(RuntimeError, "Cannot download.*master"),
        ):
            ConfigBootstrapper(self.app).bootstrap()
        self.assertEqual(list(self.base.iterdir()), [])

    def test_invalid_blob_metadata_is_rejected_before_downloads(self) -> None:
        """Require valid sizes and Git hashes before requesting any file bytes.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise invalid metadata fields before downloading any blobs.
        for invalid in [
            {"size": -1}, {"size": "3"}, {"sha": "invalid"}, {"sha": "z" * 40},
        ]:
            with self.subTest(metadata=invalid):
                entry = _file("config/app.py", b"app")
                entry.update(invalid)
                self.responses[_TREE_URL] = _tree([entry])
                with self.assertRaisesRegex(RuntimeError, "Invalid metadata"): # NOSONAR
                    ConfigBootstrapper(self.app).bootstrap()
        self.assertEqual(self.urls, [_TREE_URL] * 4)
        self.assertEqual(list(self.base.iterdir()), [])

    def test_invalid_tree_responses_are_rejected(self) -> None:
        """Handle malformed, missing and truncated manifests explicitly.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Reject invalid manifests before making filesystem changes.
        manifests = [
            b"invalid json",
            b"[]",
            b"{}",
            b'{"truncated":true,"tree":[]}',
            _tree([]),
        ]
        for manifest in manifests:
            with self.subTest(manifest=manifest):
                self.responses[_TREE_URL] = manifest
                with self.assertRaises(RuntimeError): # NOSONAR
                    ConfigBootstrapper(self.app).bootstrap()
        self.assertFalse((self.base / "config").exists())

    def test_remote_traversal_and_links_are_rejected_before_writes(self) -> None:
        """Validate portable paths and refuse remote symlinks or submodules.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise traversal paths and Git entry types that can escape config.
        unsafe = [
            "config/../escape.py",
            "config/cache/../../escape.py",
            "config//escape.py",
            "config/./escape.py",
            "config/C:/escape.py",
            "config/cache\\escape.py",
            "config/escape\0.py",
        ]
        for path in unsafe:
            with self.subTest(path=path):
                self.responses[_TREE_URL] = _tree([_file(path, b"content")])
                with self.assertRaisesRegex(RuntimeError, "Unsafe remote"): # NOSONAR
                    ConfigBootstrapper(self.app).bootstrap()
        for kind, mode in [("blob", "120000"), ("commit", "160000")]:
            with self.subTest(mode=mode):
                entry = _file("config/linked", b"outside")
                entry.update(type=kind, mode=mode)
                self.responses[_TREE_URL] = _tree([entry])
                with self.assertRaisesRegex(RuntimeError, "Unsafe remote"): # NOSONAR
                    ConfigBootstrapper(self.app).bootstrap()
        self.assertEqual(list(self.base.iterdir()), [])

    def test_duplicate_remote_paths_are_rejected(self) -> None:
        """Reject duplicate and platform-dependent case collisions.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Compare paths case-insensitively to model portable destinations.
        self.responses[_TREE_URL] = _tree(
            [
                _file("config/app.py", b"first"),
                _file("config/APP.py", b"second"),
            ],
        )

        with self.assertRaisesRegex(RuntimeError, "Unsafe remote"): # NOSONAR
            ConfigBootstrapper(self.app).bootstrap()

        self.assertFalse((self.base / "config").exists())

    def test_existing_directory_cannot_stand_in_for_a_config_file(self) -> None:
        """Report a conflicting local resource instead of announcing success.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Place a directory where the manifest requires a regular file.
        self._fixtures({"config/app.py": b"official"})
        (self.base / "config" / "app.py").mkdir(parents=True)

        with self.assertRaisesRegex(OSError, "not a regular file"): # NOSONAR
            ConfigBootstrapper(self.app).bootstrap()

        self.assertTrue((self.base / "config" / "app.py").is_dir())

    def test_local_directory_link_cannot_escape_config(self) -> None:
        """Protect the config boundary from preexisting links to outside paths.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Link a nested destination outside the effective configuration root.
        self._fixtures({"config/nested/app.py": b"official"})
        outside = self.base / "outside"
        outside.mkdir()
        config = self.base / "config"
        config.mkdir()
        link = config / "nested"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Creating symlinks is unavailable: {error}")

        with self.assertRaisesRegex(OSError, "Unsafe configuration path"): # NOSONAR
            ConfigBootstrapper(self.app).bootstrap()

        self.assertEqual(list(outside.iterdir()), [])

if __name__ == "__main__":
    # Run this module directly with the standard unittest runner.
    unittest.main()
