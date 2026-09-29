from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock
from orionis.foundation.directory import Directory
from orionis.foundation.contracts.directory import IDirectory
from orionis.test import TestCase

def _make_directory(path_map: dict | None = None) -> Directory:
    """Create a Directory instance backed by a mock IApplication.

    Parameters
    ----------
    path_map : dict | None
        Value supplied for ``path_map``.

    Returns
    -------
    Directory
        Value produced by the helper.
    """
    mock_app = MagicMock()
    default_path = Path("/fake/root")

    def path_side_effect(key: str) -> Path:
        """Resolve the requested path using the configured map.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        Path
            Value produced by the helper.
        """
        if path_map:
            return path_map.get(key, default_path / key)
        return default_path / key

    mock_app.path.side_effect = path_side_effect
    return Directory(mock_app)

# ===========================================================================
# TestDirectory
# ===========================================================================

class TestDirectory(TestCase):

    def testImplementsIDirectory(self) -> None:
        """
        Assert that Directory implements the IDirectory contract.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        instance = _make_directory()
        self.assertIsInstance(instance, IDirectory)

    def testCanBeInstantiated(self) -> None:
        """
        Assert that Directory can be created with a mock application.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        instance = _make_directory()
        self.assertIsNotNone(instance)

    def testRootDelegatesToApp(self) -> None:
        """
        Assert that root() delegates to app.path('root').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"root": Path("/project")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.root(), Path("/project"))

    def testAppDelegatesToApp(self) -> None:
        """
        Assert that app() delegates to app.path('app').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"app": Path("/project/app")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.app(), Path("/project/app"))

    def testConsoleDelegatesToApp(self) -> None:
        """
        Assert that console() delegates to app.path('console').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"console": Path("/project/app/console")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.console(), Path("/project/app/console"))

    def testExceptionsDelegatesToApp(self) -> None:
        """
        Assert that exceptions() delegates to app.path('exceptions').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"exceptions": Path("/project/app/exceptions")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.exceptions(), Path("/project/app/exceptions"))

    def testHttpDelegatesToApp(self) -> None:
        """
        Assert that http() delegates to app.path('http').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"http": Path("/project/app/http")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.http(), Path("/project/app/http"))

    def testModelsDelegatesToApp(self) -> None:
        """
        Assert that models() delegates to app.path('models').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"models": Path("/project/app/models")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.models(), Path("/project/app/models"))

    def testProvidersDelegatesToApp(self) -> None:
        """
        Assert that providers() delegates to app.path('providers').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"providers": Path("/project/app/providers")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.providers(), Path("/project/app/providers"))

    def testNotificationsDelegatesToApp(self) -> None:
        """
        Assert that notifications() delegates to app.path('notifications').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"notifications": Path("/project/app/notifications")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.notifications(), Path("/project/app/notifications"))

    def testServicesDelegatesToApp(self) -> None:
        """
        Assert that services() delegates to app.path('services').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"services": Path("/project/app/services")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.services(), Path("/project/app/services"))

    def testJobsDelegatesToApp(self) -> None:
        """
        Assert that jobs() delegates to app.path('jobs').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"jobs": Path("/project/app/jobs")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.jobs(), Path("/project/app/jobs"))

    def testBootstrapDelegatesToApp(self) -> None:
        """
        Assert that bootstrap() delegates to app.path('bootstrap').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"bootstrap": Path("/project/bootstrap")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.bootstrap(), Path("/project/bootstrap"))

    def testConfigDelegatesToApp(self) -> None:
        """
        Assert that config() delegates to app.path('config').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"config": Path("/project/config")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.config(), Path("/project/config"))

    def testDatabaseDelegatesToApp(self) -> None:
        """
        Assert that database() delegates to app.path('database').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"database": Path("/project/database")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.database(), Path("/project/database"))

    def testResourcesDelegatesToApp(self) -> None:
        """
        Assert that resources() delegates to app.path('resources').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"resources": Path("/project/resources")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.resources(), Path("/project/resources"))

    def testRoutesDelegatesToApp(self) -> None:
        """
        Assert that routes() delegates to app.path('routes').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"routes": Path("/project/routes")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.routes(), Path("/project/routes"))

    def testStorageDelegatesToApp(self) -> None:
        """
        Assert that storage() delegates to app.path('storage').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"storage": Path("/project/storage")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.storage(), Path("/project/storage"))

    def testStoragePublicReturnsSubpathOfStorage(self) -> None:
        """
        Assert that storagePublic() returns storage/app/public.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"storage": Path("/project/storage")}
        instance = _make_directory(path_map)
        result = instance.storagePublic()
        self.assertEqual(result, Path("/project/storage/app/public"))

    def testTestsDelegatesToApp(self) -> None:
        """
        Assert that tests() delegates to app.path('tests').

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        path_map = {"tests": Path("/project/tests")}
        instance = _make_directory(path_map)
        self.assertEqual(instance.tests(), Path("/project/tests"))

    def testAllMethodsReturnPathInstances(self) -> None:
        """
        Assert that every public path method returns a Path instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        instance = _make_directory()
        methods = [
            "root", "app", "console", "exceptions", "http", "models",
            "providers", "notifications", "services", "jobs", "bootstrap",
            "config", "database", "resources", "routes", "storage",
            "storagePublic", "tests",
        ]
        for method in methods:
            result = getattr(instance, method)()
            self.assertIsInstance(result, Path, msg=f"{method}() should return Path")
