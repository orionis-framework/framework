import tempfile
from pathlib import Path
from orionis.test import TestCase
from orionis.view.cache import OrionisBytecodeCache

class _StubBucket:
    """Bytecode bucket double exposing only the cache key."""

    __slots__ = ("key",)

    def __init__(self, key: str) -> None:
        self.key: str = key

class TestOrionisBytecodeCache(TestCase):

    def setUp(self) -> None:
        """
        Create an isolated temporary directory before each test.

        Provides a fresh, writable directory so every test operates on
        its own filesystem state without side effects.
        """
        self._tmpdir = tempfile.TemporaryDirectory()
        self._cache_dir = self._tmpdir.name

    def tearDown(self) -> None:
        """
        Remove the temporary directory after each test.

        Ensures all files created during the test are cleaned up
        regardless of whether the test passed or failed.
        """
        self._tmpdir.cleanup()

    def _make(self) -> OrionisBytecodeCache:
        """
        Construct an OrionisBytecodeCache backed by the temp directory.

        Returns
        -------
        OrionisBytecodeCache
            A fresh instance backed by the test's temporary directory.
        """
        return OrionisBytecodeCache(self._cache_dir)

    def testGetCacheKeyStripsHtmlExtension(self) -> None:
        """
        Strip the .html extension from the cache key.

        Validates that a template name ending in .html produces a key
        without the extension appended.
        """
        cache = self._make()
        self.assertEqual(cache.get_cache_key("users/index.html"), "users.index")

    def testGetCacheKeyStripsHtmExtension(self) -> None:
        """
        Strip the .htm extension from the cache key.

        Validates that a template name ending in .htm produces a key
        without the extension.
        """
        cache = self._make()
        self.assertEqual(cache.get_cache_key("pages/about.htm"), "pages.about")

    def testGetCacheKeyStripsJinjaExtension(self) -> None:
        """
        Strip the .jinja extension from the cache key.

        Validates that a template name ending in .jinja produces a key
        without the extension.
        """
        cache = self._make()
        self.assertEqual(
            cache.get_cache_key("layout/base.jinja"), "layout.base",
        )

    def testGetCacheKeyStripsJinja2Extension(self) -> None:
        """
        Strip the .jinja2 extension from the cache key.

        Validates that a template name ending in .jinja2 produces a key
        without the extension.
        """
        cache = self._make()
        key = cache.get_cache_key("emails/welcome.jinja2")
        self.assertEqual(key, "emails.welcome")

    def testGetCacheKeyStripsJ2Extension(self) -> None:
        """
        Strip the .j2 extension from the cache key.

        Validates that a template name ending in .j2 produces a key
        without the extension.
        """
        cache = self._make()
        self.assertEqual(
            cache.get_cache_key("admin/dashboard.j2"), "admin.dashboard",
        )

    def testGetCacheKeyConvertsSlashesToDots(self) -> None:
        """
        Convert forward slashes to dots in the cache key.

        Validates that nested template paths are flattened using dot
        separators so the key is suitable as a filename stem.
        """
        cache = self._make()
        key = cache.get_cache_key("deep/nested/path/template.html")
        self.assertEqual(key, "deep.nested.path.template")

    def testGetCacheKeyConvertsBackslashesToDots(self) -> None:
        """
        Convert backslashes to dots in the cache key.

        Validates that Windows-style path separators are handled the
        same way as forward slashes.
        """
        cache = self._make()
        key = cache.get_cache_key("partials\\nav.html")
        self.assertEqual(key, "partials.nav")

    def testGetCacheKeyPreservesUnknownExtension(self) -> None:
        """
        Preserve unknown extensions in the cache key.

        Validates that extensions not in the known list are kept intact
        in the returned key without stripping.
        """
        cache = self._make()
        self.assertEqual(
            cache.get_cache_key("styles/main.css"), "styles.main.css",
        )

    def testGetCacheKeyNoExtension(self) -> None:
        """
        Return the name unchanged when no recognised extension is present.

        Validates that a template identifier without a known extension
        passes through the sanitisation step unmodified.
        """
        cache = self._make()
        self.assertEqual(cache.get_cache_key("no_extension"), "no_extension")

    def testGetCacheKeyIgnoresFilenameArgument(self) -> None:
        """
        Produce the same key regardless of the filename argument.

        Validates that the optional filename parameter does not affect the
        computed cache key because the implementation intentionally ignores it.
        """
        cache = self._make()
        key_without = cache.get_cache_key("users/index.html")
        key_with = cache.get_cache_key(
            "users/index.html", "/abs/path/index.html",
        )
        self.assertEqual(key_without, key_with)

    def testGetCacheFilenameReturnsExpectedPath(self) -> None:
        """
        Return the absolute path string from _get_cache_filename.

        Validates that the returned path is rooted at the configured
        cache directory and ends with the .cache suffix.
        """
        cache = self._make()
        bucket = _StubBucket("users.index")
        result = cache._get_cache_filename(bucket)
        expected = str(Path(self._cache_dir) / "users.index.cache")
        self.assertEqual(result, expected)

    def testGetCacheFilenameUsesKeyAttribute(self) -> None:
        """
        Build the cache filename from the bucket key attribute.

        Validates that the filename stem is exactly the key on the
        provided bucket, preserving any dot-separated structure.
        """
        cache = self._make()
        bucket = _StubBucket("admin.dashboard.j2")
        result = cache._get_cache_filename(bucket)
        self.assertIn("admin.dashboard.j2.cache", result)

    def testGetCacheFilenameAlwaysEndsDotCache(self) -> None:
        """
        Ensure _get_cache_filename always appends the .cache suffix.

        Validates that every cache filename produced by the method ends
        with the .cache extension.
        """
        cache = self._make()
        bucket = _StubBucket("emails.welcome")
        result = cache._get_cache_filename(bucket)
        self.assertTrue(result.endswith(".cache"))

    def testGetCacheFilenameIsAbsolutePath(self) -> None:
        """
        Confirm _get_cache_filename returns a string rooted at cache_dir.

        Validates that the returned filename starts with the configured
        cache directory path so writes land in the expected location.
        """
        cache = self._make()
        bucket = _StubBucket("some.template")
        result = cache._get_cache_filename(bucket)
        self.assertTrue(result.startswith(self._cache_dir))

    def testGetCacheKeyStripsOnlyTheMatchingExtension(self) -> None:
        """
        Strip a single recognised extension from the cache key.

        Validates that the sanitisation loop stops at the first match so
        chained suffixes are not removed twice.
        """
        cache = self._make()
        self.assertEqual(cache.get_cache_key("page.html.j2"), "page.html")

    def testGetCacheKeyOnEmptyNameReturnsEmptyString(self) -> None:
        """
        Return an empty key for an empty template name.

        Validates that the sanitisation step never fails on a degenerate
        template identifier.
        """
        cache = self._make()
        self.assertEqual(cache.get_cache_key(""), "")
