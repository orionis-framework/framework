# orionis.mail

> `orionis.mail` composes immutable mail declarations, renders views, resolves storage attachments, and delivers through SMTP, file, or custom transports.

## Overview

The mail pipeline separates declaration from side effects. `Envelope`, `Content`, and `Attachment` validate immutable intent; `Mailable` packages reusable intent; `PendingMail` creates independent fluent branches; `MailComposer` renders and serializes one complete MIME message; and `MailManager` resolves the selected transport only when `send`, `raw`, or `html` is awaited.

Built-in drivers are `smtp` and `file`. SMTP reports server acceptance, not final mailbox delivery. The file driver atomically publishes private `.eml` files and is useful for development, testing, or archival workflows.

## Requirements

- Python 3.14 or newer.
- A booted Orionis application for the `Mail` facade, dependency injection, views, and configured storage disks.
- A reachable SMTP server for the SMTP driver, or a local filesystem supporting hard links for the file driver.
- Valid sender and recipient mailbox addresses; at least one body and one transport recipient per send.

## Quick start

```python
from orionis.mail import Address, Content, Envelope

sender = Address("notifications@example.com", "Example App")
envelope = Envelope(
    subject="Welcome",
    from_address=sender,
    to=("ana@example.com", "ops@example.com"),
    reply_to="support@example.com",
)
content = Content(text="Welcome to Orionis.", html="<p>Welcome to Orionis.</p>")
assert envelope.recipients() == ("ana@example.com", "ops@example.com")
assert content.text == "Welcome to Orionis."
print(sender.asHeader())
```

Validation: **Executed successfully** on CPython 3.14.6; declaration performs no I/O.

## Core concepts

### Immutable declarations

Addresses, envelopes, content, attachments, prepared messages, and results are immutable snapshots. `Content.data` recursively freezes owned containers. `Mailable` methods are synchronous and declarative, so one instance can be reused by concurrent sends without mutation.

### Fluent operations

Every `PendingMail` method returns a new chain. `mailer`, `fromAddress`, `to`, `cc`, `bcc`, `replyTo`, `subject`, and `attach` do not render, read a file, or resolve a transport. Terminal methods are asynchronous. A callback receives an operation-local mutable `Message`, runs once, and may be synchronous or asynchronous.

### Composition boundary

`MailComposer` renders HTML/text views, reads every attachment through `IStorageManager`, validates sender/recipients, builds standards-based MIME bytes, and removes Bcc from visible headers while keeping it in the transport envelope. Preparation completes before a transport is created, so rendering or attachment errors never open SMTP or publish a partial file.

### Transport results

`MailStatus.ACCEPTED` means SMTP accepted every intended recipient, `PARTIAL` means it accepted some, and `STORED` means a complete `.eml` was published. None proves mailbox delivery or that a user read the message.

## Module structure

| Path | Responsibility |
|---|---|
| `entities/` | Addresses, envelopes, content, attachments, options, prepared MIME, settings, and results. |
| `mailable.py` | Reusable declarative mail abstraction. |
| `message.py` | Operation-local callback configurator. |
| `pending.py` | Immutable fluent chains and async terminal overloads. |
| `composer.py` | View rendering, storage reads, MIME composition, Bcc separation. |
| `manager.py` | Configuration, driver registry, global sender, and delivery orchestration. |
| `transports/smtp.py` | Blocking SMTP boundary executed away from the event loop. |
| `transports/file.py` | Atomic unique `.eml` publication. |
| `contracts/` | Manager and transport interfaces. |
| `provider.py`, `exceptions.py`, `enums/`, `types.py` | Container wiring and supporting public types. |

## Public API

The package root exports `Address`, `Attachment`, `Content`, `Envelope`, `MailResult`, `MailStatus`, `Mailable`, `Message`, and `PendingMail`.

### Value objects

- `Address(address, name=None)` accepts one addr-spec and normalizes its IDNA domain.
- `Envelope(...)` validates headers, normalizes/deduplicates recipients, and prevents a mailbox being both visible and Bcc.
- `Content(view=None, html=None, text=None, text_view=None, data=None)` requires at least one body and forbids view/literal conflicts for the same alternative.
- `Attachment.fromStorage(path, disk=None, name=None, mime_type=None)` declares deferred storage I/O with safe logical paths and metadata.
- `MailResult` returns message ID, mailer/driver, intended/accepted/rejected recipients, status, and optional file path.

