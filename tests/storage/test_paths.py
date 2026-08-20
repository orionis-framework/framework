from orionis.storage.exceptions import StoragePathException
from orionis.storage.paths import normalizeFilePath, normalizePath
from orionis.test import TestCase

class TestNormalizePath(TestCase):

    def testEmptyPathResolvesToRoot(self) -> None:
        """
        Resolve an empty path to the disk root.

        Validates that the root is represented by the empty string.
        """
        self.assertEqual(normalizePath(""), "")

    def testSeparatorsOnlyResolveToRoot(self) -> None:
        """
        Resolve separator-only paths to the disk root.

        Validates that empty segments are discarded.
        """
        self.assertEqual(normalizePath("/"), "")
        self.assertEqual(normalizePath("///"), "")

    def testKeepsAlreadyCanonicalPaths(self) -> None:
        """
        Keep canonical paths untouched.

        Validates the identity case of the normalizer.
        """
        self.assertEqual(normalizePath("docs/sub/a.txt"), "docs/sub/a.txt")

    def testStripsLeadingTrailingAndRepeatedSlashes(self) -> None:
        """
        Collapse redundant separators around and inside the path.

        Validates that the result never starts or ends with a slash.
        """
        self.assertEqual(normalizePath("/docs//sub///a.txt/"), "docs/sub/a.txt")

    def testConvertsBackslashesToForwardSlashes(self) -> None:
        """
        Convert Windows separators into the canonical form.

        Validates cross-platform path ingestion.
        """
        self.assertEqual(normalizePath("docs\\sub\\a.txt"), "docs/sub/a.txt")

    def testDropsCurrentDirectorySegments(self) -> None:
        """
        Discard ``.`` segments from the path.

        Validates that current-directory references are inert.
        """
        self.assertEqual(normalizePath("./docs/./sub/a.txt"), "docs/sub/a.txt")

    def testResolvesParentSegmentsLogically(self) -> None:
        """
        Resolve ``..`` segments without touching the filesystem.

        Validates that parent references consume the previous segment.
        """
        self.assertEqual(normalizePath("docs/sub/../a.txt"), "docs/a.txt")

    def testParentSegmentCanCollapseToRoot(self) -> None:
        """
        Allow ``..`` to consume the last remaining segment.

        Validates that collapsing to the root is not an escape.
        """
        self.assertEqual(normalizePath("docs/.."), "")

    def testRejectsLeadingParentSegment(self) -> None:
        """
        Reject paths starting above the disk root.

        Validates the traversal guard on the first segment.
        """
        with self.assertRaises(StoragePathException) as ctx:
            normalizePath("../escape")
        self.assertIn("escapes the disk root", str(ctx.exception))

    def testRejectsParentSegmentsBeyondRoot(self) -> None:
        """
        Reject paths climbing past the disk root.

        Validates the traversal guard after consuming segments.
        """
        with self.assertRaises(StoragePathException):
            normalizePath("docs/../../escape")

    def testRejectsDriveLetterSegments(self) -> None:
        """
        Reject segments containing a colon.

        Validates the guard against drive letters and stream names.
        """
        with self.assertRaises(StoragePathException) as ctx:
            normalizePath("C:/data")
        self.assertIn("forbidden", str(ctx.exception))

    def testRejectsColonInsideNestedSegments(self) -> None:
        """
        Reject colons in any segment, not just the first one.

        Validates that the check applies to the whole path.
        """
        with self.assertRaises(StoragePathException):
            normalizePath("docs/file:stream")

    def testRejectsNullBytes(self) -> None:
        """
        Reject paths containing a null byte.

        Validates the earliest guard of the normalizer.
        """
        with self.assertRaises(StoragePathException) as ctx:
            normalizePath("docs/a\x00.txt")
        self.assertIn("null bytes", str(ctx.exception))

class TestNormalizeFilePath(TestCase):

    def testReturnsCanonicalFilePath(self) -> None:
        """
        Return the canonical form of a valid file path.

        Validates that normalization rules are shared with directories.
        """
        self.assertEqual(normalizeFilePath("/docs//a.txt/"), "docs/a.txt")

    def testRejectsEmptyPath(self) -> None:
        """
        Reject an empty path for file operations.

        Validates that the disk root is never a valid file target.
        """
        with self.assertRaises(StoragePathException) as ctx:
            normalizeFilePath("")
        self.assertIn("non-empty file path", str(ctx.exception))

    def testRejectsPathsResolvingToRoot(self) -> None:
        """
        Reject paths that collapse to the disk root.

        Validates the guard applied after normalization.
        """
        with self.assertRaises(StoragePathException):
            normalizeFilePath("docs/..")

    def testPropagatesTraversalErrors(self) -> None:
        """
        Propagate traversal failures from the shared normalizer.

        Validates that file paths inherit every path guard.
        """
        with self.assertRaises(StoragePathException):
            normalizeFilePath("../escape.txt")
