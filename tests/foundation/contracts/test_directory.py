from __future__ import annotations
import inspect
from abc import ABC
from inspect import isabstract
from orionis.foundation.contracts.directory import IDirectory
from orionis.test import TestCase

class _ConcreteDirectory(IDirectory):
    """Minimal concrete implementation used to verify the contract."""

    def _stub_path(self):
        """Build the path shared by the directory accessors.

        Returns
        -------
        object
            Value produced by the helper.
        """
        from pathlib import Path
        return Path("/stub")

    def root(self):
        """Return the root directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def app(self):
        """Return the application directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def console(self):
        """Return the console directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def exceptions(self):
        """Return the exceptions directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def http(self):
        """Return the HTTP directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def models(self):
        """Return the models directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def providers(self):
        """Return the providers directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def notifications(self):
        """Return the notifications directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def services(self):
        """Return the services directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def jobs(self):
        """Return the jobs directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def bootstrap(self):
        """Return the bootstrap directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def config(self):
        """Return the configuration directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def database(self):
        """Return the database directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def resources(self):
        """Return the resources directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def routes(self):
        """Return the routes directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def storage(self):
        """Return the storage directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def storagePublic(self):
        """Return the public storage path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()
    def tests(self):
        """Return the tests directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self._stub_path()

class _PartialDirectory(IDirectory):
    """Subclass implementing only root — intentionally incomplete."""

    def root(self):
        """Return the root directory path from the test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        from pathlib import Path
        return Path("/root")

# ===========================================================================
# TestIDirectoryContract
# ===========================================================================

class TestIDirectoryContract(TestCase):

    def testInheritsFromABC(self) -> None:
        """
        Assert that IDirectory inherits from ABC.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(issubclass(IDirectory, ABC))

    def testIsAbstractClass(self) -> None:
        """
        Assert that inspect.isabstract identifies IDirectory as abstract.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(isabstract(IDirectory))

    def testCannotInstantiateDirectly(self) -> None:
        """
        Assert that instantiating IDirectory directly raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            IDirectory()  # type: ignore[abstract]

    def testExpectedAbstractMethodsExist(self) -> None:
        """
        Assert that all expected path methods are abstract.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        expected = {
            "root", "app", "console", "exceptions", "http", "models",
            "providers", "notifications", "services", "jobs", "bootstrap",
            "config", "database", "resources", "routes", "storage",
            "storagePublic", "tests",
        }
        for method in expected:
            self.assertIn(
                method,
                IDirectory.__abstractmethods__,
                msg=f"'{method}' should be abstract",
            )

    def testAbstractMethodsSetHasExpectedCount(self) -> None:
        """
        Assert that __abstractmethods__ contains exactly 18 methods.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(len(IDirectory.__abstractmethods__), 18)

    def testPartialSubclassCannotBeInstantiated(self) -> None:
        """
        Assert that a subclass implementing only root cannot be instantiated.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            _PartialDirectory()  # type: ignore[abstract]

    def testConcreteSubclassCanBeInstantiated(self) -> None:
        """
        Assert that a fully implemented subclass can be created without error.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        instance = _ConcreteDirectory()
        self.assertIsInstance(instance, IDirectory)

    def testConcreteMethodsReturnPath(self) -> None:
        """
        Assert that each method in the concrete implementation returns a Path.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        from pathlib import Path
        instance = _ConcreteDirectory()
        methods = [
            "root", "app", "console", "exceptions", "http", "models",
            "providers", "notifications", "services", "jobs", "bootstrap",
            "config", "database", "resources", "routes", "storage",
            "storagePublic", "tests",
        ]
        for method in methods:
            result = getattr(instance, method)()
            self.assertIsInstance(result, Path, msg=f"{method}() should return Path")

    def testRootMethodSignature(self) -> None:
        """
        Assert that root method has a valid signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = inspect.signature(IDirectory.root)
        self.assertIn("self", sig.parameters)
