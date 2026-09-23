import asyncio
from inspect import CORO_CLOSED, getcoroutinestate
from typing import TYPE_CHECKING
from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.envelope import Envelope
from orionis.mail.exceptions import MailCompositionException, MailConfigurationException
from orionis.mail.mailable import Mailable
from orionis.mail.message import Message
from orionis.mail.pending import PendingMail
from orionis.test import TestCase
from tests.mail.fixtures.doubles import RecordingDelivery

if TYPE_CHECKING:
    from collections.abc import Sequence

class WelcomeMail(Mailable):
    """Declare a reusable message with an envelope, bodies, and a guide."""

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def envelope(self) -> Envelope:
        """Declare reusable initial headers."""
        return Envelope(
            subject="Welcome",
            from_address="original@example.com",
            to="original-recipient@example.com",
        )

    def content(self) -> Content:
        """Declare reusable view and text alternatives."""
        return Content(
            view="emails.welcome",
            text=f"Hello, {self.name}",
            data={"name": self.name},
        )

    def attachments(self) -> list[Attachment]:
        """Declare a deferred guide attachment."""
        return [Attachment.fromStorage("documents/guide.pdf")]

class PlainMail(Mailable):
    """Declare complete headers while keeping the default attachments."""

    __slots__ = ()

    def envelope(self) -> Envelope:
        """Provide a complete envelope without fluent configuration."""
        return Envelope(from_address="a@example.com", to="b@example.com")

    def content(self) -> Content:
        """Provide literal text without any I/O."""
        return Content(text="plain")

class InvalidMail(PlainMail):
    """Supply configurable contract violations without a fake transport."""

    __slots__ = ("content_value", "envelope_value", "failure", "items")

    def __init__(self) -> None:
        self.envelope_value: object = super().envelope()
        self.content_value: object = super().content()
        self.failure: Exception | None = None
        self.items: object = ()

    def envelope(self) -> Envelope:
        """Return the deliberately supplied declaration value."""
        if self.failure is not None:
            raise self.failure
        return self.envelope_value

    def content(self) -> Content:
        """Return the deliberately supplied content value."""
        return self.content_value

    def attachments(self) -> Sequence[Attachment]:
        """Return the deliberately supplied attachment declaration."""
        return self.items

class Callback:
    """Record invocations and return the outcome configured by a test."""

    __slots__ = ("calls", "failure", "received", "result")

    def __init__(self) -> None:
        self.calls = 0
        self.received: list[Message] = []
        self.result: object = None
        self.failure: Exception | None = None

    def __call__(self, message: Message) -> object:
        """Configure headers once and return the requested outcome."""
        self.calls += 1
        self.received.append(message)
        message.subject("Callback").to("callback@example.com")
        if self.failure:
            raise self.failure
        return message if self.result == "self" else self.result

    async def configure(self, message: Message) -> object:
        """Expose the same behavior through an awaitable bound method."""
        await asyncio.sleep(0)
        return self(message)