### `Mailable`

Implement `envelope()` and `content()`; optionally implement `attachments()`. Pass an instance to `Mail.send()`, or pass the class so the container constructs it with dependency injection for each send.

### Fluent manager/facade

The `IMailManager` service and `Mail` facade provide `mailer`, `fromAddress`, `to`, `cc`, `bcc`, `replyTo`, `subject`, `attach`, `send`, `raw`, `html`, and `extend`. A selected mailer is a configuration entry name; its `driver` chooses an implementation.

### Terminal overloads

- `await Mail.send(mailable_or_class)`
- `await Mail.send("emails.welcome", data, callback)`
- `await Mail.send(Content(...), callback=callback)`
- `await Mail.raw(text, callback=None)`
- `await Mail.html(html, callback=None)`

## Common workflows

### Create reusable mail

Put recipients, subject, body, and attachment declarations in a `Mailable`. Keep declaration methods deterministic and free of I/O. Add per-send recipients or select a mailer by deriving a facade chain before `send`.

### Send a view or literal body

Pass a view name plus data to `send`, or use `raw`/`html` for literal content. Configure headers with a callback or preceding fluent chain. A callback must return `None` or the same `Message`; exceptions become composition failures.

### Attach storage files

Declare a logical storage path. The composer resolves the configured disk only during send, reads it asynchronously, applies an explicit/storage/inferred media type in that order, and uses the override name or path basename.

### Add a transport driver

Implement `IMailTransport`, create a sync or async factory accepting `(app, normalized_config)`, call `manager.extend()` during provider startup, and configure a named mailer with that driver. Duplicate driver names are rejected.

## Examples

### Declare a reusable mailable

```python
from orionis.mail import Content, Envelope, Mailable


class WelcomeMail(Mailable):
    def __init__(self, name: str) -> None:
        self.name = name

    def envelope(self) -> Envelope:
        return Envelope(subject="Welcome", to="ana@example.com")

    def content(self) -> Content:
        return Content(
            view="emails.welcome",
            text=f"Welcome, {self.name}.",
            data={"name": self.name},
        )


mail = WelcomeMail("Ana")
assert mail.envelope().subject == "Welcome"
assert mail.attachments() == ()
print(mail.content().text)
```

Validation: **Executed successfully** on CPython 3.14.6.

### Configure one message

```python
from orionis.mail import Attachment, Message

message = (
    Message()
    .fromAddress("billing@example.com", "Billing")
    .to("ana@example.com", "Ana")
    .cc(["audit@example.com", "audit@example.com"])
    .subject("Invoice 42")
    .attach(Attachment.fromStorage("invoices/42.pdf"))
)
snapshot = message._snapshot()
assert snapshot.envelope().recipients() == ("ana@example.com", "audit@example.com")
assert snapshot.attachments[0].path == "invoices/42.pdf"
print(snapshot.subject)
```

Validation: **Executed successfully** on CPython 3.14.6; `_snapshot()` is used here only to inspect the example declaration.

### Declare a named storage attachment

```python
from orionis.mail import Attachment

attachment = Attachment.fromStorage(
    "reports/annual.pdf",
    disk="private",
    name="Annual Report.pdf",
    mime_type="application/pdf",
)
assert attachment.path == "reports/annual.pdf"
assert attachment.disk == "private"
assert attachment.name == "Annual Report.pdf"
print(attachment.mime_type)
```

Validation: **Executed successfully** on CPython 3.14.6; no storage access occurred.

### Build independent fluent branches

```python
from orionis.mail import PendingMail


async def deliver(*args, **kwargs):
    raise AssertionError("declarations must not deliver")


base = PendingMail(deliver)
first = base.to("first@example.com")
second = base.to("second@example.com")
assert first is not base and second is not base and first is not second
assert base._options.to == ()
assert first._options.to[0].address == "first@example.com"
assert second._options.to[0].address == "second@example.com"
print("branches are isolated")
```

