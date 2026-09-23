import asyncio
import json
import smtplib
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import TYPE_CHECKING
from orionis import Application
from orionis.container.providers import ServiceProvider
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.responses import Response
from orionis.mail import (
    Address, Attachment, Content, Envelope, Mailable, MailResult, Message, PendingMail,
)
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.enums.status import MailStatus
from orionis.storage.contracts.manager import IStorageManager
from orionis.support.facades.mail import Mail

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.foundation.contracts.application import IApplication
    from orionis.mail.entities.prepared import PreparedMail

_PDF = b"%PDF-1.4\nMail integration fixture\n%%EOF\n"


class WelcomeMail(Mailable):
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def envelope(self) -> Envelope:
        """Declare the example sender and subject."""
        return Envelope(
            from_address=Address("no-reply@example.com", "Example App"),
            subject="Welcome",
        )

    def content(self) -> Content:
        """Declare the example view and plain-text alternative."""
        return Content(
            view="emails.welcome", data={"name": self.name},
            text=f"Hello, {self.name}. Welcome to our application.",
        )

    def attachments(self) -> list[Attachment]:
        """Declare a guide resolved from the actual configured storage disk."""
        return [Attachment.fromStorage(
            "documents/guide.pdf", disk="local", name="guide.pdf",
            mime_type="application/pdf",
        )]


class CompleteWelcomeMail(WelcomeMail):
    __slots__ = ()

    def envelope(self) -> Envelope:
        """Declare a self-contained envelope accepted by Mail.send(mailable)."""
        return Envelope(from_address="no-reply@example.com", subject="Complete",
                        to="ana@example.com")


async def send_welcome() -> MailResult:
    """Execute the reusable Mailable acceptance example."""
    return await Mail.mailer("file").to(Address("ana@example.com", "Ana")).send(
        WelcomeMail("Ana"),
    )


def configure_welcome(message: Message) -> None:
    """Configure the direct controller example with every envelope field."""
    message.fromAddress("no-reply@example.com", "Example App")
    message.to("ana@example.com", "Ana")
    message.cc("operations@example.com")
    message.bcc("audit@example.com")
    message.replyTo("support@example.com")
    message.subject("Welcome")
    message.attach(Attachment.fromStorage(
        "documents/guide.pdf", disk="local", name="guide.pdf",
        mime_type="application/pdf",
    ))


class WelcomeController(BaseController):
    __slots__ = ()

    async def sendWelcome(self) -> HttpResponse:
        """Return a real JSON response after awaiting the direct view send."""
        result = await Mail.send("emails.welcome", {"name": "Ana"}, configure_welcome)
        return response.json({"message_id": result.message_id, "status": result.status})


class InvoiceDeliveryService:
    __slots__ = ()

    async def sendInvoice(
        self, recipient: str, invoice_number: str, attachment_path: str,
    ) -> MailResult:
        """Execute the fluent Content-and-attachment acceptance example."""
        return await (
            Mail.mailer("file").fromAddress("billing@example.com", "Example Billing")
            .to(recipient).subject(f"Invoice {invoice_number}")
            .attach(Attachment.fromStorage(
                attachment_path, disk="local", name=f"invoice-{invoice_number}.pdf",
                mime_type="application/pdf",
            )).send(Content(
                view="emails.invoice", data={"invoice_number": invoice_number},
                text=f"Your invoice {invoice_number} is attached.",
            ))
        )


async def send_notifications() -> None:
    """Execute both literal-body examples without a callback or Mailable."""
    await (Mail.fromAddress("notifications@example.com", "Example App")
           .to("ana@example.com").subject("Report ready").raw("Your report is ready."))
    await (Mail.fromAddress("notifications@example.com", "Example App")
           .to("ana@example.com").subject("Report ready")
           .html("<h1>Your report is ready.</h1>"))


class NotificationService:
    __slots__ = ()

    async def configureMessage(self, message: Message) -> None:
        """Configure values through the required asynchronous bound callback."""
        message.fromAddress("notifications@example.com", "Example App")
        message.to("ana@example.com")
        message.subject("Notification")

    async def sendNotification(self) -> MailResult:
        """Await the asynchronous callback before sending literal text."""
        return await Mail.mailer("file").raw(
            "Your notification is ready.", self.configureMessage,
        )


