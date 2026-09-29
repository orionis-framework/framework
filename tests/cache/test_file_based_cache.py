from __future__ import annotations
import tempfile
import time
from pathlib import Path
from orionis.cache.file_based_cache import FileBasedCache
from orionis.cache.serializer import Serializer
from orionis.test import TestCase

class TestFileBasedCache(TestCase):

    def setUp(self) -> None:
        """Create an isolated temporary directory before each test.

        Provides a fresh, writable directory so every test operates on
        its own filesystem state without side effects.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._cache_path = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        """Remove the temporary directory after each test.

        Ensures all files created during the test are cleaned up
        regardless of whether the test passed or failed.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._tmpdir.cleanup()

    def _make(
        self,
        filename: str = "cache.bin",
        monitored_files: list[Path] | None = None,
        monitored_dirs: list[Path] | None = None,
    ) -> FileBasedCache:
        """
        Construct a FileBasedCache instance rooted in the temp directory.

        Parameters
        ----------
        filename : str
            Cache file name, default ``"cache.bin"``.
        monitored_files : list[Path] or None
            Explicit files to monitor for hash invalidation.
        monitored_dirs : list[Path] or None
            Directories whose Python files are monitored.

        Returns
        -------
        FileBasedCache
            A fresh instance backed by the test's temporary directory.
        """
        return FileBasedCache(
            path=self._cache_path,
            filename=filename,
            monitored_files=monitored_files,
            monitored_dirs=monitored_dirs,
        )

    def testInitRequiresPathInstance(self) -> None:
        """Raise TypeError when path is not a Path instance.

        Validates that passing a plain string instead of a Path object
        is rejected immediately during construction.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            FileBasedCache(
                path="/not/a/path",  # type: ignore[arg-type]
                filename="cache.bin",
            )

    def testInitCreatesDirectoryIfMissing(self) -> None:
        """Create the cache directory hierarchy during initialization.

        Validates that FileBasedCache.mkdir(parents=True) is called so
        that a multi-level path that does not yet exist is created.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        nested = self._cache_path / "deep" / "nested"
        FileBasedCache(path=nested, filename="cache.bin")
        self.assertTrue(nested.is_dir())

    def testSaveRequiresDictData(self) -> None:
        """Raise TypeError when the data argument to save is not a dict.

        Validates that non-dict arguments are rejected before any I/O
        is performed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        with self.assertRaises(TypeError):
            cache.save("not a dict")  # type: ignore[arg-type]

    def testSaveRequiresDictDataInt(self) -> None:
        """Raise TypeError when an integer is passed to save.

        Validates that the type guard inside save covers numeric types.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        with self.assertRaises(TypeError):
            cache.save(42)  # type: ignore[arg-type]

    def testGetReturnsNoneWhenNoCacheFile(self) -> None:
        """Return None from get when no cache file has been written yet.

        Validates that get() handles a missing cache file gracefully
        without raising an exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        self.assertIsNone(cache.get())

    def testSaveAndGetRoundtrip(self) -> None:
        """Persist data and retrieve it intact within the same session.

        Validates that data written via save() is returned unchanged by
        a subsequent get() call on the same instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        data = {"key": "value", "count": 42, "flag": True}
        cache.save(data)
        result = cache.get()
        self.assertEqual(result, data)

    def testSaveReturnsVersionAndHash(self) -> None:
        """Return a (version, hash) tuple from save.

        Validates that the return value contains the expected integer
        CACHE_VERSION constant and a non-empty hexadecimal hash string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        version, sourceshash = cache.save({"a": 1})
        self.assertEqual(version, FileBasedCache.CACHE_VERSION)
        self.assertIsInstance(sourceshash, str)
        self.assertGreater(len(sourceshash), 0)

    def testSaveAndGetNestedData(self) -> None:
        """Preserve nested structures through a save/get cycle.

        Validates that deeply nested dicts and lists are returned
        without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        data = {"routes": [{"path": "/", "handler": "index"}], "meta": {"v": 2}}
        cache.save(data)
        self.assertEqual(cache.get(), data)

    def testSaveAndGetEmptyDict(self) -> None:
        """Persist and retrieve an empty dict.

        Validates that an empty mapping is a valid payload and is
        returned intact by get().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        cache.save({})
        self.assertEqual(cache.get(), {})

    def testSaveDifferentDataOverwritesCache(self) -> None:
        """Overwrite cached data when new data differs from the stored copy.

        Validates that a second save with different data causes get() to
        return the new data.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        cache.save({"v": 1})
        cache.save({"v": 2})
        self.assertEqual(cache.get(), {"v": 2})

    def testSaveIdempotentForIdenticalData(self) -> None:
        """Return the same version and hash on consecutive saves of equal data.

        Validates that the short-circuit optimisation triggers when the
        data, version, and hash are all identical.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        data = {"stable": True, "count": 7}
        v1, h1 = cache.save(data)
        v2, h2 = cache.save(data)
        self.assertEqual(v1, v2)
        self.assertEqual(h1, h2)
        self.assertEqual(cache.get(), data)

    def testClearReturnsTrueWhenFileExists(self) -> None:
        """Return True after successfully removing an existing cache file.

        Validates that clear() deletes the file and reports success.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        cache.save({"x": 1})
        self.assertTrue(cache.clear())
        self.assertIsNone(cache.get())

    def testClearReturnsFalseWhenNoFile(self) -> None:
        """Return False when the cache file does not exist.

        Validates that clear() returns False without raising when called
        on a cache with no persisted file.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        self.assertFalse(cache.clear())

    def testClearTwiceReturnsFalseOnSecondCall(self) -> None:
        """Return False on a second clear when the file was already removed.

        Validates that calling clear() twice is safe and idempotent.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cache = self._make()
        cache.save({"x": 1})
        self.assertTrue(cache.clear())
        self.assertFalse(cache.clear())

    def testGetReturnsNoneOnVersionMismatch(self) -> None:
        """Return None when the cache file contains a mismatched version.

        Validates that get() ignores cache entries that do not match the
        current CACHE_VERSION constant.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        filename = "v_cache.bin"
        cache = self._make(filename=filename)
        cache.save({"data": "original"})

        cache_file = self._cache_path / filename
        bad_payload = {
            "__meta__": {
                "version": 999,
                "generatedAt": 0,
                "sourcesHash": "",
            },
            "__data__": {"data": "original"},
        }
        Serializer.dumpToFile(bad_payload, cache_file)

        fresh = FileBasedCache(path=self._cache_path, filename=filename)
        self.assertIsNone(fresh.get())

    def testGetReturnsNoneOnMissingMeta(self) -> None:
        """Return None when the cache payload lacks the __meta__ section.

        Validates that get() handles a structurally corrupted cache file
        that is missing the required metadata key.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        filename = "meta_cache.bin"
        cache_file = self._cache_path / filename
        Serializer.dumpToFile({"__data__": {"key": "val"}}, cache_file)

        fresh = FileBasedCache(path=self._cache_path, filename=filename)
        self.assertIsNone(fresh.get())

    def testGetReturnsNoneOnHashMismatch(self) -> None:
        """Return None when a monitored file changes after the last save.

        Validates that modifying a monitored source file causes get() to
        detect the hash mismatch and invalidate the cached entry.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        monitored = self._cache_path / "source.py"
        monitored.write_text("x = 1\n", encoding="utf-8")

        filename = "hash_cache.bin"
        cache = FileBasedCache(
            path=self._cache_path,
            filename=filename,
            monitored_files=[monitored],
        )
        cache.save({"payload": True})

        # Small sleep then write different-length content to guarantee
        # both mtime_ns and st_size differ from the original.
        time.sleep(0.02)
        monitored.write_text("x = 100\n", encoding="utf-8")

        # A fresh instance starts with __lasthashcheck = 0 so the hash
        # interval cache is bypassed and the new hash is computed.
        fresh = FileBasedCache(
            path=self._cache_path,
            filename=filename,
            monitored_files=[monitored],
        )
        self.assertIsNone(fresh.get())

    def testGetValidWhenMonitoredFileUnchanged(self) -> None:
        """Return cached data when the monitored file has not changed.

        Validates that get() returns the stored data when the hash of
        monitored sources remains identical between save and get.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        monitored = self._cache_path / "stable.py"
        monitored.write_text("y = 42\n", encoding="utf-8")

        cache = FileBasedCache(
            path=self._cache_path,
            filename="stable_cache.bin",
            monitored_files=[monitored],
        )
        data = {"stable": True}
        cache.save(data)
        self.assertEqual(cache.get(), data)

    def testSaveAndGetWithMonitoredDirectory(self) -> None:
        """Persist and retrieve data when a directory is monitored.

        Validates that save() and get() work correctly when the cache
        monitors a directory of Python source files.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        subdir = self._cache_path / "pkg"
        subdir.mkdir()
        (subdir / "module.py").write_text("val = 1\n", encoding="utf-8")

        cache = FileBasedCache(
            path=self._cache_path,
            filename="dir_cache.bin",
            monitored_dirs=[subdir],
        )
        data = {"modules": ["module"]}
        cache.save(data)
        self.assertEqual(cache.get(), data)

    def testMonitoredDirectoryHashChangesOnNewFile(self) -> None:
        """Invalidate the cache when a new Python file appears in a monitored dir.

        Validates that adding a file to a monitored directory changes the
        computed hash so get() returns None on a fresh instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        subdir = self._cache_path / "src"
        subdir.mkdir()
        (subdir / "a.py").write_text("a = 1\n", encoding="utf-8")

        filename = "dir_hash_cache.bin"
        cache = FileBasedCache(
            path=self._cache_path,
            filename=filename,
            monitored_dirs=[subdir],
        )
        cache.save({"v": 1})

        # Add a new Python file to invalidate the hash
        time.sleep(0.02)
        (subdir / "b.py").write_text("b = 2\n", encoding="utf-8")

        fresh = FileBasedCache(
            path=self._cache_path,
            filename=filename,
            monitored_dirs=[subdir],
        )
        self.assertIsNone(fresh.get())

    def testNonExistentMonitoredFileIsIgnored(self) -> None:
        """Ignore monitored files that do not exist on disk.

        Validates that listing a non-existent path in monitored_files
        does not raise an exception and the cache still operates normally.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ghost = self._cache_path / "ghost.py"
        cache = FileBasedCache(
            path=self._cache_path,
            filename="ghost_cache.bin",
            monitored_files=[ghost],
        )
        data = {"ok": True}
        cache.save(data)
        self.assertEqual(cache.get(), data)

    def testTwoInstancesShareSameCacheFile(self) -> None:
        """Allow separate instances pointing to the same file to share data.

        Validates that a FileBasedCache instance can read data written by
        a different instance using the same path and filename.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        writer = FileBasedCache(
            path=self._cache_path, filename="shared.bin",
        )
        writer.save({"shared": "yes"})

        reader = FileBasedCache(
            path=self._cache_path, filename="shared.bin",
        )
        self.assertEqual(reader.get(), {"shared": "yes"})

    def testDifferentFilenamesAreIndependent(self) -> None:
        """Keep separate cache files independent of each other.

        Validates that two FileBasedCache instances using different
        filenames in the same directory do not share state.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = self._make(filename="a.bin")
        b = self._make(filename="b.bin")

        a.save({"owner": "a"})
        b.save({"owner": "b"})

        self.assertEqual(a.get(), {"owner": "a"})
        self.assertEqual(b.get(), {"owner": "b"})
