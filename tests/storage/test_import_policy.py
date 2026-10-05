import json
import subprocess
import sys
from orionis.storage.drivers.functions import (
    assert_binary_mode,
    derive_directories,
    filter_files,
    import_driver_dependency,
    resolve_download_target,
)
from orionis.storage.paths import normalize_file_path, normalize_path
from orionis.test import TestCase

class TestStorageImportPolicy(TestCase):
    """Exercise public imports in isolated interpreter processes."""

    def testColdPackageDoesNotLoadDriverImplementations(self) -> None:
        """Keep driver modules unloaded until an export is requested.

        Returns
        -------
        None
            Assertions validate the initial storage import state.
        """
        code = (
            "import json, sys\n"
            "import orionis.storage\n"
            "print(json.dumps([name for name in sys.modules "
            "if name.startswith('orionis.storage.drivers.')]))\n"
        )
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-B", "-c", code],
            capture_output=True,
            check=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(json.loads(completed.stdout), [])

    def testLocalExportDoesNotLoadCloudDrivers(self) -> None:
        """Load a selected local driver without importing cloud drivers.

        Returns
        -------
        None
            Assertions validate export identity and selective imports.
        """
        code = (
            "import json, sys\n"
            "from orionis.storage import LocalStorageDriver\n"
            "from orionis.storage.drivers.local import LocalStorageDriver as Direct\n"
            "print(json.dumps({'same': LocalStorageDriver is Direct, "
            "'loaded': [name for name in sys.modules "
            "if name.startswith('orionis.storage.drivers.')] }))\n"
        )
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-B", "-c", code],
            capture_output=True,
            check=True,
            text=True,
            timeout=15,
        )
        result = json.loads(completed.stdout)
        self.assertTrue(result["same"])
        self.assertEqual(result["loaded"], ["orionis.storage.drivers.local"])

    def testLegacyHelpersResolveToSnakeCaseImplementations(self) -> None:
        """Preserve helper imports while exposing snake_case definitions.

        Returns
        -------
        None
            Assertions validate compatibility names and function identities.
        """
        from orionis.storage import paths
        from orionis.storage.drivers import functions

        aliases = (
            (paths.normalizePath, normalize_path),
            (paths.normalizeFilePath, normalize_file_path),
            (functions.importDriverDependency, import_driver_dependency),
            (functions.assertBinaryMode, assert_binary_mode),
            (functions.resolveDownloadTarget, resolve_download_target),
            (functions.filterFiles, filter_files),
            (functions.deriveDirectories, derive_directories),
        )
        for old, new in aliases:
            self.assertIs(old, new)
            self.assertRegex(new.__name__, r"^[a-z][a-z0-9_]*$")
