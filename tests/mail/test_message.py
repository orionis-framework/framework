from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.options import MailOptions
from orionis.mail.exceptions import MailCompositionException
from orionis.mail.message import Message
from orionis.test import TestCase

class TestMessage(TestCase):

    def setUp(self) -> None:
        """Create a configurator that starts from an empty declaration."""
        self.message = Message()

    def testEveryMutatorReturnsTheSameInstance(self) -> None:
        """
        Return the received configurator from every mutator.

        Validates that a callback can chain calls on one message.
        """
        mutations = (
            self.message.fromAddress("sender@example.com"),
            self.message.to("ana@example.com"),
            self.message.cc("cc@example.com"),
            self.message.bcc("hidden@example.com"),
            self.message.replyTo("support@example.com"),
            self.message.subject("Notice"),
            self.message.attach(Attachment.fromStorage("guide.pdf")),
        )
        for mutation in mutations:
            self.assertIs(mutation, self.message)

    def testBuildsTheDeclaredEnvelope(self) -> None:
        """
        Collect every declared field into one envelope.

        Validates the declaration handed to the delivery pipeline.
        """
        self.message.fromAddress("sender@example.com", "Sender")
        self.message.to(["ana@example.com", "luis@example.com"])
        self.message.cc("cc@example.com")
        self.message.bcc("hidden@example.com")
        self.message.replyTo("support@example.com")
        self.message.subject("Notice")

        envelope = self.message._snapshot().envelope()
        self.assertEqual(envelope.subject, "Notice")
        self.assertEqual(envelope.from_address.name, "Sender")
        self.assertEqual(
            envelope.recipients(),
            (
                "ana@example.com",
                "luis@example.com",
                "cc@example.com",
                "hidden@example.com",
            ),
        )
        self.assertEqual(envelope.reply_to[0].address, "support@example.com")

    def testScalarsAreReplacedAndCollectionsAccumulate(self) -> None:
        """
        Replace the sender and subject while appending recipients.

        Validates the documented merge rules of successive calls.
        """
        self.message.fromAddress("first@example.com").fromAddress("last@example.com")
        self.message.subject("first").subject("last")
        self.message.to("a@example.com").to(Address("b@example.com"))
        self.message.attach(Attachment.fromStorage("a.pdf"))
        self.message.attach(Attachment.fromStorage("b.pdf"))

        options = self.message._snapshot()
        self.assertEqual(options.from_address.address, "last@example.com")
        self.assertEqual(options.subject, "last")
        self.assertEqual(len(options.to), 2)
        self.assertEqual(len(options.attachments), 2)

    def testStartsFromTheSuppliedChainSnapshot(self) -> None:
        """
        Continue the declaration supplied by a pending chain.

        Validates that a callback receives the chain state.
        """
        options = MailOptions(mailer="file", to=(Address("chain@example.com"),))
        message = Message(options)
        message.to("callback@example.com")

        snapshot = message._snapshot()
        self.assertEqual(snapshot.mailer, "file")
        self.assertEqual(len(snapshot.to), 2)

    def testSnapshotsAreImmutableAndDetached(self) -> None:
        """
        Detach a snapshot from later mutations of the configurator.

        Validates that a captured declaration cannot change afterwards.
        """
        self.message.subject("before")
        snapshot = self.message._snapshot()
        self.message.subject("after")

        self.assertEqual(snapshot.subject, "before")
        self.assertEqual(self.message._snapshot().subject, "after")
        self.assertFalse(hasattr(self.message, "__dict__"))

    def testRejectsInvalidDeclarations(self) -> None:
        """
        Reject unsafe headers, ambiguous names, and invalid attachments.

        Validates that mutators fail immediately instead of at send time.
        """
        with self.assertRaises(MailCompositionException):
            self.message.subject("Notice\r\nBcc: x@y")
        with self.assertRaises(MailCompositionException):
            self.message.to(Address("ana@example.com"), "Ana")
        with self.assertRaises(MailCompositionException):
            self.message.fromAddress("not-a-mailbox")
        with self.assertRaises(MailCompositionException):
            self.message.attach("guide.pdf")

    def testDoesNotExposeForbiddenSenderAliases(self) -> None:
        """
        Expose one canonical sender method and no alias.

        Validates the naming rule of the public composition API.
        """
        for name in ("from_", "from", "From", "sender", "setFrom"):
            self.assertFalse(hasattr(self.message, name))
        self.assertTrue(callable(self.message.fromAddress))
