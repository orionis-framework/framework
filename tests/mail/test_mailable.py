from abc import ABC
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.envelope import Envelope
from orionis.mail.mailable import Mailable
from orionis.test import TestCase

class WelcomeMail(Mailable):
    """Declare a minimal reusable message without overriding attachments."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def envelope(self) -> Envelope:
        """Declare the headers of the reusable message."""
        return Envelope(from_address="no-reply@example.com", subject="Welcome")

    def content(self) -> Content:
        """Declare the bodies of the reusable message."""
        return Content(view="emails.welcome", text=f"Hello, {self.name}.")

class TestMailable(TestCase):

    def testRequiresTheTwoDeclarativeMethods(self) -> None:
        """
        Require an envelope and a content declaration in every subclass.

        Validates that an incomplete Mailable cannot be instantiated.
        """
        self.assertTrue(issubclass(Mailable, ABC))
        self.assertEqual(
            Mailable.__abstractmethods__,
            frozenset({"envelope", "content"}),
        )
        with self.assertRaises(TypeError):
            Mailable()

    def testAttachmentsDefaultToAnEmptySequence(self) -> None:
        """
        Return no attachments unless a subclass declares them.

        Validates the optional part of the declarative contract.
        """
        mailable = WelcomeMail("Ana")
        self.assertEqual(mailable.attachments(), ())

    def testSubclassesDeclareTheirOwnAttachments(self) -> None:
        """
        Let a subclass replace the default attachment declaration.

        Validates that declarations stay synchronous and side-effect free.
        """

        class GuideMail(WelcomeMail):
            __slots__ = ()

            def attachments(self) -> list[Attachment]:
                """Declare one deferred storage attachment."""
                return [Attachment.fromStorage("documents/guide.pdf")]

        attachments = GuideMail("Ana").attachments()
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].path, "documents/guide.pdf")

    def testDeclarationsAreRepeatableAndDoNotMutateTheInstance(self) -> None:
        """
        Produce an equivalent declaration on every call.

        Validates that a Mailable can be reused for concurrent sends.
        """
        mailable = WelcomeMail("Ana")
        first = mailable.envelope()
        second = mailable.envelope()

        self.assertIsNot(first, second)
        self.assertEqual(first, second)
        self.assertEqual(mailable.content().text, "Hello, Ana.")
        self.assertEqual(mailable.name, "Ana")

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots on the abstract base class.

        Validates that subclasses control their own attribute layout.
        """
        self.assertEqual(Mailable.__slots__, ())
        self.assertFalse(hasattr(WelcomeMail("Ana"), "__dict__"))