class TestPendingMail(TestCase):

    def setUp(self) -> None:
        """Create an isolated recorder and an empty pending chain."""
        self.delivery = RecordingDelivery()
        self.base = PendingMail(self.delivery).mailer("archive")

    def testEveryFluentEntryReturnsANewIndependentChain(self) -> None:
        """
        Return a new chain from every composition method.

        Validates that chains are values instead of mutable builders.
        """
        entries = (
            self.base.mailer("file"),
            self.base.fromAddress("a@example.com"),
            self.base.to("a@example.com"),
            self.base.cc("a@example.com"),
            self.base.bcc("a@example.com"),
            self.base.replyTo("a@example.com"),
            self.base.subject("Notice"),
            self.base.attach(Attachment.fromStorage("guide.pdf")),
        )
        for chain in entries:
            self.assertIsInstance(chain, PendingMail)
            self.assertIsNot(chain, self.base)

    async def testDerivationsAreIndependentAndConcurrent(self) -> None:
        """
        Keep a reusable chain free of recipients added by its children.

        Validates that concurrent branches never mix recipients.
        """
        base = self.base.fromAddress("sender@example.com").subject("Notice")
        first = base.to("ana@example.com")
        second = base.to("luis@example.com")

        await asyncio.gather(first.raw("Ana"), second.html("<p>Luis</p>"))
        await base.to("third@example.com").raw("third")

        self.assertEqual(
            [item[1].recipients() for item in self.delivery.messages],
            [("ana@example.com",), ("luis@example.com",), ("third@example.com",)],
        )

    async def testMailableMergeReplacesScalarsAndAppendsCollections(self) -> None:
        """
        Overlay explicit scalars and append recipients and attachments.

        Validates that sending never mutates the reusable declaration.
        """
        mailable = WelcomeMail("Ana")
        await (
            self.base.fromAddress(Address("new@example.com", "New"))
            .subject("")
            .to("ana@example.com")
            .cc("cc@example.com")
            .bcc("hidden@example.com")
            .replyTo("support@example.com")
            .attach(Attachment.fromStorage("extra.pdf"))
            .send(mailable)
        )
        _, envelope, content, attachments = self.delivery.messages[0]

        self.assertEqual(envelope.subject, "")
        self.assertEqual(envelope.from_address.address, "new@example.com")
        self.assertEqual(
            envelope.recipients(),
            (
                "original-recipient@example.com",
                "ana@example.com",
                "cc@example.com",
                "hidden@example.com",
            ),
        )
        self.assertEqual(len(attachments), 2)
        self.assertEqual(content.data["name"], "Ana")
        self.assertEqual(mailable.envelope().subject, "Welcome")

    async def testStringContentAndLiteralTerminals(self) -> None:
        """
        Keep views, Content, and literal bodies unambiguous.

        Validates that a literal is never interpreted as a template.
        """
        await self.base.send("emails.welcome", {"name": "Ana"})
        await self.base.send(Content(html="{{ literal }}", text="{{ literal }}"))
        await self.base.raw("{{ literal }}")
        await self.base.html("{{ literal }}")
        contents = [item[2] for item in self.delivery.messages]

        self.assertEqual(contents[0].view, "emails.welcome")
        self.assertEqual(contents[0].data["name"], "Ana")
        self.assertEqual(contents[1].html, "{{ literal }}")
        self.assertEqual(contents[2].text, "{{ literal }}")
        self.assertEqual(contents[3].html, "{{ literal }}")

    async def testSelectedMailerTravelsWithTheOperation(self) -> None:
        """
        Forward the selected mailer to the delivery pipeline.

        Validates that no mailer is resolved before a terminal call.
        """
        await self.base.fromAddress("a@example.com").to("b@example.com").raw("text")
        await PendingMail(self.delivery).fromAddress("a@example.com").to(
            "b@example.com",
        ).raw("text")

        self.assertEqual(
            [item[0] for item in self.delivery.messages],
            ["archive", None],
        )

    async def testDefaultAttachmentsAndSuccessiveScalarReplacement(self) -> None:
        """
        Use the last fluent scalar and the default empty attachments.

        Validates the merge rules for repeated composition calls.
        """
        await (
            self.base.fromAddress("first@example.com")
            .fromAddress("last@example.com")
            .subject("first")
            .subject("last")
            .send(PlainMail())
        )
        _, envelope, _, attachments = self.delivery.messages[0]

        self.assertEqual(envelope.from_address.address, "last@example.com")
        self.assertEqual(envelope.subject, "last")
        self.assertEqual(attachments, ())

    async def testCallbacksAreCalledOnceAndTheirAwaitablesAreAwaited(self) -> None:
        """
        Invoke callable objects and async methods exactly once.

        Validates that a captured message cannot change a sent operation.
        """
        callback = Callback()
        await self.base.subject("base").to("base@example.com").raw("one", callback)
        callback.result = "self"
        await self.base.html("two", callback.configure)

        self.assertEqual(callback.calls, 2)
        self.assertIsNot(callback.received[0], callback.received[1])
        self.assertEqual(self.delivery.messages[0][1].subject, "Callback")
        self.assertEqual(
            self.delivery.messages[0][1].recipients(),
            ("base@example.com", "callback@example.com"),
        )

        callback.received[0].subject("late")
        self.assertEqual(self.delivery.messages[0][1].subject, "Callback")

    async def testCallbackScalarsOverrideAndForeignMessageReturnFails(self) -> None:
        """
        Let callback scalars win and reject a foreign Message return.

        Validates that only None or the received message are accepted.
        """
        def configure(message: Message) -> Message:
            return (
                message.fromAddress("callback@example.com")
                .subject("")
                .attach(Attachment.fromStorage("extra.pdf"))
            )

        await (
            self.base.fromAddress("base@example.com")
            .subject("base")
            .raw("text", configure)
        )
        _, envelope, _, attachments = self.delivery.messages[0]

        self.assertEqual(envelope.from_address.address, "callback@example.com")
        self.assertEqual(envelope.subject, "")
        self.assertEqual(len(attachments), 1)

        callback = Callback()
        callback.result = Message()
        with self.assertRaises(MailCompositionException):
            await self.base.raw("invalid result", callback)
        self.assertEqual(len(self.delivery.messages), 1)

    async def testCallbackFailureOrInvalidReturnNeverDelivers(self) -> None:
        """
        Reject a false return value and a failing callback.

        Validates that neither reaches the delivery pipeline.
        """
        callback = Callback()
        callback.result = False
        with self.assertRaises(MailCompositionException):
            await self.base.raw("text", callback)

        callback.failure = ValueError("private callback failure")
        with self.assertRaises(MailCompositionException):
            await self.base.raw("text", callback.configure)

        self.assertEqual(callback.calls, 2)
        self.assertEqual(self.delivery.messages, [])

    async def testCompositionFailuresRaisedByACallbackKeepTheirIdentity(self) -> None:
        """
        Propagate a composition failure raised inside a callback unchanged.

        Validates that a precise message is not replaced by a generic one.
        """
        callback = Callback()
        callback.failure = MailCompositionException("explicit callback rejection")
        with self.assertRaises(MailCompositionException) as raised:
            await self.base.raw("text", callback)

        self.assertIs(raised.exception, callback.failure)
        self.assertIsNone(raised.exception.__cause__)
        self.assertEqual(self.delivery.messages, [])

    async def testRejectsInvalidTerminalArgumentCombinations(self) -> None:
        """
        Reject ignored arguments even when they are explicitly None.

        Validates that an invalid combination fails instead of being dropped.
        """
        invalid_calls = (
            self.base.send(WelcomeMail("Ana"), None),
            self.base.send(WelcomeMail("Ana"), callback=None),
            self.base.send(Content(text=""), None),
            self.base.send(123),
            self.base.raw("text", False),
        )
        for operation in invalid_calls:
            with self.assertRaises(MailCompositionException):
                await operation
        self.assertEqual(self.delivery.messages, [])

    def testRejectsInvalidMailerAndAttachmentDeclarations(self) -> None:
        """
        Fail immediately on invalid fluent declarations.

        Validates that composition performs no deferred validation.
        """
        for value in (None, 1, ""):
            with self.assertRaises(MailConfigurationException):
                self.base.mailer(value)
        with self.assertRaises(MailCompositionException):
            self.base.attach("file.pdf")

    async def testInvalidDeclarationsCannotReachDelivery(self) -> None:
        """
        Reject declarations that violate their synchronous contract.

        Validates that the Mailable itself is never mutated.
        """
        for field, value in (
            ("envelope_value", None),
            ("content_value", "text"),
            ("items", None),
            ("items", ["not an attachment"]),
        ):
            mailable = InvalidMail()
            setattr(mailable, field, value)
            with self.assertRaises(MailCompositionException):
                await self.base.send(mailable)
        self.assertEqual(self.delivery.messages, [])

    async def testAsyncDeclarationIsRejectedAndItsCoroutineClosed(self) -> None:
        """
        Reject an asynchronous declaration without leaking a coroutine.

        Validates that no "never awaited" warning can be produced.
        """
        async def declaration() -> Envelope:
            return Envelope()

        value = declaration()
        mailable = InvalidMail()
        mailable.envelope_value = value

        with self.assertRaises(MailCompositionException):
            await self.base.send(mailable)
        self.assertEqual(getcoroutinestate(value), CORO_CLOSED)
        self.assertEqual(self.delivery.messages, [])

    async def testDeclarationExceptionsKeepTheirCauseAndPreventDelivery(self) -> None:
        """
        Translate a failing declaration into a composition failure.

        Validates that the original cause is preserved.
        """
        mailable = InvalidMail()
        mailable.failure = ValueError("declaration failure")

        with self.assertRaises(MailCompositionException) as raised:
            await self.base.send(mailable)
        self.assertIs(raised.exception.__cause__, mailable.failure)
        self.assertEqual(self.delivery.messages, [])

    async def testCallbackCancellationNeverContinuesToDelivery(self) -> None:
        """
        Propagate cancellation instead of translating it.

        Validates that a cancelled operation never delivers.
        """
        async def cancel(_message: Message) -> None:
            raise asyncio.CancelledError

        with self.assertRaises(asyncio.CancelledError):
            await self.base.raw("text", cancel)
        self.assertEqual(self.delivery.messages, [])
