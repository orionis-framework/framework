import asyncio
from email import policy
from email.parser import BytesParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Self, cast
from orionis.mail.composer import MailComposer
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.envelope import Envelope
from orionis.mail.entities.result import MailResult
from orionis.mail.enums.status import MailStatus
from orionis.mail.exceptions import MailAttachmentException, MailCompositionException
from orionis.storage.disk import Disk
from orionis.storage.drivers.local import LocalStorageDriver
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.exceptions import UnsupportedStorageOperationException
from orionis.test import TestCase
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication
    from orionis.mail.entities.prepared import PreparedMail
    from orionis.storage.contracts.manager import IStorageManager
    from orionis.view.contracts.engine import IViewEngine

_FIXTURE_ROOT = Path(__file__).parent / "fixtures"

class ViewApplication:
    """Expose explicit view configuration without an HTTP request."""

    __slots__ = ("base_path",)

    def __init__(self, path: Path) -> None:
        """Initialize the test helper.

        Parameters
        ----------
        path : Path
            Value supplied for ``path``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.base_path = path

    @property
    def basePath(self) -> Path:
        """Return the application root required by ViewEnvironment.

        Returns
        -------
        Path
            Value produced by the helper.
        """
        return self.base_path

    def config(self, key: str) -> object:
        """Return the fixture template directory as the configured loader.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        object
            Value produced by the helper.

        Raises
        ------
        KeyError
            Raised by this helper to exercise the failure path.
        """
        if key != "view":
            error_msg = "Unexpected configuration section."
            raise KeyError(error_msg)
        return {
            "paths": [str(_FIXTURE_ROOT)],
            "cache_path": None,
            "autoescape": True,
        }

class MailApplication(ViewApplication):
    """Expose central mail configuration plus a recording dependency resolver."""

    __slots__ = ("mail_config", "resolved")

    def __init__(self, path: Path, config: object) -> None:
        """Initialize the test helper.

        Parameters
        ----------
        path : Path
            Value supplied for ``path``.
        config : object
            Value supplied for ``config``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        super().__init__(path)
        self.mail_config = config
        self.resolved: list[type] = []

    def config(self, key: str) -> object:
        """Serve the selected section without reading environment variables.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self.mail_config if key == "mail" else super().config(key)

    async def make(self, contract: type) -> object:
        """Resolve the dependency requested by an extension factory.

        Parameters
        ----------
        contract : type
            Value supplied for ``contract``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        self.resolved.append(contract)
        return contract()

class RenderingEngine:
    """Return a controlled render result instead of a real template."""

    __slots__ = ("failure", "rendered", "requested")

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.failure: Exception | None = None
        self.rendered: object = "rendered"
        self.requested: list[tuple[str, dict[str, object]]] = []

    async def render(self, template: str, data: dict[str, object]) -> object:
        """Record the request and return the configured render result.

        Parameters
        ----------
        template : str
            Value supplied for ``template``.
        data : dict[str, object]
            Value supplied for ``data``.

        Returns
        -------
        object
            Value produced by the helper.

        Raises
        ------
        self.failure
            Raised by this helper to exercise the failure path.
        """
        self.requested.append((template, data))
        if self.failure is not None:
            raise self.failure
        return self.rendered

class MemoryStorage:
    """Expose memory-backed disks without local paths or public URLs."""

    __slots__ = ("default_disk", "disks", "selected")

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.disks = {
            "local": Disk("local", MemoryStorageDriver()),
            "remote": Disk("remote", MemoryStorageDriver()),
        }
        self.default_disk = "remote"
        self.selected: list[str | None] = []

    def disk(self, name: str | None = None) -> Disk:
        """Resolve an explicit or default disk and record the selection.

        Parameters
        ----------
        name : str | None
            Value supplied for ``name``.

        Returns
        -------
        Disk
            Value produced by the helper.
        """
        self.selected.append(name)
        return self.disks[name or self.default_disk]

class RemoteStream:
    """Expose an async stream without any local filesystem handle or path."""

    __slots__ = (
        "close_error",
        "closed",
        "entered",
        "open_error",
        "payload",
        "read_error",
        "release",
    )

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.close_error = False
        self.closed = 0
        self.entered = asyncio.Event()
        self.open_error = False
        self.payload: object = b"remote-data"
        self.read_error = False
        self.release = asyncio.Event()
        self.release.set()

    async def __aenter__(self) -> Self:
        """Pause opening when requested to exercise cancellation-safe ownership.

        Returns
        -------
        Self
            Value produced by the helper.

        Raises
        ------
        PermissionError
            Raised by this helper to exercise the failure path.
        """
        self.entered.set()
        await self.release.wait()
        if self.open_error:
            error_msg = "Remote opening denied."
            raise PermissionError(error_msg)
        return self

    async def read(self) -> object:
        """Return bytes or an explicit simulated driver failure value.

        Returns
        -------
        object
            Value produced by the helper.

        Raises
        ------
        PermissionError
            Raised by this helper to exercise the failure path.
        """
        if self.read_error:
            error_msg = "Remote read denied."
            raise PermissionError(error_msg)
        return self.payload

    async def close(self) -> None:
        """Record stream cleanup, including on read errors.

        Returns
        -------
        None
            Completes the operation described above.

        Raises
        ------
        OSError
            Raised by this helper to exercise the failure path.
        """
        self.closed += 1
        if self.close_error:
            error_msg = "Remote close failed."
            raise OSError(error_msg)

