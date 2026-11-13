# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect artifact paths, source fingerprints, and rich type round trips."""

from contextlib import chdir
from enum import Enum
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.cache.file_based_cache import FileBasedCache
from orionis.cache.serializer import Serializer
from orionis.test import TestCase


class _ArtifactTypes:
    """Expose importable nested types for artifact reconstruction."""

    class Payload:
        """Represent a nested class stored as framework metadata."""

    class Kind(Enum):
        """Store a supported non-JSON enum value."""

        BINARY = b"artifact"


class TestArtifactRegressions(TestCase):
    """Validate artifact behavior using only disposable directories."""

    def testRejectsMalformedEnvelopeAndRebuilds(self) -> None:
        """Treat valid JSON with invalid artifact structure as a cache miss."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cache = FileBasedCache(root, "artifact")
            for payload in ([1], {"__meta__": "invalid"}, {"__meta__": [1]}):
                with self.subTest(payload=payload):
                    Serializer.dumpToFile(payload, root / "artifact")
                    self.assertIsNone(cache.get())
                    cache.save({"rebuilt": True})
                    self.assertEqual(cache.get(), {"rebuilt": True})
            cache.save({"valid": True})
            payload = Serializer.loadFromFile(root / "artifact")
            payload["__data__"] = [1]
            Serializer.dumpToFile(payload, root / "artifact")
            self.assertIsNone(cache.get())

    def testRejectsNamesOutsideCacheDirectory(self) -> None:
        """Reject traversal and path components before creating any directory."""
        with TemporaryDirectory() as directory:
            root = Path(directory) / "cache"
            for name in (
                "",
                ".",
                "..",
                "../outside",
                "sub/file",
                "sub\\file",
                "file:stream",
            ):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        FileBasedCache(root, name)
                    self.assertFalse(root.exists())

    def testRelativeDirectoryRetainsItsConstructionLocation(self) -> None:
        """Keep the selected cache directory stable after a cwd change."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first").mkdir()
            (root / "second").mkdir()
            with chdir(root / "first"):
                cache = FileBasedCache(Path("cache"), "artifact")
            with chdir(root / "second"):
                cache.save({"location": "first"})
                self.assertEqual(cache.get(), {"location": "first"})
            self.assertTrue((root / "first" / "cache" / "artifact").is_file())
            self.assertFalse((root / "second" / "cache").exists())

    def testFingerprintsSourceBeforeUnixEpoch(self) -> None:
        """Hash a real source file whose modification time predates 1970."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            os.utime(source, ns=(-1_000_000_000, -1_000_000_000))
            self.assertLess(source.stat().st_mtime_ns, 0)
            cache = FileBasedCache(root, "artifact", monitored_files=[source])
            cache.save({"value": 1})
            self.assertEqual(cache.get(), {"value": 1})

    def testRoundTripsNestedTypesAndTypedEnumValues(self) -> None:
        """Resolve nested classes and recursively decode enum values."""
        for value in (_ArtifactTypes.Payload, _ArtifactTypes.Kind.BINARY):
            with self.subTest(value=value):
                self.assertIs(Serializer.loads(Serializer.dumps(value)), value)
