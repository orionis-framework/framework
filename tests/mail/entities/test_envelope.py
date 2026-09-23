from orionis.mail.entities.address import Address
from orionis.mail.entities.envelope import Envelope
from orionis.mail.exceptions import MailCompositionException
from orionis.test import TestCase

class TestEnvelope(TestCase):

    def testNormalizesEveryDeclaredCollection(self) -> None:
        """
        Convert each recipient declaration into a tuple of addresses.

        Validates that mixed strings and Address values are accepted.
        """
        envelope = Envelope(
            subject="Welcome",
            from_address="sender@example.com",
            to=[Address("ana@example.com", "Ana"), "luis@example.com"],
            cc="cc@example.com",
            bcc=("hidden@example.com",),
            reply_to="support@example.com",
        )
        self.assertEqual(envelope.subject, "Welcome")
        self.assertEqual(envelope.from_address.address, "sender@example.com")
        self.assertEqual(len(envelope.to), 2)
        self.assertEqual(envelope.cc[0].address, "cc@example.com")
        self.assertEqual(envelope.bcc[0].address, "hidden@example.com")
        self.assertEqual(envelope.reply_to[0].address, "support@example.com")

    def testDefaultsToAnEmptyDeclaration(self) -> None:
        """
        Build an empty envelope without a sender or recipients.

        Validates the starting point used when merging fluent options.
        """
        envelope = Envelope()
        self.assertEqual(envelope.subject, "")
        self.assertIsNone(envelope.from_address)
        self.assertEqual(envelope.recipients(), ())

    def testCopiesSuppliedCollections(self) -> None:
        """
        Detach recipient collections from the caller's list.

        Validates that mutating the original list never changes the envelope.
        """
        recipients = ["a@example.com"]
        envelope = Envelope(to=recipients)
        recipients.append("late@example.com")
        self.assertEqual(envelope.recipients(), ("a@example.com",))

    def testTransportRecipientsExcludeReplyTo(self) -> None:
        """
        Build the transport union from To, Cc, and Bcc only.

        Validates that duplicates are removed while order is preserved.
        """
        envelope = Envelope(
            to=["a@example.com", "b@example.com"],
            cc="a@example.com",
            bcc="c@example.com",
            reply_to="support@example.com",
        )
        self.assertEqual(
            envelope.recipients(),
            ("a@example.com", "b@example.com", "c@example.com"),
        )

    def testRejectsHiddenAndVisibleConflicts(self) -> None:
        """
        Reject a mailbox declared as both a visible recipient and Bcc.

        Validates that the intended privacy of a message stays unambiguous.
        """
        with self.assertRaises(MailCompositionException):
            Envelope(to="a@example.com", bcc="a@example.com")
        with self.assertRaises(MailCompositionException):
            Envelope(cc="a@example.com", bcc="a@example.com")

    def testRejectsUnsafeSubjectsAndSenders(self) -> None:
        """
        Reject header injection in the subject and an invalid sender.

        Validates that envelopes never carry control characters.
        """
        with self.assertRaises(MailCompositionException):
            Envelope(subject="Title\nBcc: x@y")
        with self.assertRaises(MailCompositionException):
            Envelope(from_address="not-a-mailbox")