class RemoteStorage:
    """Serve the real disk/file/stream call shape without a local path."""

    __slots__ = ("metadata_calls", "mime_type", "paths", "selected", "stream")

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.metadata_calls = 0
        self.mime_type: str | None = None
        self.paths: list[str] = []
        self.selected: list[str | None] = []
        self.stream = RemoteStream()

    def disk(self, name: str | None = None) -> Self:
        """Record the explicit or default disk selected by preparation.

        Parameters
        ----------
        name : str | None
            Value supplied for ``name``.

        Returns
        -------
        Self
            Value produced by the helper.
        """
        self.selected.append(name)
        return self

    def file(self, path: str) -> Self:
        """Record the normalized logical path without rebuilding a local path.

        Parameters
        ----------
        path : str
            Value supplied for ``path``.

        Returns
        -------
        Self
            Value produced by the helper.
        """
        self.paths.append(path)
        return self

    async def mimeType(self) -> str | None:
        """Return backend metadata or a supported metadata-absent signal.

        Returns
        -------
        str | None
            Value produced by the helper.

        Raises
        ------
        UnsupportedStorageOperationException
            Raised by this helper to exercise the failure path.
        """
        self.metadata_calls += 1
        if self.mime_type == "unsupported":
            error_msg = "Metadata unsupported."
            raise UnsupportedStorageOperationException(error_msg)
        return self.mime_type

    def open(self, mode: str) -> RemoteStream:
        """Return a lazily opened stream with no filesystem representation.

        Parameters
        ----------
        mode : str
            Value supplied for ``mode``.

        Returns
        -------
        RemoteStream
            Value produced by the helper.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        if mode != "rb":
            error_msg = "Expected binary read mode."
            raise ValueError(error_msg)
        return self.stream

class RecordingDelivery:
    """Capture the declarations a chain hands to the delivery pipeline."""

    __slots__ = ("messages",)

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.messages: list[
            tuple[str | None, Envelope, Content, tuple[Attachment, ...]]
        ] = []

    async def __call__(
        self,
        mailer: str | None,
        envelope: Envelope,
        content: Content,
        attachments: tuple[Attachment, ...],
    ) -> MailResult:
        """Record one declaration without opening a production transport.

        Parameters
        ----------
        mailer : str | None
            Value supplied for ``mailer``.
        envelope : Envelope
            Value supplied for ``envelope``.
        content : Content
            Value supplied for ``content``.
        attachments : tuple[Attachment, ...]
            Value supplied for ``attachments``.

        Returns
        -------
        MailResult
            Value produced by the helper.
        """
        self.messages.append((mailer, envelope, content, attachments))
        await asyncio.sleep(0)
        return MailResult(
            message_id="<test@example.com>",
            mailer=mailer or "file",
            driver="file",
            status=MailStatus.STORED,
            recipients=envelope.recipients(),
        )

class RecordingTransport(IMailTransport):
    """Record only prepared mail; never see templates or logical paths."""

    __slots__ = ("messages",)

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.messages: list[PreparedMail] = []

    async def send(
        self,
        message: PreparedMail,
        *,
        mailer: str,
        driver: str,
    ) -> MailResult:
        """Record one message and return a typed test-only storage result.

        Parameters
        ----------
        message : PreparedMail
            Value supplied for ``message``.
        mailer : str
            Value supplied for ``mailer``.
        driver : str
            Value supplied for ``driver``.

        Returns
        -------
        MailResult
            Value produced by the helper.
        """
        self.messages.append(message)
        return MailResult(
            message_id=message.message_id,
            mailer=mailer,
            driver=driver,
            status=MailStatus.STORED,
            recipients=message.recipients,
        )

class RecordingFactory:
    """Exercise the public extension signature and async dependency lookup."""

    __slots__ = ("configs", "transports")

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.configs: list[object] = []
        self.transports: list[RecordingTransport] = []

    async def __call__(self, app: object, config: object) -> IMailTransport:
        """Obtain a transport dependency through the supplied container.

        Parameters
        ----------
        app : object
            Value supplied for ``app``.
        config : object
            Value supplied for ``config``.

        Returns
        -------
        IMailTransport
            Value produced by the helper.
        """
        self.configs.append(config)
        transport = await app.make(RecordingTransport)
        self.transports.append(transport)
        return transport

class TestMailComposer(TestCase):
    def setUp(self) -> None:
        """Build real Jinja and storage engines with isolated fixtures.

        Returns
        -------
        None
            Completes the operation described above.
        """
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
        """Render both alternatives through the configured Jinja engine.

        Validates that a template works without an active HTTP request.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Nest alternatives inside multipart/mixed with binary attachments.

        Validates that literal bodies are never rendered as templates.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Keep hidden recipients out of every serialized header.

        Validates that a message may have Bcc recipients only.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Fail before transport when a required preparation step is invalid.

        Validates that no partial message is ever produced.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Require SMTPUTF8 for international mailboxes only.

        Validates that Unicode bodies alone do not change the transport.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Read local files through the same API used for remote backends.

        Validates that the composer never rebuilds a filesystem path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Build the composer with an explicit pathless storage boundary.

        Returns
        -------
        None
            Completes the operation described above.
        """
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
        """Prepare one message carrying a single declared attachment.

        Parameters
        ----------
        **options : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        PreparedMail
            Value produced by the helper.
        """
        return await self.composer.prepare(
            self.envelope,
            Content(text="hello"),
            (Attachment.fromStorage("private/document.pdf", **options),),
        )

    async def testResolutionIsDeferredAndStreamsAreClosed(self) -> None:
        """Read attachment bytes only while preparing the message.

        Validates that declaring an attachment touches no backend.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Treat an empty payload as a valid attachment.

        Validates that the default disk is used when none was declared.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.storage.stream.payload = b""
        prepared = await self.prepareAttachment()
        parsed = BytesParser(policy=policy.default).parsebytes(prepared.mime)

        self.assertEqual(next(parsed.iter_attachments()).get_payload(decode=True), b"")
        self.assertEqual(self.storage.selected, [None])
        self.assertEqual(self.storage.stream.closed, 1)

    async def testExplicitMetadataOverridesBackendAndPath(self) -> None:
        """Prefer explicit metadata over backend metadata and inference.

        Validates that the backend is not even asked for a MIME type.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Fall back from backend metadata to inference and octet-stream.

        Validates the documented MIME resolution order.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Reject a backend MIME type carrying header parameters.

        Validates that storage metadata is validated like explicit metadata.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.storage.mime_type = "text/plain; charset=utf-8"
        with self.assertRaises(MailAttachmentException):
            await self.prepareAttachment()

    async def testDriverFailureValuesAreNotSilentlyEmptyAttachments(self) -> None:
        """Reject non-binary read results after closing the stream.

        Validates that a failure value never becomes an empty attachment.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for payload in (None, False, "not bytes"):
            self.storage.stream.payload = payload
            before = self.storage.stream.closed
            with self.assertRaises(MailAttachmentException):
                await self.prepareAttachment()
            self.assertEqual(self.storage.stream.closed, before + 1)

    async def testReadFailureClosesAndKeepsOriginalCause(self) -> None:
        """Keep a read failure visible even when cleanup also fails.

        Validates that the original cause survives the translation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.storage.stream.read_error = True
        self.storage.stream.close_error = True
        with self.assertRaises(MailAttachmentException) as raised:
            await self.prepareAttachment()

        self.assertIsInstance(raised.exception.__cause__, PermissionError)
        self.assertEqual(self.storage.stream.closed, 1)

    async def testOpenAndCloseFailuresAbortPreparation(self) -> None:
        """Abort preparation when a stream cannot be opened or closed.

        Validates that neither failure reaches the transport.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Retain ownership of an opening stream until cleanup finishes.

        Validates that cancellation is preserved after the stream closes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Build a composer over a view engine controlled by the test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.view = RenderingEngine()
        self.composer = MailComposer(
            cast("IViewEngine", self.view),
            cast("IStorageManager", MemoryStorage()),
        )

    async def testRejectsAnEnvelopeWithoutSender(self) -> None:
        """Refuse to compose a message that declares no sender.

        Validates the final guard reached through direct composer use.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(MailCompositionException):
            await self.composer.prepare(
                Envelope(to="ana@example.com"),
                Content(text="body"),
                (),
            )

    async def testRejectsNonTextRenderResults(self) -> None:
        """Refuse a view engine result that is not rendered text.

        Validates that a misbehaving engine never produces a MIME body.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.view.rendered = b"bytes"
        with self.assertRaises(MailCompositionException):
            await self.composer.prepare(
                Envelope(from_address="a@example.com", to="b@example.com"),
                Content(view="emails.welcome"),
                (),
            )

    async def testTranslatesViewEngineFailures(self) -> None:
        """Translate any engine failure into a composition failure.

        Validates that the original cause is preserved for debugging.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.view.failure = RuntimeError("template exploded")
        with self.assertRaises(MailCompositionException) as raised:
            await self.composer.prepare(
                Envelope(from_address="a@example.com", to="b@example.com"),
                Content(view="emails.welcome"),
                (),
            )
        self.assertIs(raised.exception.__cause__, self.view.failure)
