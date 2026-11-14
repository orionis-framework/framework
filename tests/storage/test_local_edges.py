# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve local I/O failures and constrain directory traversal."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from unittest.mock import patch

from orionis.storage.drivers.local import LocalStorageDriver
from orionis.test import TestCase

if os.name == "nt":
    import _winapi

if TYPE_CHECKING:
    from collections.abc import Iterator


class TestLocalStorageEdges(TestCase):
    """Exercise local error boundaries against an isolated filesystem."""

    def setUp(self) -> None:
        """Create a disposable disk with real file and directory entries."""
        super().setUp()
        # Match the driver's canonical paths before installing targeted mocks.
        # Windows runners may expose the temporary directory through an 8.3 alias.
        self.parent = Path(self.enterContext(TemporaryDirectory())).resolve()
        self.root = self.parent / "root"
        self.driver = LocalStorageDriver(self.root)
        (self.root / "data").write_bytes(b"payload")
        (self.root / "nested").mkdir()

    async def testReadAndOpenPreservePermissionFailures(self) -> None:
        """Keep the original access error for reads and lazy stream opening."""
        original = Path.open
        failure = PermissionError("controlled read denial")
        target = self.root / "data"

        def denied(path: Path, *args: object, **kwargs: object) -> object:
            """Deny only the fixture file and delegate every unrelated open."""
            if path == target:
                raise failure
            return original(path, *args, **kwargs)

        with patch.object(Path, "open", denied):
            for action in ("read", "open", "stream"):
                with self.subTest(action=action):
                    with self.assertRaises(PermissionError) as caught:
                        if action == "read":
                            await self.driver.read("data")
                        elif action == "open":
                            async with self.driver.open("data"):
                                self.fail("A denied file was opened.")
                        else:
                            async for _ in self.driver.readStream("data"):
                                self.fail("A denied file yielded content.")
                    self.assertIs(caught.exception, failure)

    async def testMetadataPreservesUnexpectedStatErrors(self) -> None:
        """Distinguish a failed stat from a missing or non-file path."""
        original = Path.stat
        target = self.root / "data"
        for failure in (PermissionError("controlled denial"), OSError("device error")):

            def denied(
                path: Path,
                *args: object,
                selected_error: OSError = failure,
                **kwargs: object,
            ) -> os.stat_result:
                """Fail only the selected file stat with the original object."""
                if path == target:
                    raise selected_error
                return original(path, *args, **kwargs)

            with patch.object(Path, "stat", denied):
                for operation in (
                    self.driver.size,
                    self.driver.info,
                    self.driver.exists,
                ):
                    with self.subTest(
                        error=type(failure).__name__,
                        api=operation.__name__,
                    ):
                        with self.assertRaises(type(failure)) as caught:
                            await operation("data")
                        self.assertIs(caught.exception, failure)

    async def testDirectoryErrorsCannotBecomeEmptyOrMissingResults(self) -> None:
        """Propagate inaccessible directory metadata instead of returning absence."""
        original = Path.stat
        failure = PermissionError("controlled directory denial")
        target = self.root / "nested"

        def denied(path: Path, *args: object, **kwargs: object) -> os.stat_result:
            """Reject the selected directory metadata lookup."""
            if path == target:
                raise failure
            return original(path, *args, **kwargs)

        with patch.object(Path, "stat", denied):
            for operation in (
                self.driver.files,
                self.driver.directories,
                self.driver.directoryExists,
                self.driver.deleteDirectory,
            ):
                with self.subTest(api=operation.__name__):
                    with self.assertRaises(PermissionError) as caught:
                        await operation("nested")
                    self.assertIs(caught.exception, failure)

    async def testChildClassificationPreservesStatErrors(self) -> None:
        """Reject partial direct listings when a child's type cannot be read."""
        original = Path.stat
        failure = PermissionError("controlled child denial")
        target = self.root / "data"

        def denied(path: Path, *args: object, **kwargs: object) -> os.stat_result:
            """Fail only the child type check used by directory classification."""
            if path == target:
                raise failure
            return original(path, *args, **kwargs)

        with patch.object(Path, "stat", denied):
            for operation in (self.driver.files, self.driver.directories):
                with self.subTest(api=operation.__name__):
                    with self.assertRaises(PermissionError) as caught:
                        await operation()
                    self.assertIs(caught.exception, failure)

    async def testRecursiveScanPreservesTheOriginalError(self) -> None:
        """Propagate a failed child scan rather than returning partial results."""
        original = os.scandir
        failure = PermissionError("controlled scan denial")
        target = self.root / "nested"

        def denied(path: object) -> Iterator[os.DirEntry[str]]:
            """Deny the selected scan while retaining real traversal elsewhere."""
            if Path(path) == target:
                raise failure
            return original(path)

        with patch.object(os, "scandir", denied):
            for operation in (self.driver.files, self.driver.directories):
                with self.subTest(api=operation.__name__):
                    with self.assertRaises(PermissionError) as caught:
                        await operation(recursive=True)
                    self.assertIs(caught.exception, failure)

    async def testRecursiveListingNeverScansAnExternalDirectoryLink(self) -> None:
        """Prune a real directory link before it can traverse an outside tree."""
        outside = self.parent / "outside"
        outside.mkdir()
        (outside / "other-data").write_bytes(b"outside")
        link = self.root / "external"
        if os.name == "nt":
            _winapi.CreateJunction(str(outside), str(link))
        else:
            link.symlink_to(outside, target_is_directory=True)
        original = os.scandir
        visited = []

        def tracked(path: object) -> Iterator[os.DirEntry[str]]:
            """Record scans and reject traversal into the external fixture tree."""
            selected = Path(path)
            visited.append(selected)
            if selected.resolve().is_relative_to(outside):
                message = "The storage listing traversed an external directory."
                raise AssertionError(message)
            return original(path)

        try:
            with patch.object(os, "scandir", tracked):
                files = await self.driver.files(recursive=True)
                directories = await self.driver.directories(recursive=True)
            self.assertNotIn("external/other-data", files)
            self.assertNotIn("external", directories)
            self.assertNotIn(link, visited)
            self.assertIn("data", files)
            self.assertIn("nested", directories)
        finally:
            if os.name == "nt":
                link.rmdir()
            else:
                link.unlink()
