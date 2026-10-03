from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from orionis.cache.cache_manager import CacheManager
from orionis.cache.exceptions import CacheStoreException
from orionis.test import TestCase

class _CacheApplication:
    """Supply a fixed cache configuration to the manager."""

    __slots__ = ("basePath",)

    def __init__(self, base_path: Path) -> None:
        """Store the base path for backend construction.

        Parameters
        ----------
        base_path : Path
            Directory used by file backends.
        """
        self.basePath = base_path

    def config(self, section: str) -> SimpleNamespace:
        """Return the cache configuration section.

        Parameters
        ----------
        section : str
            Configuration section name.

        Returns
        -------
        SimpleNamespace
            Fixed cache settings.
        """
        if section != "cache":
            error_msg = "Only the cache section is available."
            raise KeyError(error_msg)
        return SimpleNamespace(
            default="memory",
            prefix="",
            stores=SimpleNamespace(),
        )

class TestCacheManager(TestCase):
    """Verify named cache backend selection."""

    def testUnknownStoreDoesNotBecomeAFileStore(self) -> None:
        """Reject an unknown driver before creating a backend.

        Returns
        -------
        None
            Assertions verify explicit backend selection.
        """
        with TemporaryDirectory() as directory:
            manager = CacheManager(_CacheApplication(Path(directory)))
            with self.assertRaises(CacheStoreException):
                manager.store("unknown")

    def testDefaultRepositoryIsReused(self) -> None:
        """Reuse the resolved default repository on later lookups.

        Returns
        -------
        None
            Assertions verify repository identity.
        """
        with TemporaryDirectory() as directory:
            manager = CacheManager(_CacheApplication(Path(directory)))
            self.assertIs(manager.store(), manager.store())
