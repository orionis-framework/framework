import asyncio
import os
import threading
from email import policy
from email.parser import BytesParser
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from orionis.mail.entities.prepared import PreparedMail
from orionis.mail.enums.status import MailStatus
from orionis.mail.exceptions import MailConfigurationException, MailTransportException
from orionis.mail.transports import file as file_module
from orionis.mail.transports.file import FileTransport, create_file_transport
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

_PAYLOAD = b"From: a@example.com\r\nSubject: Stored\r\n\r\nComplete body\r\n"
_PREPARED = PreparedMail(
    message_id="<stored@example.com>",
    sender="a@example.com",
    recipients=("hidden@example.com",),
    mime=_PAYLOAD,
    smtp_utf8=False,
)

class PublicationBoundary:
    """Inject failures around publication while keeping real filesystem writes."""

    __slots__ = ("failure", "name", "observed", "release", "started", "synced")

    def __init__(self) -> None:
        self.failure: str | None = None
        self.name = "safe-unique-name"
        self.observed: list[tuple[bytes, bool, bool]] = []
        self.release = threading.Event()
        self.release.set()
        self.started = threading.Event()
        self.synced = False

    def token_hex(self, _size: int) -> str:
        """Return a deterministic safe name for collision tests."""
        return self.name

    def fsync(self, descriptor: int) -> None:
        """Sync a real temporary file or simulate a persistence failure."""
        if self.failure == "sync":
            error_msg = "Injected sync failure."
            raise OSError(error_msg)
        os.fsync(descriptor)
        self.synced = True

    def link(self, temporary: Path, final: Path) -> None:
        """Inspect the staged file before its atomic publication."""
        self.observed.append((temporary.read_bytes(), final.exists(), self.synced))
        self.started.set()
        if not self.release.wait(5):
            error_msg = "Publication was not released by the test."
            raise TimeoutError(error_msg)
        if self.failure == "link":
            error_msg = "Injected unsupported hard-link filesystem."
            raise OSError(error_msg)
        os.link(temporary, final)

class ObservedFileTransport(FileTransport):
    """Expose completion of the worker, including its temporary cleanup."""

    __slots__ = ("finished",)

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.finished = threading.Event()

    def _store(self, payload: bytes) -> Path:
        """Signal completion once the worker released every resource."""
        try:
            return super()._store(payload)
        finally:
            self.finished.set()

