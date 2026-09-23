from types import MappingProxyType
from orionis.mail.exceptions import MailAttachmentException, MailCompositionException
from orionis.mail.functions import (
    attachment_name,
    freeze_owned,
    header_value,
    media_type,
    sanitize_reason,
)
from orionis.test import TestCase

_CREDENTIAL = "p@ss:word"

class TestHeaderValue(TestCase):

    def testReturnsSafeTextUnchanged(self) -> None:
        """
        Return safe header text exactly as supplied.

        Validates that Unicode and empty subjects are preserved.
        """
        self.assertEqual(header_value("", "Subject"), "")
        self.assertEqual(header_value("Aviso \u00fatil", "Subject"), "Aviso \u00fatil")

    def testRejectsControlCharactersAndNonText(self) -> None:
        """
        Reject header injection and values that are not text.

        Validates that the supplied label identifies the offending field.
        """
        for value in ("a\r\nBcc: x@y", "a\nb", "a\x00b", "a\u2028b"):
            with self.assertRaises(MailCompositionException):
                header_value(value, "Subject")
        with self.assertRaises(MailCompositionException) as failure:
            header_value(7, "Subject")
        self.assertIn("Subject", str(failure.exception))

class TestAttachmentName(TestCase):

    def testAcceptsUnicodeBasenames(self) -> None:
        """
        Accept a visible basename with Unicode characters.

        Validates that names are returned unchanged.
        """
        self.assertEqual(attachment_name("gu\u00eda.pdf"), "gu\u00eda.pdf")

    def testRejectsPathsAndUnsafeNames(self) -> None:
        """
        Reject separators, traversal, blanks, and control characters.

        Validates that a private path is never exposed as a filename.
        """
        for value in ("../secret", "a/b.pdf", "a\\b.pdf", "c:file", ".", "..", " "):
            with self.assertRaises(MailAttachmentException):
                attachment_name(value)

class TestMediaType(TestCase):

    def testNormalizesTypeAndSubtypeToLowercase(self) -> None:
        """
        Normalize a valid type/subtype pair to lowercase.

        Validates the value written into Content-Type.
        """
        self.assertEqual(media_type("APPLICATION/PDF"), "application/pdf")
        self.assertEqual(media_type("text/vnd.custom+xml"), "text/vnd.custom+xml")

    def testRejectsParametersAndMalformedPairs(self) -> None:
        """
        Reject header parameters and incomplete media types.

        Validates that no extra Content-Type directive can be injected.
        """
        for value in ("text/plain; charset=utf-8", "text", "text/", "/plain", 7):
            with self.assertRaises(MailAttachmentException):
                media_type(value)

class TestFreezeOwned(TestCase):

    def testCopiesContainersRecursively(self) -> None:
        """
        Convert owned containers into read-only equivalents.

        Validates that nested lists, sets, and mappings are detached.
        """
        source = {"names": ["Ana"], "tags": {"a"}, "pair": ("x",)}
        frozen = freeze_owned(source)
        source["names"].append("Luis")

        self.assertIsInstance(frozen, MappingProxyType)
        self.assertEqual(frozen["names"], ("Ana",))
        self.assertEqual(frozen["tags"], frozenset({"a"}))
        self.assertEqual(frozen["pair"], ("x",))

    def testKeepsOpaqueValuesByIdentity(self) -> None:
        """
        Share values that are not owned containers by reference.

        Validates that services are never deep-copied.
        """
        service = object()
        frozen = freeze_owned({"service": service, "count": 3})
        self.assertIs(frozen["service"], service)
        self.assertEqual(frozen["count"], 3)

    def testRejectsCyclicContainers(self) -> None:
        """
        Reject a container tree that cannot be snapshotted.

        Validates that a cycle fails instead of recursing forever.
        """
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        with self.assertRaises(MailCompositionException):
            freeze_owned(cyclic)

    def testAllowsTheSameContainerTwiceInOneTree(self) -> None:
        """
        Accept a shared container that is not an ancestor of itself.

        Validates that deduplication never rejects repeated references.
        """
        shared = ["value"]
        frozen = freeze_owned({"first": shared, "second": shared})
        self.assertEqual(frozen["first"], ("value",))
        self.assertEqual(frozen["second"], ("value",))

class TestSanitizeReason(TestCase):

    def testRemovesControlCharactersAndBounds(self) -> None:
        """
        Collapse control characters and bound the diagnostic length.

        Validates that a server response stays single line.
        """
        self.assertEqual(sanitize_reason(b"No\r\nmail\x00"), "No  mail ")
        self.assertEqual(len(sanitize_reason("x" * 900)), 512)

    def testRedactsConfiguredSecrets(self) -> None:
        """
        Redact every configured credential before reporting a rejection.

        Validates that the longest secret is replaced first.
        """
        reason = sanitize_reason(
            f"auth {_CREDENTIAL} for p@ss",
            (_CREDENTIAL, "p@ss", ""),
        )
        self.assertNotIn(_CREDENTIAL, reason)
        self.assertEqual(reason, "auth [redacted] for [redacted]")

    def testDecodesNonUtf8Responses(self) -> None:
        """
        Decode a non-UTF-8 response instead of failing.

        Validates that a malformed reply still produces a diagnostic.
        """
        self.assertIn("mail", sanitize_reason(b"\xff mail"))
