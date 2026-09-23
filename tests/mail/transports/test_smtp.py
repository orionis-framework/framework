import asyncio
import smtplib
import ssl
import threading
import traceback
from email import policy
from email.parser import BytesParser
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from orionis.mail.composer import MailComposer
from orionis.mail.entities.content import Content
from orionis.mail.entities.prepared import PreparedMail
from orionis.mail.entities.smtp_settings import SmtpSettings
from orionis.mail.enums.status import MailStatus
from orionis.mail.exceptions import MailTransportException
from orionis.mail.manager import MailManager
from orionis.mail.transports import smtp as smtp_module
from orionis.mail.transports.smtp import SmtpTransport
from orionis.test import TestCase
from tests.mail.fixtures.doubles import MailApplication

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.foundation.contracts.application import IApplication
    from orionis.storage.contracts.manager import IStorageManager
    from orionis.view.contracts.engine import IViewEngine

_CREDENTIAL = "private-auth-value"
_MESSAGE = PreparedMail(
    message_id="<transaction@example.com>",
    sender="sender@example.com",
    recipients=("ana@example.com", "hidden@example.com"),
    mime=b"From: sender@example.com\r\nTo: ana@example.com\r\n\r\nHello\r\n",
    smtp_utf8=False,
)

class SmtpBoundary:
    """Build explicit per-operation connections without opening a socket."""

    __slots__ = (
        "clients",
        "close_error",
        "closed",
        "extensions",
        "failure",
        "failure_at",
        "refused",
        "release",
        "started",
        "status",
    )

    def __init__(self) -> None:
        self.clients: list[RecordingClient] = []
        self.close_error = False
        self.closed = threading.Event()
        self.extensions = {"smtputf8", "8bitmime", "starttls"}
        self.failure: Exception | None = None
        self.failure_at: str | None = None
        self.refused: dict[str, tuple[int, bytes]] = {}
        self.release = threading.Event()
        self.release.set()
        self.started = threading.Event()
        self.status = 220

    def plain(self, *, timeout: int | None) -> RecordingClient:
        """Build one plaintext or STARTTLS-capable connection."""
        return self._create(timeout, None)

    def encrypted(
        self,
        *,
        timeout: int | None,
        context: ssl.SSLContext,
    ) -> RecordingClient:
        """Build one implicit-TLS connection and keep its context."""
        return self._create(timeout, context)

    def _create(
        self,
        timeout: int | None,
        context: ssl.SSLContext | None,
    ) -> RecordingClient:
        """Register and return a new recording connection."""
        connection = RecordingClient(self, timeout, context)
        self.clients.append(connection)
        return connection

class RecordingClient:
    """Implement the exact smtplib boundary used by the transport."""

    __slots__ = ("boundary", "events", "ssl_context", "thread", "timeout")

    def __init__(
        self,
        boundary: SmtpBoundary,
        timeout: int | None,
        context: ssl.SSLContext | None,
    ) -> None:
        self.boundary = boundary
        self.timeout = timeout
        self.ssl_context = context
        self.events: list[tuple[object, ...]] = []
        self.thread = threading.get_ident()

    def _record(self, action: str, *values: object) -> None:
        """Record one protocol step and raise the configured failure."""
        self.events.append((action, *values))
        if self.boundary.failure_at == action:
            raise self.boundary.failure

    def connect(self, host: str, port: int) -> tuple[int, bytes]:
        """Record endpoint selection or raise a connection error."""
        self._record("connect", host, port)
        return self.boundary.status, b"welcome"

    def ehlo_or_helo_if_needed(self) -> None:
        """Record capability negotiation using the standard method name."""
        self._record("ehlo")

    def starttls(self, *, context: ssl.SSLContext) -> None:
        """Record a mandatory STARTTLS upgrade or reject it."""
        self._record("starttls", context)

    def login(self, username: str, password: str) -> None:
        """Record the effective authentication pair."""
        self._record("login", username, password)

    def has_extn(self, name: str) -> bool:
        """Expose the explicitly configured SMTP capabilities."""
        return name in self.boundary.extensions

    def sendmail(
        self,
        sender: str,
        recipients: tuple[str, ...],
        payload: bytes,
        *,
        mail_options: list[str],
    ) -> Mapping[str, tuple[int, bytes]]:
        """Record a transaction and optionally block for cancellation."""
        self._record("sendmail", sender, recipients, payload, mail_options)
        self.boundary.started.set()
        if not self.boundary.release.wait(5):
            error_msg = "Test release event did not arrive."
            raise TimeoutError(error_msg)
        return self.boundary.refused

    def close(self) -> None:
        """Record closure even when closing itself fails."""
        self.events.append(("close",))
        self.boundary.closed.set()
        if self.boundary.close_error:
            error_msg = "Private close failure."
            raise OSError(error_msg)

