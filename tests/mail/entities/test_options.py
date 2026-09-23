from dataclasses import replace
from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.envelope import Envelope
from orionis.mail.entities.options import MailOptions
from orionis.mail.exceptions import MailCompositionException
from orionis.test import TestCase

class TestMailOptions(TestCase):

    def testEmptyOptionsProduceAnEmptyEnvelope(self) -> None:
        """
        Build an empty envelope when nothing was declared.

        Validates the default state of a fresh chain.
        """
        options = MailOptions()
        envelope = options.envelope()
        self.assertIsNone(options.mailer)
        self.assertEqual(options.attachments, ())
        self.assertEqual(envelope.subject, "")
        self.assertIsNone(envelope.from_address)

    def testExplicitScalarsReplaceTheDeclaredOnes(self) -> None:
        """
        Overlay the sender and subject supplied through the chain.

        Validates that an explicitly empty subject also wins.
        """
        base = Envelope(subject="Declared", from_address="declared@example.com")
        options = MailOptions(
            from_address=Address("explicit@example.com"),
            subject="",
        )
        envelope = options.envelope(base)
        self.assertEqual(envelope.subject, "")
        self.assertEqual(envelope.from_address.address, "explicit@example.com")

    def testAbsentScalarsKeepTheDeclaredValues(self) -> None:
        """
        Preserve declared values when the chain supplied none.

        Validates that None means "not supplied" instead of "clear".
        """
        base = Envelope(subject="Declared", from_address="declared@example.com")
        envelope = MailOptions().envelope(base)
        self.assertEqual(envelope.subject, "Declared")
        self.assertEqual(envelope.from_address.address, "declared@example.com")

    def testRecipientCollectionsAreAppended(self) -> None:
        """
        Append chain recipients after the declared ones.

        Validates that merging never drops a declared recipient.
        """
        base = Envelope(
            to="declared@example.com",
            cc="declared-cc@example.com",
            bcc="declared-bcc@example.com",
            reply_to="declared-reply@example.com",
        )
        options = MailOptions(
            to=(Address("chain@example.com"),),
            cc=(Address("chain-cc@example.com"),),
            bcc=(Address("chain-bcc@example.com"),),
            reply_to=(Address("chain-reply@example.com"),),
        )
        envelope = options.envelope(base)
        self.assertEqual(
            envelope.recipients(),
            (
                "declared@example.com",
                "chain@example.com",
                "declared-cc@example.com",
                "chain-cc@example.com",
                "declared-bcc@example.com",
                "chain-bcc@example.com",
            ),
        )
        self.assertEqual(len(envelope.reply_to), 2)

    def testMergedPrivacyConflictsAreRejected(self) -> None:
        """
        Reject a merge that makes a hidden recipient visible.

        Validates that privacy rules also apply to combined declarations.
        """
        base = Envelope(bcc="ana@example.com")
        options = MailOptions(to=(Address("ana@example.com"),))
        with self.assertRaises(MailCompositionException):
            options.envelope(base)

    def testReplacingOptionsLeavesTheOriginalIntact(self) -> None:
        """
        Derive new options without mutating the previous snapshot.

        Validates the immutability the fluent chains depend on.
        """
        options = MailOptions(mailer="file")
        derived = replace(
            options,
            attachments=(Attachment.fromStorage("guide.pdf"),),
        )
        self.assertEqual(options.attachments, ())
        self.assertEqual(len(derived.attachments), 1)
        self.assertEqual(derived.mailer, "file")
