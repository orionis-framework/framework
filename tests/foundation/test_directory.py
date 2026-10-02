from pathlib import Path
from orionis.foundation.contracts.directory import IDirectory
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.foundation.directory import Directory
from orionis.test import TestCase

def _method_name(key: str) -> str:
    """Convert a configured snake_case key to a camelCase method name.

    Parameters
    ----------
    key : str
        Configured application path key.

    Returns
    -------
    str
        CamelCase directory accessor name.
    """
    head, *tail = key.split("_")
    return head + "".join(part.capitalize() for part in tail)

class _StubApplication:
    """Provide deterministic paths for the directory service."""

    __slots__ = ("paths", "requested")

    def __init__(self) -> None:
        """Initialize the path map and request log.

        Returns
        -------
        None
            Store independent paths and an empty call log.
        """
        self.paths = {"root": Path("/project")}
        self.paths.update(
            {key: Path("/project") / key for key in CORE_APP_PATHS},
        )
        self.requested: list[str | None] = []

    def path(self, key: str | None = None) -> Path | dict[str, Path]:
        """Return and record a configured path or the complete mapping.

        Parameters
        ----------
        key : str or None, optional
            Requested path key, or None for all configured paths.

        Returns
        -------
        Path or dict[str, Path]
            Configured path or the caller-owned path mapping.
        """
        self.requested.append(key)
        return self.paths if key is None else self.paths[key]

class TestDirectory(TestCase):
    """Test the application directory accessors."""

    def testImplementsIDirectory(self) -> None:
        """Verify that Directory implements its public contract."""
        self.assertIsInstance(Directory(_StubApplication()), IDirectory)

    def testExposesEveryCorePath(self) -> None:
        """Verify that every CORE_APP_PATHS key has a matching accessor."""
        directory = Directory(_StubApplication())
        expected = {"root", *(_method_name(key) for key in CORE_APP_PATHS)}
        actual = {
            name
            for name in IDirectory.__abstractmethods__
            if not name.startswith("_")
        }
        self.assertEqual(actual, expected)
        for method_name in expected:
            self.assertIsInstance(getattr(directory, method_name)(), Path)

    def testAccessorsReturnTheConfiguredPaths(self) -> None:
        """Verify that accessors return values from application.path()."""
        app = _StubApplication()
        directory = Directory(app)
        self.assertEqual(directory.root(), app.paths["root"])
        for key in CORE_APP_PATHS:
            method_name = _method_name(key)
            self.assertEqual(getattr(directory, method_name)(), app.paths[key])

    def testResolvesAllConfiguredKeysDuringInitialization(self) -> None:
        """Retrieve the complete path mapping with one application call.

        Returns
        -------
        None
            Construction obtains all configured paths in one read.
        """
        app = _StubApplication()
        Directory(app)
        self.assertEqual(app.requested, [None])

    def testKeepsAnIndependentSnapshotOfThePathMapping(self) -> None:
        """Preserve cached paths after the application's mapping changes.

        Returns
        -------
        None
            Accessors retain their construction-time paths without further calls.
        """
        app = _StubApplication()
        original = app.paths["root"]
        directory = Directory(app)
        app.paths["root"] = Path("changed")
        self.assertIs(directory.root(), original)
        self.assertEqual(app.requested, [None])

    def testStoresTheSnapshotWithoutAnInstanceDictionary(self) -> None:
        """Keep the directory service state inside its declared slot.

        Returns
        -------
        None
            The concrete service does not allocate an instance dictionary.
        """
        self.assertFalse(hasattr(Directory(_StubApplication()), "__dict__"))
