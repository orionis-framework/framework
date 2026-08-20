from __future__ import annotations
import tempfile
from pathlib import Path
from orionis.storage.drivers.functions import (
    assertBinaryMode,
    deriveDirectories,
    filterFiles,
    importDriverDependency,
    resolveDownloadTarget,
)
from orionis.storage.exceptions import (
    MissingStorageDependencyException,
    UnsupportedStorageOperationException,
)
from orionis.test import TestCase

# Shared key fixture emulating an object-store listing.
_KEYS: list[str] = [
    "docs/a.txt",
    "docs/sub/b.txt",
    "docs/sub/",
    "other/c.txt",
    "root.txt",
]

class TestDriverFunctions(TestCase):

    def testImportDriverDependencyRaisesWithInstallHint(self) -> None:
        """
        Raise a descriptive error for a missing optional package.

        Validates that the exception names the package and both
        installation commands.
        """
        with self.assertRaises(MissingStorageDependencyException) as ctx:
            importDriverDependency(
                "orionis_missing_sdk_xyz", "fake-sdk", "faker",
            )
        message = str(ctx.exception)
        self.assertIn("pip install fake-sdk", message)
        self.assertIn("orionis[faker]", message)

    def testAssertBinaryModeAcceptsBinaryModes(self) -> None:
        """
        Accept every supported binary mode without raising.

        Validates the mode whitelist shared by cloud drivers.
        """
        for mode in ("rb", "wb", "ab", "rb+", "wb+", "ab+"):
            assertBinaryMode(mode)

    def testAssertBinaryModeRejectsTextModes(self) -> None:
        """
        Reject text-oriented stream modes.

        Validates the failure contract of the shared mode check.
        """
        with self.assertRaises(UnsupportedStorageOperationException):
            assertBinaryMode("r")

    def testFilterFilesExcludesMarkersAndScopes(self) -> None:
        """
        Select only file keys under the requested base prefix.

        Validates marker exclusion and recursive scoping.
        """
        self.assertEqual(
            filterFiles(_KEYS, "docs", recursive=False),
            ["docs/a.txt"],
        )
        self.assertEqual(
            filterFiles(_KEYS, "docs", recursive=True),
            ["docs/a.txt", "docs/sub/b.txt"],
        )
        self.assertEqual(
            filterFiles(_KEYS, "", recursive=False),
            ["root.txt"],
        )

    def testDeriveDirectoriesFromKeysAndMarkers(self) -> None:
        """
        Infer directory prefixes from keys and explicit markers.

        Validates direct and recursive derivation at several bases.
        """
        self.assertEqual(
            deriveDirectories(_KEYS, "docs", recursive=False),
            ["docs/sub"],
        )
        self.assertEqual(
            deriveDirectories(_KEYS, "", recursive=False),
            ["docs", "other"],
        )
        self.assertEqual(
            deriveDirectories(_KEYS, "", recursive=True),
            ["docs", "docs/sub", "other"],
        )

    def testResolveDownloadTargetHandlesDirectories(self) -> None:
        """
        Keep the remote file name when the destination is a folder.

        Validates directory targets and parent creation for file
        targets.
        """
        with tempfile.TemporaryDirectory() as tmp:
            into_dir = resolveDownloadTarget("docs/report.pdf", tmp)
            self.assertEqual(into_dir, Path(tmp) / "report.pdf")

            explicit = resolveDownloadTarget(
                "docs/report.pdf", Path(tmp) / "nested" / "out.pdf",
            )
            self.assertEqual(explicit.name, "out.pdf")
            self.assertTrue(explicit.parent.is_dir())
