# ruff: noqa: PT009, TC001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep runtime reflection annotations and intentionally deferred imports.
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.directory import Directory
from orionis.test import TestCase


class TestExample(TestCase):
    async def testAsyncMethod(
        self,
        app: IApplication,
        directory: Directory,
    ) -> None:
        """
        Verify that the application's root path matches the directory's root.

        Parameters
        ----------
        app : IApplication
            The application instance to test.
        directory : Directory
            The directory service to compare.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Assert that the root path from app and directory are equal.
        self.assertEqual(app.path("root"), directory.root())

    def testSyncMethod(
        self,
        app: IApplication,
        directory: Directory,
    ) -> None:
        """
        Verify that the application's root path matches the directory's root.

        Parameters
        ----------
        app : IApplication
            The application instance to test.
        directory : Directory
            The directory service to compare.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Assert that the root path from app and directory are equal.
        self.assertEqual(app.path("root"), directory.root())
