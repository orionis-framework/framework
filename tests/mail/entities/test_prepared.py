from dataclasses import FrozenInstanceError
from orionis.mail.entities.prepared import PreparedMail
from orionis.test import TestCase

class TestPreparedMail(TestCase):

    def testCarriesMimeAndTransportEnvelopeSeparately(self) -> None:
        """
        Expose serialized bytes beside the transport recipient union.

        Validates the only data a transport receives.
        """
        prepared = PreparedMail(
            message_id="<id@example.com>",
            sender="sender@example.com",
            recipients=("ana@example.com", "hidden@example.com"),
            mime=b"Subject: Hello\r\n\r\nBody\r\n",
            smtp_utf8=False,
        )
        self.assertEqual(prepared.message_id, "<id@example.com>")
        self.assertEqual(prepared.sender, "sender@example.com")
        self.assertEqual(len(prepared.recipients), 2)
        self.assertIsInstance(prepared.mime, bytes)
        self.assertFalse(prepared.smtp_utf8)

    def testIsFrozenAndSlotted(self) -> None:
        """
        Reject mutation and keep instances free of attribute dictionaries.

        Validates that a prepared message cannot be altered by a transport.
        """
        prepared = PreparedMail(
            message_id="<id@example.com>",
            sender="sender@example.com",
            recipients=(),
            mime=b"",
            smtp_utf8=True,
        )
        self.assertFalse(hasattr(prepared, "__dict__"))
        with self.assertRaises(FrozenInstanceError):
            prepared.mime = b"replaced"