class TestFileTransport(TestCase):

    def setUp(self) -> None:
        """Isolate the output and cwd, replacing publication primitives."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.root = root / "application"
        self.root.mkdir()
        other = root / "other-cwd"
        other.mkdir()
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(other)

        self.original_os = file_module.os
        self.original_secrets = file_module.secrets
        self.boundary = PublicationBoundary()
        file_module.os = SimpleNamespace(
            link=self.boundary.link,
            fsync=self.boundary.fsync,
        )
        file_module.secrets = self.boundary
        self.app = cast("IApplication", SimpleNamespace(basePath=self.root))

    def tearDown(self) -> None:
        """Restore the production publication primitives."""
        self.boundary.release.set()
        file_module.os = self.original_os
        file_module.secrets = self.original_secrets

    async def testRelativePathsAnchorToApplicationAndPublishCompleteMime(self) -> None:
        """
        Resolve a relative output against the application root.

        Validates that a complete parseable message is published.
        """
        transport = create_file_transport(self.app, {"path": "outgoing"})
        result = await transport.send(_PREPARED, mailer="archive", driver="file")

        self.assertEqual(result.file_path.parent, self.root / "outgoing")
        self.assertFalse((Path.cwd() / "outgoing").exists())
        self.assertEqual(self.boundary.observed, [(_PAYLOAD, False, True)])
        self.assertEqual(result.status, MailStatus.STORED)
        self.assertEqual(result.recipients, ("hidden@example.com",))
        self.assertEqual(result.accepted_recipients, ())
        self.assertEqual(list(result.file_path.parent.glob("*.tmp")), [])

        parsed = BytesParser(policy=policy.default).parsebytes(
            result.file_path.read_bytes(),
        )
        self.assertEqual(parsed["Subject"], "Stored")
        self.assertIsNone(parsed["Bcc"])
        if os.name == "posix":
            self.assertEqual(result.file_path.stat().st_mode & 0o077, 0)

    async def testDefaultsToTheConventionalOutputDirectory(self) -> None:
        """
        Fall back to the documented storage directory.

        Validates the behaviour of a mailer that omits its path.
        """
        transport = create_file_transport(self.app, {})
        result = await transport.send(_PREPARED, mailer="file", driver="file")
        self.assertEqual(result.file_path.parent, self.root / "storage/mail")

    async def testAbsoluteOutputPathsAreRespected(self) -> None:
        """
        Keep an absolute output path outside the application root.

        Validates that absolute configuration is never re-anchored.
        """
        output = self.root.parent / "absolute"
        transport = create_file_transport(self.app, {"path": str(output)})
        result = await transport.send(_PREPARED, mailer="archive", driver="file")
        self.assertEqual(result.file_path.parent, output)

    async def testNameCollisionsNeverOverwriteExistingMail(self) -> None:
        """
        Let the filesystem arbitrate competing publications.

        Validates that an existing message is never replaced.
        """
        transport = FileTransport(self.root / "outgoing")
        results = await asyncio.gather(
            transport.send(_PREPARED, mailer="file", driver="file"),
            transport.send(_PREPARED, mailer="file", driver="file"),
            return_exceptions=True,
        )

        self.assertEqual(
            sum(isinstance(item, MailTransportException) for item in results),
            1,
        )
        files = list((self.root / "outgoing").iterdir())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_bytes(), _PAYLOAD)

    async def testSyncAndPublicationFailuresLeaveNoTemporaryOrFinalFile(self) -> None:
        """
        Remove the staged file when durability or publication fails.

        Validates that no partial message survives a failure.
        """
        for failure in ("sync", "link"):
            self.boundary.failure = failure
            target = self.root / failure
            with self.assertRaises(MailTransportException):
                await FileTransport(target).send(
                    _PREPARED,
                    mailer="file",
                    driver="file",
                )
            self.assertEqual(list(target.iterdir()), [])

    async def testDirectoryCreationFailureIsExplicit(self) -> None:
        """
        Report an unwritable output boundary instead of inventing a result.

        Validates that an existing file blocks the directory creation.
        """
        target = self.root / "not-a-directory"
        target.write_bytes(b"existing")
        with self.assertRaises(MailTransportException):
            await FileTransport(target).send(_PREPARED, mailer="file", driver="file")
        self.assertEqual(target.read_bytes(), b"existing")

    def testRejectsInvalidOutputConfiguration(self) -> None:
        """
        Validate the configured path when the transport is selected.

        Validates that an ambiguous or empty path never reaches the disk.
        """
        for path in ("", "   ", "bad\x00path", None, 7):
            with self.assertRaises(MailConfigurationException):
                create_file_transport(self.app, {"path": path})

    def testRejectsAnchoredButRelativePaths(self) -> None:
        """
        Reject a path that is anchored yet not absolute.

        Validates that a drive-relative location is never guessed.
        """
        candidate = Path("C:outgoing")
        if not candidate.anchor or candidate.is_absolute():
            self.skipTest("This platform has no drive-relative paths.")
        with self.assertRaises(MailConfigurationException):
            create_file_transport(self.app, {"path": str(candidate)})

    async def testCancellationDoesNotAbandonTheWorkerTemporary(self) -> None:
        """
        Let the worker own its cleanup after the waiter is cancelled.

        Validates that cancellation never leaves a stray temporary file.
        """
        self.boundary.release.clear()
        output = self.root / "cancelled"
        transport = ObservedFileTransport(output)
        operation = asyncio.create_task(
            transport.send(_PREPARED, mailer="file", driver="file"),
        )

        self.assertTrue(await asyncio.to_thread(self.boundary.started.wait, 3))
        operation.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await operation

        self.boundary.release.set()
        self.assertTrue(await asyncio.to_thread(transport.finished.wait, 3))
        files = list(output.iterdir())
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].suffix, ".eml")
        self.assertEqual(files[0].read_bytes(), _PAYLOAD)