async def send_independent_messages() -> None:
    """Execute concurrent derivations of the same immutable fluent chain."""
    base = (Mail.mailer("file").fromAddress("notifications@example.com", "Example App")
            .subject("Notification"))
    first = base.to("ana@example.com")
    second = base.to("luis@example.com")
    await asyncio.gather(first.raw("Hello, Ana."), second.raw("Hello, Luis."))


class AlertService:
    __slots__ = ("__mail",)

    def __init__(self, mail: IMailManager) -> None:
        self.__mail = mail

    async def sendAlert(self, recipient: str) -> MailResult:
        """Send using the contract injected by the real framework container."""
        return await (self.__mail.fromAddress("alerts@example.com", "Example App")
                      .to(recipient).subject("Service alert")
                      .raw("A service alert requires your attention."))


class RecordingSink:
    __slots__ = ("messages",)

    def __init__(self) -> None:
        self.messages: list[PreparedMail] = []


class RecordingTransport(IMailTransport):
    __slots__ = ("sink",)

    def __init__(self, sink: RecordingSink) -> None:
        self.sink = sink

    async def send(
        self, message: PreparedMail, *, mailer: str, driver: str,
    ) -> MailResult:
        """Record one prepared operation without bypassing public driver resolution."""
        self.sink.messages.append(message)
        return MailResult(message_id=message.message_id, mailer=mailer, driver=driver,
                          status=MailStatus.STORED, recipients=message.recipients)


async def recording_factory(
    app: IApplication, config: Mapping[str, object],
) -> IMailTransport:
    """Resolve a driver dependency using the documented factory signature."""
    if config["label"] != "provider-extension":
        error_msg = "The factory did not receive its normalized central config."
        raise AssertionError(error_msg)
    return await app.make(RecordingTransport)


class RecordingProvider(ServiceProvider):
    __slots__ = ()

    def register(self) -> None:
        """Register test-only transport dependencies during normal startup."""
        self.app.singleton(RecordingSink, RecordingSink)
        self.app.singleton(RecordingTransport, RecordingTransport)

    async def boot(self) -> None:
        """Extend the already registered manager before the driver's first use."""
        manager = await self.app.make(IMailManager)
        manager.extend("recording", recording_factory)


def forbid_smtp(*_args: object, **_kwargs: object) -> None:
    """Fail if a file-only example attempts any SMTP connection."""
    error_msg = "File-only examples must not construct an SMTP connection."
    raise AssertionError(error_msg)


def semantic_content(path: Path) -> list[tuple[object, ...]]:
    """Compare MIME structure and payloads without operation-specific boundaries."""
    parsed = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    return [
        (part.get_content_type(), part.get_content_disposition(),
         part.get_filename(), part.get_payload(decode=True))
        for part in parsed.walk()
    ]


def require(condition: object, detail: str) -> None:
    """Fail an isolated acceptance check even when Python optimization is enabled."""
    if not condition:
        raise AssertionError(detail)


