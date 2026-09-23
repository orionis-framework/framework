import asyncio
from email import policy
from email.parser import BytesParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, cast
from orionis.mail.composer import MailComposer
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.envelope import Envelope
from orionis.mail.exceptions import MailAttachmentException, MailCompositionException
from orionis.storage.disk import Disk
from orionis.storage.drivers.local import LocalStorageDriver
from orionis.test import TestCase
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment
from tests.mail.fixtures.doubles import (
    MemoryStorage,
    RemoteStorage,
    RenderingEngine,
    ViewApplication,
)

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication
    from orionis.mail.entities.prepared import PreparedMail
    from orionis.storage.contracts.manager import IStorageManager
    from orionis.view.contracts.engine import IViewEngine

class TestMailComposer(TestCase):

    def setUp(self) -> None:
        """Build real Jinja and storage engines with isolated fixtures."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.app = ViewApplication(Path(temporary.name))
        self.view = Jinja2Engine(ViewEnvironment(cast("IApplication", self.app)))
        self.storage = MemoryStorage()
        self.composer = MailComposer(self.view, cast("IStorageManager", self.storage))
        self.envelope = Envelope(
            from_address="sender@example.com",
            to="ana@example.com",
        )

    async def testRealViewsRenderWithoutRequestAndWithIsolatedContext(self) -> None:
        """
        Render both alternatives through the configured Jinja engine.

        Validates that a template works without an active HTTP request.
        """
        content = Content(
            view="emails.welcome",
            text_view="emails/welcome.txt",
            data={"name": "Ana & Luis"},
        )
        prepared = await self.composer.prepare(self.envelope, content, ())
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)

        self.assertEqual(parsed.get_content_type(), "multipart/alternative")
        self.assertIn("Ana &amp; Luis", parsed.get_body(("html",)).get_content())
        self.assertIn("Ana &amp; Luis", parsed.get_body(("plain",)).get_content())
        self.assertEqual(str(parsed["Message-ID"]), prepared.message_id)
        self.assertIsNotNone(parsed["Date"])

    async def testMimeAlternativesAndAttachmentsKeepCorrectNesting(self) -> None:
        """
        Nest alternatives inside multipart/mixed with binary attachments.

        Validates that literal bodies are never rendered as templates.
        """
        await self.storage.disk("remote").file("private/empty.bin").write(b"")
        await self.storage.disk("local").file("documents/guide.pdf").write(b"%PDF-test")
        prepared = await self.composer.prepare(
            self.envelope,
            Content(text="plain {{ literal }}", html="<b>\u00e9</b>"),
            (
                Attachment.fromStorage("private/empty.bin"),
                Attachment.fromStorage(
                    "documents/guide.pdf",
                    disk="local",
                    name="gu\u00eda.pdf",
                    mime_type="application/pdf",
                ),
            ),
        )
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)
        parts = list(parsed.iter_parts())

        self.assertEqual(parsed.get_content_type(), "multipart/mixed")
        self.assertEqual(parts[0].get_content_type(), "multipart/alternative")
        self.assertEqual(parts[1].get_payload(decode=True), b"")
        self.assertEqual(parts[1].get_filename(), "empty.bin")
        self.assertEqual(parts[2].get_filename(), "gu\u00eda.pdf")
        self.assertEqual(parts[2].get_payload(decode=True), b"%PDF-test")
        self.assertIn("{{ literal }}", parsed.get_body(("plain",)).get_content())

    async def testBccOnlyIsPresentOnlyInTransportEnvelope(self) -> None:
        """
        Keep hidden recipients out of every serialized header.

        Validates that a message may have Bcc recipients only.
        """
        envelope = Envelope(from_address="sender@example.com", bcc="hidden@example.com")
        prepared = await self.composer.prepare(envelope, Content(text="private"), ())
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)

        self.assertEqual(prepared.recipients, ("hidden@example.com",))
        self.assertIsNone(parsed["Bcc"])
        self.assertIsNone(parsed["To"])
        self.assertIsNone(parsed["Sender"])
        self.assertNotIn(b"hidden@example.com", prepared.mime)

    async def testMissingSenderRecipientViewOrFileFailsPreparation(self) -> None:
        """
        Fail before transport when a required preparation step is invalid.

        Validates that no partial message is ever produced.
        """
        for envelope in (Envelope(to="a@b"), Envelope(from_address="a@b")):
            with self.assertRaises(MailCompositionException):
                await self.composer.prepare(envelope, Content(text=""), ())

        with self.assertRaises(MailCompositionException):
            await self.composer.prepare(self.envelope, Content(view="missing"), ())

        with self.assertRaises(MailAttachmentException):
            await self.composer.prepare(
                self.envelope,
                Content(text=""),
                (Attachment.fromStorage("missing.pdf"),),
            )

    async def testUtf8MailboxesArePreservedAndFlagged(self) -> None:
        """
        Require SMTPUTF8 for international mailboxes only.

        Validates that Unicode bodies alone do not change the transport.
        """
        prepared = await self.composer.prepare(
            Envelope(from_address="jos\u00e9@example.com", to="ana@example.com"),
            Content(html="<p>Hola, Jos\u00e9</p>"),
            (),
        )
        self.assertTrue(prepared.smtp_utf8)
        self.assertIn("jos\u00e9@example.com".encode(), prepared.mime)

        regular = await self.composer.prepare(self.envelope, Content(text="\u00e9"), ())
        self.assertFalse(regular.smtp_utf8)

    async def testReadsARealLocalStorageDisk(self) -> None:
        """
        Read local files through the same API used for remote backends.

        Validates that the composer never rebuilds a filesystem path.
        """
        disk = Disk("local", LocalStorageDriver(self.app.basePath / "storage"))
        self.storage.disks["local"] = disk
        await disk.file("documents/guide.pdf").write(b"%PDF-local-fixture")

        prepared = await self.composer.prepare(
            self.envelope,
            Content(text="Guide"),
            (Attachment.fromStorage("documents/guide.pdf", disk="local"),),
        )
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)
        self.assertEqual(
            next(parsed.iter_attachments()).get_payload(decode=True),
            b"%PDF-local-fixture",
        )

class TestMailComposerStorageAttachments(TestCase):

    def setUp(self) -> None:
        """Build the composer with an explicit pathless storage boundary."""
        self.storage = RemoteStorage()
        self.composer = MailComposer(
            cast("IViewEngine", object()),
            cast("IStorageManager", self.storage),
        )
        self.envelope = Envelope(
            from_address="sender@example.com",
            to="ana@example.com",
        )

    async def prepareAttachment(self, **options: object) -> PreparedMail:
        """Prepare one message carrying a single declared attachment."""
        return await self.composer.prepare(
            self.envelope,
            Content(text="hello"),
            (Attachment.fromStorage("private/document.pdf", **options),),
        )

    async def testResolutionIsDeferredAndStreamsAreClosed(self) -> None:
        """
        Read attachment bytes only while preparing the message.

        Validates that declaring an attachment touches no backend.
        """
        attachment = Attachment.fromStorage("private/document.pdf", disk="remote")
        self.assertEqual(self.storage.selected, [])

        prepared = await self.composer.prepare(
            self.envelope,
            Content(text="hello"),
            (attachment,),
        )
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)
        part = next(parsed.iter_attachments())

        self.assertEqual(part.get_payload(decode=True), b"remote-data")
        self.assertEqual(part.get_filename(), "document.pdf")
        self.assertEqual(self.storage.selected, ["remote"])
        self.assertEqual(self.storage.stream.closed, 1)

    async def testZeroBytesAndDefaultDiskAreValid(self) -> None:
        """
        Treat an empty payload as a valid attachment.

        Validates that the default disk is used when none was declared.
        """
        self.storage.stream.payload = b""
        prepared = await self.prepareAttachment()
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)

        self.assertEqual(next(parsed.iter_attachments()).get_payload(decode=True), b"")
        self.assertEqual(self.storage.selected, [None])
        self.assertEqual(self.storage.stream.closed, 1)

    async def testExplicitMetadataOverridesBackendAndPath(self) -> None:
        """
        Prefer explicit metadata over backend metadata and inference.

        Validates that the backend is not even asked for a MIME type.
        """
        self.storage.mime_type = "invalid metadata"
        prepared = await self.prepareAttachment(
            name="report.txt",
            mime_type="text/plain",
        )
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)
        part = next(parsed.iter_attachments())

        self.assertEqual(part.get_content_type(), "text/plain")
        self.assertEqual(part.get_filename(), "report.txt")
        self.assertEqual(self.storage.metadata_calls, 0)

    async def testMetadataThenNameThenBinaryFallback(self) -> None:
        """
        Fall back from backend metadata to inference and octet-stream.

        Validates the documented MIME resolution order.
        """
        self.storage.mime_type = "image/png"
        prepared = await self.prepareAttachment()
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)
        self.assertEqual(
            next(parsed.iter_attachments()).get_content_type(),
            "image/png",
        )

        self.storage.mime_type = "unsupported"
        prepared = await self.prepareAttachment(name="unknown.extension-unregistered")
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)
        self.assertEqual(
            next(parsed.iter_attachments()).get_content_type(),
            "application/octet-stream",
        )

    async def testRejectsUnsafeBackendMetadata(self) -> None:
        """
        Reject a backend MIME type carrying header parameters.

        Validates that storage metadata is validated like explicit metadata.
        """
        self.storage.mime_type = "text/plain; charset=utf-8"
        with self.assertRaises(MailAttachmentException):
            await self.prepareAttachment()

    async def testDriverFailureValuesAreNotSilentlyEmptyAttachments(self) -> None:
        """
        Reject non-binary read results after closing the stream.

        Validates that a failure value never becomes an empty attachment.
        """
        for payload in (None, False, "not bytes"):
            self.storage.stream.payload = payload
            before = self.storage.stream.closed
            with self.assertRaises(MailAttachmentException):
                await self.prepareAttachment()
            self.assertEqual(self.storage.stream.closed, before + 1)

    async def testReadFailureClosesAndKeepsOriginalCause(self) -> None:
        """
        Keep a read failure visible even when cleanup also fails.

        Validates that the original cause survives the translation.
        """
        self.storage.stream.read_error = True
        self.storage.stream.close_error = True
        with self.assertRaises(MailAttachmentException) as raised:
            await self.prepareAttachment()

        self.assertIsInstance(raised.exception.__cause__, PermissionError)
        self.assertEqual(self.storage.stream.closed, 1)

    async def testOpenAndCloseFailuresAbortPreparation(self) -> None:
        """
        Abort preparation when a stream cannot be opened or closed.

        Validates that neither failure reaches the transport.
        """
        self.storage.stream.open_error = True
        with self.assertRaises(MailAttachmentException):
            await self.prepareAttachment()
        self.assertEqual(self.storage.stream.closed, 1)

        self.storage.stream.open_error = False
        self.storage.stream.close_error = True
        with self.assertRaises(MailAttachmentException):
            await self.prepareAttachment()
        self.assertEqual(self.storage.stream.closed, 2)

    async def testCancellationDuringOpenWaitsForClosureThenPropagates(self) -> None:
        """
        Retain ownership of an opening stream until cleanup finishes.

        Validates that cancellation is preserved after the stream closes.
        """
        self.storage.stream.release.clear()
        operation = asyncio.create_task(self.prepareAttachment())
        await self.storage.stream.entered.wait()

        operation.cancel()
        await asyncio.sleep(0)
        self.assertFalse(operation.done())

        operation.cancel()
        self.storage.stream.release.set()
        with self.assertRaises(asyncio.CancelledError):
            await operation
        self.assertEqual(self.storage.stream.closed, 1)

class TestMailComposerGuards(TestCase):

    def setUp(self) -> None:
        """Build a composer over a view engine controlled by the test."""
        self.view = RenderingEngine()
        self.composer = MailComposer(
            cast("IViewEngine", self.view),
            cast("IStorageManager", MemoryStorage()),
        )

    async def testRejectsAnEnvelopeWithoutSender(self) -> None:
        """
        Refuse to compose a message that declares no sender.

        Validates the final guard reached through direct composer use.
        """
        with self.assertRaises(MailCompositionException):
            await self.composer.prepare(
                Envelope(to="ana@example.com"),
                Content(text="body"),
                (),
            )

    async def testRejectsNonTextRenderResults(self) -> None:
        """
        Refuse a view engine result that is not rendered text.

        Validates that a misbehaving engine never produces a MIME body.
        """
        self.view.rendered = b"bytes"
        with self.assertRaises(MailCompositionException):
            await self.composer.prepare(
                Envelope(from_address="a@example.com", to="b@example.com"),
                Content(view="emails.welcome"),
                (),
            )

    async def testTranslatesViewEngineFailures(self) -> None:
        """
        Translate any engine failure into a composition failure.

        Validates that the original cause is preserved for debugging.
        """
        self.view.failure = RuntimeError("template exploded")
        with self.assertRaises(MailCompositionException) as raised:
            await self.composer.prepare(
                Envelope(from_address="a@example.com", to="b@example.com"),
                Content(view="emails.welcome"),
                (),
            )
        self.assertIs(raised.exception.__cause__, self.view.failure)
