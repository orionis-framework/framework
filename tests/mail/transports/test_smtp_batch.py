import smtplib
from typing import TYPE_CHECKING, Self
from unittest.mock import patch
from orionis.mail.entities.smtp_settings import SmtpSettings
from orionis.mail.exceptions import MailBatchException
from orionis.mail.transports.smtp import SmtpTransport
from orionis.test import TestCase
from tests.mail.transports.test_smtp import _MESSAGE, RecordingClient, SmtpBoundary

if TYPE_CHECKING:
    from collections.abc import Mapping

class TestSmtpBatch(TestCase):
    """Reuse one SMTP connection while retaining partial outcomes without retries."""

    async def testOneConnectionForManyMessages(self: Self) -> None:
        """
        Authenticate once and send each envelope independently.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        boundary = SmtpBoundary()
        transport = SmtpTransport(
            SmtpSettings.fromConfig(
                {
                    "host": "smtp.example.test",
                    "encryption": "TLS",
                    "username": "user",
                    "password": "test-only",
                    "timeout": 3,
                },
            ),
        )
        with patch("orionis.mail.transports.smtp.smtplib.SMTP", boundary.plain):
            results = await transport.sendMany(
                [_MESSAGE] * 5,
                mailer="test",
                driver="smtp",
            )
        self.assertEqual(len(results), 5)
        self.assertEqual(len(boundary.clients), 1)
        actions = [event[0] for event in boundary.clients[0].events]
        self.assertEqual(actions.count("login"), 1)
        self.assertEqual(actions.count("sendmail"), 5)
        self.assertEqual(actions[-1], "close")

    async def testFailureRetainsAcceptedPrefixAndStopsWithoutRetry(self: Self) -> None:
        """
        Expose the uncertain message without duplicating accepted deliveries.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        boundary = SmtpBoundary()
        transport = SmtpTransport(
            SmtpSettings.fromConfig({"host": "test", "encryption": "none"}),
        )
        calls = 0
        original = RecordingClient.sendmail

        def send(
            client: RecordingClient, *args: object, **kwargs: object,
        ) -> Mapping[str, tuple[int, bytes]]:
            """
            Disconnect on the second delivery and forward all earlier sends.

            Parameters
            ----------
            client : RecordingClient
                Recording SMTP client sending the message.
            *args : object
                Positional arguments forwarded to the wrapped operation.
            **kwargs : object
                Keyword arguments forwarded to the wrapped operation.

            Returns
            -------
            Mapping[str, tuple[int, bytes]]
                Recipient rejection details returned by the recording SMTP client.
            """
            nonlocal calls
            calls += 1
            if calls == 2:
                error_msg = "disconnected"
                raise smtplib.SMTPServerDisconnected(error_msg)
            return original(client, *args, **kwargs)

        with (
            patch("orionis.mail.transports.smtp.smtplib.SMTP", boundary.plain),
            patch.object(RecordingClient, "sendmail", send),
            self.assertRaises(MailBatchException) as raised,
        ):
            await transport.sendMany([_MESSAGE] * 5, mailer="test", driver="smtp")
        self.assertEqual(len(raised.exception.completed), 1)
        self.assertEqual(raised.exception.failed_index, 1)
        self.assertEqual(calls, 2)
        self.assertTrue(boundary.closed.is_set())
        with self.assertRaises(ValueError):
            await transport.sendMany([_MESSAGE] * 101, mailer="test", driver="smtp")
