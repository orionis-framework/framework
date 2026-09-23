from dataclasses import FrozenInstanceError
from orionis.mail.entities.attachment import Attachment
from orionis.mail.exceptions import MailAttachmentException
from orionis.test import TestCase

class TestAttachment(TestCase):

    def testDeclarationNormalizesPathAndMimeType(self) -> None:
        """
        Normalize the logical path and lowercase an explicit MIME type.

        Validates that declaring an attachment performs no storage access.
        """
        attachment = Attachment.fromStorage(
            "./private/../documents/guide.pdf",
            disk="local",
            name="guide.pdf",
            mime_type="APPLICATION/PDF",
        )
        self.assertEqual(attachment.path, "documents/guide.pdf")
        self.assertEqual(attachment.mime_type, "application/pdf")
        self.assertEqual(attachment.disk, "local")
        self.assertEqual(attachment.name, "guide.pdf")

    def testMissingFilesRemainValidDeclarations(self) -> None:
        """
        Accept a path that does not exist yet.

        Validates that resolution is deferred to the sending pipeline.
        """
        attachment = Attachment.fromStorage("private/missing.pdf")
        self.assertEqual(attachment.path, "private/missing.pdf")
        self.assertIsNone(attachment.disk)
        self.assertIsNone(attachment.name)
        self.assertIsNone(attachment.mime_type)

    def testDeclarationIsFrozen(self) -> None:
        """
        Reject mutation of an already declared attachment.

        Validates that a shared declaration cannot be rewritten in place.
        """
        attachment = Attachment.fromStorage("guide.pdf")
        with self.assertRaises(FrozenInstanceError):
            attachment.path = "other.pdf"

    def testRejectsUnsafePathsAndDisks(self) -> None:
        """
        Reject traversal, control characters, and empty disk names.

        Validates that unsafe declarations fail before any disk resolution.
        """
        for path in ("../private.pdf", "guide\r\n.pdf", "", "a\x00b"):
            with self.assertRaises(MailAttachmentException):
                Attachment.fromStorage(path)
        with self.assertRaises(MailAttachmentException):
            Attachment.fromStorage("guide.pdf", disk="   ")

    def testRejectsUnsafeVisibleNamesAndMediaTypes(self) -> None:
        """
        Reject visible names holding paths and MIME types with parameters.

        Validates that Content-Disposition and Content-Type stay safe.
        """
        for options in (
            {"name": "../secret"},
            {"name": "x\r\nY"},
            {"name": "  "},
            {"name": "."},
            {"mime_type": "text/plain; charset=utf-8"},
            {"mime_type": "text"},
            {"mime_type": "text/"},
        ):
            with self.assertRaises(MailAttachmentException):
                Attachment.fromStorage("safe.pdf", **options)