Validation: **Executed successfully** on CPython 3.14.6; protected state is inspected only to demonstrate isolation.

### Publish a prepared message with the file transport

```python
import asyncio
from tempfile import TemporaryDirectory
from pathlib import Path
from orionis.mail.entities.prepared import PreparedMail
from orionis.mail.transports.file import FileTransport


async def main() -> None:
    prepared = PreparedMail(
        message_id="<example@example.com>",
        sender="a@example.com",
        recipients=("b@example.com",),
        mime=b"Subject: Example\r\n\r\nHello\r\n",
        smtp_utf8=False,
    )
    with TemporaryDirectory() as root:
        result = await FileTransport(Path(root)).send(prepared, mailer="file", driver="file")
        assert result.file_path is not None
        assert result.file_path.read_bytes() == prepared.mime
        print(result.status)


asyncio.run(main())
```

Validation: **Executed successfully** on CPython 3.14.6; the `.eml` was written only in a temporary directory.

### Validate SMTP settings without connecting

```python
from orionis.mail.entities.smtp_settings import SmtpSettings
from orionis.mail.enums.encryption import MailEncryption

settings = SmtpSettings.fromConfig({
    "url": "smtps://user:secret@mail.example.com",
    "host": "ignored.example.com",
    "port": 587,
    "encryption": "TLS",
    "username": "",
    "password": "",
    "timeout": 10,
})
assert settings.host == "mail.example.com"
assert settings.port == 465
assert settings.encryption is MailEncryption.SSL
assert "secret" not in repr(settings)
print(settings.host)
```

Validation: **Executed successfully** on CPython 3.14.6; no network connection was opened.

### Inspect a transport result

```python
from pathlib import Path
from orionis.mail import MailResult, MailStatus

result = MailResult(
    message_id="<stored@example.com>",
    mailer="archive",
    driver="file",
    status=MailStatus.STORED,
    recipients=("ana@example.com",),
    file_path=Path("archive/message.eml"),
)
assert result.status == "stored"
assert result.accepted_recipients == ()
assert result.file_path.name == "message.eml"
print(result.mailer)
```

Validation: **Executed successfully** on CPython 3.14.6.

### Configure a direct send callback

```python
from orionis.mail import Message


def configure_invoice(message: Message) -> None:
    message.fromAddress("billing@example.com", "Billing")
    message.to("ana@example.com", "Ana")
    message.subject("Your invoice")


probe = Message()
assert configure_invoice(probe) is None
assert probe._snapshot().envelope().subject == "Your invoice"
print(probe._snapshot().to[0].address)
```

Validation: **Executed successfully** on CPython 3.14.6.

### Implement an asynchronous custom transport factory

```python
from collections.abc import Mapping
from pathlib import Path
from orionis.foundation.contracts.application import IApplication
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.transports.file import FileTransport


async def archive_factory(
    app: IApplication,
    config: Mapping[str, object],
) -> IMailTransport:
    path = Path(str(config.get("path", "storage/mail/archive")))
    if not path.is_absolute():
        path = app.basePath / path
    return FileTransport(path)
```

Validation: **Executed by the mail documentation test** with the real `Application` container and a temporary archive path.

### Register the custom driver

```python
from orionis.mail.manager import MailManager


def register_archive(manager: MailManager) -> None:
    manager.extend("custom_archive", archive_factory)
```

Validation: **Import- and syntax-validated** on CPython 3.14.6; the manager is resolved during provider startup.

### Send through the application facade

```python
import asyncio
from orionis.mail import Message
from orionis.support.facades import Mail


def configure(message: Message) -> None:
    message.to("ana@example.com").subject("Status")


async def send_status():
    return await Mail.mailer("file").raw("All systems operational", configure)


# asyncio.run(send_status())  # Run only after the Orionis application boots.
```

Validation: **Import- and syntax-validated** on CPython 3.14.6; delivery requires a booted application.

### Send a mailable class through dependency injection