class TestSmtpTransport(TestCase):

    def setUp(self) -> None:
        """Replace only the SMTP boundary, keeping real protocol errors."""
        self.original = smtp_module.smtplib
        self.boundary = SmtpBoundary()
        smtp_module.smtplib = SimpleNamespace(
            SMTP=self.boundary.plain,
            SMTP_SSL=self.boundary.encrypted,
            SMTPConnectError=smtplib.SMTPConnectError,
            SMTPResponseException=smtplib.SMTPResponseException,
        )

    def tearDown(self) -> None:
        """Release any waiting worker and restore the network boundary."""
        self.boundary.release.set()
        smtp_module.smtplib = self.original

    def buildTransport(self, **options: object) -> SmtpTransport:
        """Build a transport from explicit effective settings."""
        return SmtpTransport(
            SmtpSettings.fromConfig({
                "host": "smtp.example.com",
                "encryption": "TLS",
                **options,
            }),
        )

    async def testStartTlsAndAuthenticationRunOffLoopWithVerifiedContext(self) -> None:
        """
        Upgrade, authenticate, and transmit on a worker thread.

        Validates certificate and hostname verification before DATA.
        """
        transport = self.buildTransport(
            username="user",
            password=_CREDENTIAL,
            timeout=9,
        )
        result = await transport.send(_MESSAGE, mailer="notifications", driver="smtp")
        client = self.boundary.clients[0]

        self.assertNotEqual(client.thread, threading.get_ident())
        self.assertEqual(client.timeout, 9)
        self.assertEqual(
            [event[0] for event in client.events],
            ["connect", "ehlo", "starttls", "ehlo", "login", "sendmail", "close"],
        )

        context = client.events[2][1]
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)

        self.assertEqual(result.status, MailStatus.ACCEPTED)
        self.assertEqual(result.accepted_recipients, _MESSAGE.recipients)
        self.assertIsNone(result.file_path)
        self.assertEqual(result.mailer, "notifications")

    async def testImplicitTlsNeverUsesStartTls(self) -> None:
        """
        Negotiate implicit TLS for the SSL mode.

        Validates that no STARTTLS upgrade is attempted afterwards.
        """
        await self.buildTransport(encryption="ssl").send(
            _MESSAGE,
            mailer="secure",
            driver="smtp",
        )
        client = self.boundary.clients[0]

        self.assertIsInstance(client.ssl_context, ssl.SSLContext)
        self.assertTrue(client.ssl_context.check_hostname)
        self.assertNotIn("starttls", [event[0] for event in client.events])
        self.assertIsNone(client.timeout)

    async def testExplicitPlaintextAndEmptyCredentialsSkipTlsAndLogin(self) -> None:
        """
        Honour an explicit plaintext connection without authenticating.

        Validates that empty credentials never trigger a login.
        """
        await self.buildTransport(encryption="none").send(
            _MESSAGE,
            mailer="local",
            driver="smtp",
        )
        client = self.boundary.clients[0]

        self.assertIsNone(client.ssl_context)
        self.assertEqual(
            [event[0] for event in client.events],
            ["connect", "ehlo", "sendmail", "close"],
        )

    async def testTlsFailureDoesNotFallbackAndStillCloses(self) -> None:
        """
        Abort the operation when the mandatory upgrade fails.

        Validates that no plaintext fallback transmits the message.
        """
        self.boundary.failure_at = "starttls"
        self.boundary.failure = smtplib.SMTPNotSupportedError("unsupported")

        with self.assertRaises(MailTransportException):
            await self.buildTransport().send(_MESSAGE, mailer="smtp", driver="smtp")

        events = [event[0] for event in self.boundary.clients[0].events]
        self.assertNotIn("sendmail", events)
        self.assertEqual(events[-1], "close")
        self.assertEqual(len(self.boundary.clients), 1)

    async def testPartialAcceptanceIsNotReportedAsTotalAcceptance(self) -> None:
        """
        Report only the recipients the server confirmed.

        Validates that rejection reasons are sanitized and redacted.
        """
        self.boundary.refused = {
            "hidden@example.com": (550, b"Rejected\r\nprivate-auth-value"),
        }
        result = await self.buildTransport(
            password=_CREDENTIAL,
            username="user",
        ).send(_MESSAGE, mailer="smtp", driver="smtp")

        self.assertEqual(result.status, MailStatus.PARTIAL)
        self.assertEqual(result.recipients, _MESSAGE.recipients)
        self.assertEqual(result.accepted_recipients, ("ana@example.com",))
        self.assertEqual(
            result.rejected_recipients["hidden@example.com"],
            (550, "Rejected  [redacted]"),
        )

    async def testTotalRejectionRaisesAndCloses(self) -> None:
        """
        Raise instead of returning a falsely successful result.

        Validates that the connection is still closed.
        """
        self.boundary.failure_at = "sendmail"
        self.boundary.failure = smtplib.SMTPRecipientsRefused(
            dict.fromkeys(_MESSAGE.recipients, (550, b"no")),
        )

        with self.assertRaises(MailTransportException):
            await self.buildTransport().send(_MESSAGE, mailer="smtp", driver="smtp")
        self.assertEqual(self.boundary.clients[0].events[-1], ("close",))

    async def testAReportedRejectionOfEveryRecipientAlsoRaises(self) -> None:
        """
        Raise when the transaction reports every recipient as refused.

        Validates that a returned mapping is judged like an exception.
        """
        self.boundary.refused = dict.fromkeys(_MESSAGE.recipients, (550, b"no"))

        with self.assertRaises(MailTransportException):
            await self.buildTransport().send(_MESSAGE, mailer="smtp", driver="smtp")
        self.assertEqual(self.boundary.clients[0].events[-1], ("close",))

    async def testFailuresNeverExposeCredentialsAndCloseErrorsDoNotMaskThem(
        self,
    ) -> None:
        """
        Sanitize every failure stage and keep closing the connection.

        Validates that no credential appears in the reported traceback.
        """
        failures = (
            ("connect", ConnectionRefusedError(_CREDENTIAL)),
            ("connect", TimeoutError(_CREDENTIAL)),
            ("starttls", ssl.SSLError(_CREDENTIAL)),
            ("login", smtplib.SMTPAuthenticationError(535, _CREDENTIAL.encode())),
            ("sendmail", smtplib.SMTPServerDisconnected(_CREDENTIAL)),
            ("sendmail", smtplib.SMTPDataError(554, _CREDENTIAL.encode())),
        )
        self.boundary.close_error = True

        for stage, failure in failures:
            self.boundary.failure_at = stage
            self.boundary.failure = failure
            with self.assertRaises(MailTransportException) as raised:
                await self.buildTransport(
                    username="user",
                    password=_CREDENTIAL,
                ).send(_MESSAGE, mailer="smtp", driver="smtp")

            self.assertNotIn(_CREDENTIAL, str(raised.exception))
            formatted = "".join(traceback.format_exception(raised.exception))
            self.assertNotIn(_CREDENTIAL, formatted)
            self.assertTrue(raised.exception.__suppress_context__)
            self.assertEqual(self.boundary.clients[-1].events[-1], ("close",))

    async def testCloseFailureDoesNotEraseConfirmedAcceptance(self) -> None:
        """
        Keep a confirmed acceptance despite a failing socket close.

        Validates that cleanup never rewrites the transaction outcome.
        """
        self.boundary.close_error = True
        result = await self.buildTransport().send(
            _MESSAGE,
            mailer="smtp",
            driver="smtp",
        )
        self.assertEqual(result.status, MailStatus.ACCEPTED)

    async def testSmtpUtf8IsNegotiatedOrRejectedExplicitly(self) -> None:
        """
        Require the advertised extensions for international mailboxes.

        Validates that no character is dropped when they are missing.
        """
        international = PreparedMail(
            message_id=_MESSAGE.message_id,
            sender="jos\u00e9@example.com",
            recipients=_MESSAGE.recipients,
            mime=_MESSAGE.mime,
            smtp_utf8=True,
        )
        await self.buildTransport().send(international, mailer="smtp", driver="smtp")
        transaction = next(
            event for event in self.boundary.clients[0].events if event[0] == "sendmail"
        )

        self.assertEqual(transaction[1], "jos\u00e9@example.com")
        self.assertEqual(transaction[-1], ["SMTPUTF8", "BODY=8BITMIME"])

        self.boundary.extensions.clear()
        with self.assertRaises(MailTransportException):
            await self.buildTransport().send(
                international,
                mailer="smtp",
                driver="smtp",
            )
        self.assertNotIn(
            "sendmail",
            [event[0] for event in self.boundary.clients[-1].events],
        )
        self.assertEqual(self.boundary.clients[-1].events[-1], ("close",))

    async def testConcurrentSendsNeverShareAConnection(self) -> None:
        """
        Open one independently closed connection per operation.

        Validates that no mutable connection is reused concurrently.
        """
        transport = self.buildTransport(encryption="none")
        results = await asyncio.gather(
            *(
                transport.send(_MESSAGE, mailer="smtp", driver="smtp")
                for _ in range(12)
            ),
        )

        self.assertEqual(len(results), 12)
        self.assertEqual(len({id(client) for client in self.boundary.clients}), 12)
        self.assertTrue(
            all(client.events[-1] == ("close",) for client in self.boundary.clients),
        )

    async def testCancellationPropagatesWhileWorkerFinishesAndCloses(self) -> None:
        """
        Propagate cancellation without claiming the message was refused.

        Validates that the worker still closes its own connection.
        """
        self.boundary.release.clear()
        operation = asyncio.create_task(
            self.buildTransport(encryption="none").send(
                _MESSAGE,
                mailer="smtp",
                driver="smtp",
            ),
        )

        self.assertTrue(await asyncio.to_thread(self.boundary.started.wait, 3))
        operation.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await operation

        self.boundary.release.set()
        self.assertTrue(await asyncio.to_thread(self.boundary.closed.wait, 3))
        self.assertEqual(len(self.boundary.clients), 1)

    async def testInvalidGreetingClosesBeforeAnyTransaction(self) -> None:
        """
        Reject a greeting other than 220 before sending anything.

        Validates that the connection is closed immediately.
        """
        self.boundary.status = 554
        with self.assertRaises(MailTransportException):
            await self.buildTransport().send(_MESSAGE, mailer="smtp", driver="smtp")
        self.assertEqual(
            [event[0] for event in self.boundary.clients[0].events],
            ["connect", "close"],
        )

    async def testPublicManagerUsesTheSameMimeAndCompleteEnvelope(self) -> None:
        """
        Select SMTP centrally and transmit the composed message.

        Validates that hidden recipients stay out of the serialized headers.
        """
        app = MailApplication(
            Path.cwd(),
            {
                "default": "smtp",
                "mailers": {
                    "smtp": {"host": "smtp.example.com", "encryption": "none"},
                },
            },
        )
        composer = MailComposer(
            cast("IViewEngine", object()),
            cast("IStorageManager", object()),
        )
        manager = MailManager(cast("IApplication", app), composer)

        result = await (
            manager.fromAddress("sender@example.com", "Jos\u00e9")
            .to("ana@example.com")
            .cc("other@example.com")
            .bcc("hidden@example.com")
            .replyTo("support@example.com")
            .subject("Aviso \u00fatil")
            .send(Content(text="Hello, \u00e9.", html="<p>Hello, \u00e9.</p>"))
        )
        transaction = next(
            event for event in self.boundary.clients[0].events if event[0] == "sendmail"
        )
        parsed = BytesParser(policy=policy.default).parsebytes(transaction[3])

        self.assertEqual(
            transaction[2],
            ("ana@example.com", "other@example.com", "hidden@example.com"),
        )
        self.assertEqual(parsed["Message-ID"], result.message_id)
        self.assertEqual(parsed["From"].addresses[0].display_name, "Jos\u00e9")
        self.assertEqual(str(parsed["Reply-To"]), "support@example.com")
        self.assertIsNone(parsed["Bcc"])
        self.assertNotIn(b"hidden@example.com", transaction[3])
        self.assertEqual(parsed.get_content_type(), "multipart/alternative")
        self.assertEqual(result.accepted_recipients, transaction[2])

    def testRealSmtplibConstructorsAcceptNoneTimeoutWithoutConnecting(self) -> None:
        """
        Confirm the runtime contract behind the local type suppressions.

        Validates that both constructors accept an unbounded timeout.
        """
        clients = (
            self.original.SMTP(timeout=None, local_hostname="test.example.com"),
            self.original.SMTP_SSL(
                timeout=None,
                local_hostname="test.example.com",
                context=ssl.create_default_context(),
            ),
        )
        for client in clients:
            try:
                self.assertIsNone(client.timeout)
                self.assertIsNone(client.sock)
            finally:
                client.close()