async def run_examples(app: Application) -> dict[str, object]:
    """Execute all required styles against the real facade, engine, and local disk."""
    require(
        isinstance(Mail.fromAddress("check@example.com"), PendingMail),
        "The fluent facade is not pinned.",
    )
    manager = await app.make(IMailManager)
    require(await Mail.resolve() is manager, "Facade and DI managers differ.")
    storage = await app.make(IStorageManager)
    await storage.disk("local").file("documents/guide.pdf").write(_PDF)
    await storage.disk("local").file("invoices/42.pdf").write(_PDF)
    welcome = await send_welcome()
    require(
        welcome.status == "stored" and welcome.file_path is not None,
        "Welcome mail was not stored.",
    )
    direct = await (Mail.mailer("file")
                    .fromAddress("no-reply@example.com", "Example App")
                    .to(Address("ana@example.com", "Ana")).subject("Welcome")
                    .attach(WelcomeMail("Ana").attachments()[0])
                    .send(WelcomeMail("Ana").content()))
    require(direct.recipients == welcome.recipients, "Envelope parity failed.")
    require(
        semantic_content(direct.file_path) == semantic_content(welcome.file_path),
        "Content parity failed.",
    )
    await Mail.send(CompleteWelcomeMail("Ana"))
    await Mail.to("ana@example.com").send(WelcomeMail("Ana"))
    controller = await app.build(WelcomeController)
    http_response = await controller.sendWelcome()
    require(isinstance(http_response, Response), "The controller returned no response.")
    require(json.loads(http_response.getBody())["status"] == "stored",
            "The HTTP response did not confirm file storage.")
    await InvoiceDeliveryService().sendInvoice(
        "ana@example.com", "42", "invoices/42.pdf",
    )
    await send_notifications()
    await NotificationService().sendNotification()
    await send_independent_messages()
    service = await app.build(AlertService)
    await service.sendAlert("ana@example.com")
    await Mail.raw("direct raw", configure_welcome)
    await Mail.html("<p>direct html</p>", configure_welcome)
    await Mail.send(
        Content(text="plain", html="<p>html</p>"), callback=configure_welcome,
    )
    await Mail.fromAddress("a@example.com").bcc("hidden@example.com").raw("Bcc only")
    shared = WelcomeMail("Shared")
    await asyncio.gather(
        Mail.to("first@example.com").send(shared),
        Mail.to("second@example.com").send(shared),
    )
    require(
        shared.name == "Shared" and shared.envelope().to == (),
        "Sending mutated a reusable Mailable.",
    )
    app.config("mail.default", "capture")
    result = await (
        Mail.fromAddress("a@example.com").to("b@example.com").raw("extension")
    )
    sink = await app.make(RecordingSink)
    require(
        result.driver == "recording" and len(sink.messages) == 1,
        "Provider extension did not receive the public send.",
    )
    files = list(app.basePath.glob("outgoing/**/*.eml"))
    require(len(files) == 18, f"Expected 18 files, received {len(files)}.")
    ids = set()
    for path in files:
        parsed = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        require(parsed["Bcc"] is None and parsed["Sender"] is None,
            "The MIME headers leak hidden recipients or invent Sender.")
        require(parsed["Date"] is not None and parsed["From"] is not None,
            "Required MIME headers are missing.")
        ids.add(str(parsed["Message-ID"]))
        body = parsed.get_body(("plain",))
        if body and body.get_content().strip() == "Hello, Luis.":
            require(
                str(parsed["To"]) == "luis@example.com",
                "Independent chains mixed recipients.",
            )
    require(len(ids) == len(files), "Message identifiers are not unique.")
    require(
        not list(app.basePath.glob("outgoing/**/*.tmp")), "Temporary files remain.",
    )
    return {"files": len(files), "extension": result.driver,
            "facade_pinned": isinstance(Mail.fromAddress("a@b"), PendingMail)}


async def main(runtime: str) -> None:
    """Boot a real isolated application through its public HTTP or CLI entry point."""
    smtplib.SMTP = forbid_smtp
    smtplib.SMTP_SSL = forbid_smtp
    routes = Path.cwd() / "routes"
    routes.mkdir()
    (routes / "__init__.py").write_text("", encoding="utf-8")
    (routes / "console.py").write_text(
        "from orionis.support.facades.reactor import Reactor\n", encoding="utf-8",
    )
    app = Application(base_path=Path.cwd(), compiled=False)
    app.withRouting(console="routes/console.py")
    app.withProviders(RecordingProvider)
    app.withConfigMail(default="archive", mailers={
        "archive": {"driver": "file", "path": "outgoing/archive"},
        "file": {"path": "outgoing/file"},
        "smtp": {"host": "", "username": "", "password": ""},
        "capture": {"driver": "recording", "label": "provider-extension"},
    })
    app.create()
    app.config("view", {"paths": [str(Path(__file__).parent)], "cache_path": None,
                        "autoescape": True})
    app.config("filesystems", {"default": "local", "disks": {
        "local": {"driver": "local", "path": "storage/attachments"},
    }})
    require(Mail._pinned_instance is None, "Import unexpectedly pinned the facade.")
    if runtime == "cli":
        code = await app.handleCommand(["reactor", "list"])
        require(code == 0, "CLI startup failed.")
        result = await run_examples(app)
    else:
        events = iter(({"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}))
        acknowledgements = []
        result = {}

        async def receive() -> dict[str, str]:
            return next(events)

        async def send(event: dict[str, str]) -> None:
            acknowledgements.append(event["type"])
            if event["type"] == "lifespan.startup.complete":
                result.update(await run_examples(app))
            if event["type"].endswith("failed"):
                error_msg = event.get("message", "Startup failed.")
                raise RuntimeError(error_msg)

        await app({"type": "lifespan"}, receive, send)
        require(acknowledgements == [
            "lifespan.startup.complete", "lifespan.shutdown.complete",
        ], "HTTP lifespan failed.")
    sys.stdout.write(json.dumps({"runtime": runtime, **result}) + "\n")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