```python
from orionis.support.facades import Mail


async def send_welcome() -> None:
    result = await Mail.to("ana@example.com").send(WelcomeMail("Ana"))
    assert result.status in {"accepted", "partial", "stored"}
```

Validation: **Import- and syntax-validated** on CPython 3.14.6; delivery requires configured views, sender, and transport.

## Configuration

`config/mail.py` defines the central mail section:

| Setting | Environment | Default |
|---|---|---|
| Default mailer | `MAIL_MAILER` | `smtp` |
| Global sender address | `MAIL_FROM_ADDRESS` | empty (must be supplied elsewhere before send) |
| Global sender name | `MAIL_FROM_NAME` | `APP_NAME`, then `Orionis` |
| SMTP URL | `MAIL_URL` | empty |
| SMTP endpoint | `MAIL_HOST`, `MAIL_PORT` | empty host, port 587 |
| SMTP security | `MAIL_ENCRYPTION` | `TLS` (`TLS`, `SSL`, or `none`) |
| SMTP credentials | `MAIL_USERNAME`, `MAIL_PASSWORD` | empty pair |
| SMTP timeout | `MAIL_TIMEOUT` | `None` |
| File output | `MAIL_FILE_PATH` | `storage/mail` |

An `smtp://` or `smtps://` URL overrides endpoint/security and replaces credentials as a pair when present. Named mailers may be added to `mailers`; conventional entries named `smtp` and `file` infer their driver, while other names require an explicit `driver`.

## Integration with Orionis

`MailProvider` binds `MailComposer` and `IMailManager` as singletons, then pins the `Mail` facade without opening a connection. The composer injects `IViewEngine` and `IStorageManager`; Mailable classes are built by the application container. Authentication uses mail for verification and password-reset flows.

Use injected `IMailManager` in services that benefit from explicit dependencies; use `Mail` in concise application entry points. Both address the same singleton, while every fluent operation remains isolated.

## Errors and edge cases

- Header controls, ambiguous address syntax, invalid domains, empty view identifiers, body conflicts, unsafe attachment paths/names/types, and Bcc overlap raise `MailCompositionException` subclasses.
- Sending without a sender or transport recipients fails during composition. An empty subject or literal body is valid.
- Attachment failures are reported as `MailAttachmentException`; missing files are not detected at declaration time.
- Unknown mailers/drivers, duplicate extensions, malformed SMTP settings, and invalid factory results raise `MailConfigurationException`.
- SMTP failures become `MailTransportException` with bounded, single-line, credential-redacted diagnostics.
- Mandatory STARTTLS fails when the server does not advertise it. International local parts require SMTPUTF8 support.
- File publication never overwrites an existing file and fails explicitly when atomic hard links are unsupported.
- Bcc recipients are included in the transport union but never serialized into MIME headers.
- A partial SMTP result must be handled according to application retry/idempotency policy; blindly resending may duplicate delivery to already accepted recipients.

## Performance and concurrency

Rendering and attachment reads run concurrently where safe; synchronous storage/file and SMTP work is moved off the event loop through Orionis' loop executor. MIME is composed completely in memory before transport, so large attachments increase peak memory. Enforce application-level limits before declaring mail.

Fluent options and Mailable declarations are immutable and safe to branch/reuse. Transport factories run per send and should return stateless or correctly synchronized transports. Driver registration must finish during startup. The file transport uses unique names and atomic links; SMTP establishes a connection per operation. Apply queueing and bounded concurrency for bulk mail.

## Compatibility

Orionis declares Python 3.14+. MIME uses Python's `email` policies, IDNA domains, Unicode display-name encoding, and SMTPUTF8 only when an addr-spec requires it. SMTP supports mandatory STARTTLS, implicit SSL, and explicit plaintext. File publication requires a local filesystem with atomic hard-link support, such as NTFS or regular POSIX filesystems.

## Verification notes

Validation used CPython 3.14.6. Exports, entities, fluent overloads, composition, views, storage attachments, SMTP/file transports, custom factories, configuration, provider/facade, and integration flows were inspected. All **193** mail test methods passed through the Orionis runner, including the documentation contract. Nine direct examples executed successfully, the custom factory executed against a real application, and three container-dependent examples were compile/import validated.
