# Orionis Mail

Reusable Mailables and direct sends share one asynchronous preparation and
delivery pipeline. Production transports are **SMTP** and **file** only.

[Spanish manual](README.es.md)

## Contents

- [Architecture](#architecture)
- [Configuration](#configuration)
- [Public API](#public-api)
- [Examples](#examples)
- [Views and attachments](#views-and-attachments)
- [MIME and privacy](#mime-and-privacy)
- [Results and errors](#results-and-errors)
- [Extending drivers](#extending-drivers)
- [Startup and scripts](#startup-and-scripts)
- [Concurrency and limits](#concurrency-and-limits)
- [Verification](#verification)

## Architecture

```text
Mail facade / IMailManager
    -> independent PendingMail
    -> Mailable declarations OR direct Content + operation-local Message
    -> merged, validated Envelope
    -> IViewEngine.render + IStorageManager.disk(...).file(...).open(...)
    -> EmailMessage -> immutable PreparedMail (MIME bytes + transport envelope)
    -> IMailTransport -> MailResult
```

| Component | Responsibility |
| --- | --- |
| [MailManager](../manager.py) / [IMailManager](../contracts/manager.py) | Read central configuration and register/resolve factories. |
| [PendingMail](../pending.py) | Derive independent synchronous chains; implement all async terminals. |
| [Message](../message.py) | Mutate the configuration of one direct-send callback. |
| [Mailable](../mailable.py) | Declare reusable envelope, content, and attachments synchronously. |
| [MailComposer](../composer.py) | Validate, render views, close storage streams, and serialize MIME. |
| [IMailTransport](../contracts/transport.py) | Consume prepared bytes and the separate transport envelope. |
| [MailProvider](../provider.py) | Bind shared services and eagerly pin the facade. |

`MailManager` reuses the same terminal implementation as `PendingMail`; `raw()`
and `html()` do not contain separate SMTP paths. Factories execute per send and
may obtain shared stateless transports from the container. No manager or built-in
transport retains a message's recipients, body, or attachments.

No additional dependency is required. The module uses the standard `email`,
`smtplib`, `ssl`, and filesystem libraries, Orionis `Loop.execute()` workers,
the configured view engine, storage, and `DateTime.now()`.

## Configuration

A **mailer** is a configuration name. A **driver** is its transport implementation.
For example, mailer `archive` can use driver `file`.

The existing frozen bootstrap remains supported without additional fields:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.mail.entities.file import File
from orionis.foundation.config.mail.entities.mail import Mail
from orionis.foundation.config.mail.entities.mailers import Mailers
from orionis.foundation.config.mail.entities.smtp import Smtp
from orionis.environment import Env


@dataclass(frozen=True, kw_only=True)
class BootstrapMail(Mail):
    default: str = field(
        default_factory=lambda: Env.get("MAIL_MAILER", "smtp"),
    )
    mailers: Mailers | dict = field(
        default_factory=lambda: Mailers(
            smtp=Smtp(
                url=Env.get("MAIL_URL", ""),
                host=Env.get("MAIL_HOST", ""),
                port=Env.get("MAIL_PORT", 587),
                encryption=Env.get("MAIL_ENCRYPTION", "TLS"),
                username=Env.get("MAIL_USERNAME", ""),
                password=Env.get("MAIL_PASSWORD", ""),
                timeout=None,
            ),
            file=File(path="storage/mail"),
        ),
    )
```

The equivalent nested dictionaries are accepted. Additional named mailers use
dictionary entries; `Mailers(smtp=..., file=...)` remains unchanged:

```python
mail_configuration = {
    "default": "archive",
    "mailers": {
        "archive": {"driver": "file", "path": "storage/mail/archive"},
        "file": {"path": "storage/mail"},
        "smtp": {
            "host": "smtp.example.com",
            "port": 587,
            "encryption": "TLS",
            "username": "",
            "password": "",
            "url": "",
            "timeout": 30,
        },
    },
}
```

Conventional `smtp` and `file` entries may omit `driver`; other names must declare
it. An entity's existing `driver` is honored. The `Mail` configuration entity
preserves dictionary mailer names through `asdict()`/`toDict()` rather than
coercing them into fixed `Mailers` fields. `default` is no longer limited to those
two fixed names. Unknown mailers and drivers fail explicitly when sending, with
no fallback. Providers can register a custom driver before its first use.

Services read only `app.config("mail")`; they never re-read environment variables
or import the application's configuration module. Selected settings are copied
into read-only container structures without modifying their source. Existing
entities still validate structural types; SMTP **effective** ports, timeouts,
encryption and authentication are validated on selection, after URL precedence.
An unused invalid SMTP endpoint does not prevent a file send or facade pinning.

There is no global sender field in this configuration. Declare one using
`Envelope(from_address=...)` or `fromAddress()`. A missing final sender fails
before transport; the SMTP username is never used as the sender.

### SMTP options and MAIL_URL

| Setting | Meaning |
| --- | --- |
| `host` | Required effective SMTP hostname. |
| `port` | Effective integer between 1 and 65535; booleans are rejected. |
| `encryption` | Case-insensitive `TLS` = mandatory STARTTLS; `SSL` = implicit TLS; `""` or `none` = explicitly requested plaintext. Other values fail. |
| `username`, `password` | Both empty means no authentication. Exactly one populated value fails. |
| `timeout` | Positive integer seconds or `None`. Zero is unsupported by blocking smtplib; floats, booleans and negatives fail. |
| `url` | Empty string uses the individual fields; otherwise apply the rules below. |

`encryption` remains a string, not a nullable field. TLS uses the system trust
store, certificate and hostname validation, and a minimum TLS version of 1.2.
Missing or failed STARTTLS never falls back to plaintext.

For a non-empty `MAIL_URL`:

1. Only `smtp://` and `smtps://` are accepted, with a required host.
2. The URL host replaces `host`.
3. `smtp://` uses its explicit port or the configured `port`, preserving the
   configured encryption mode. It does not implicitly request plaintext.
4. `smtps://` forces implicit TLS and uses its explicit port or 465.
5. URL credentials replace username/password **as a pair**, after percent
   decoding. Without URL credentials, both individual fields are used.
6. `timeout` is independent of the URL.
7. Paths (including a trailing slash), queries, fragments, unsupported schemes,
   malformed hosts and invalid ports are rejected, not silently interpreted.

`timeout=None` means an unbounded socket wait, not a hidden default. Prefer an
explicit positive timeout when indefinite waits are unsuitable. Socket timeout
is not an overall delivery deadline.

### File transport

`File.path` is a directory. Relative paths are anchored to `app.basePath`, not
process cwd and not the default storage disk. Absolute paths are respected;
Windows drive-relative/root-relative paths are rejected as ambiguous.

The worker creates the directory, writes a uniquely named private temporary,
flushes and fsyncs it, then publishes a random `.eml` name using `os.link`.
Publication is atomic and exclusive: collisions never overwrite an existing
message, and a final name never exposes a partially written message. Cleanup of
the operation-owned temporary is attempted in `finally`.

This requires hard-link support, such as NTFS on Windows or normal local POSIX
filesystems. Unsupported filesystems fail explicitly; there is no unsafe
overwrite fallback. The file and final directory use restrictive permissions
where supported (temporary file 0600, new output directory 0700). On Windows,
effective access depends on inherited ACLs. This is not a guarantee against
power-loss loss of directory entries or externally changed permissions.

Keep output outside publicly served directories and version control. The default
`storage/mail/` is ignored by this repository; exclude custom output paths too.
Storing an `.eml` does not deliver it to a mailbox.

## Public API

```python
from orionis.support.facades.mail import Mail
from orionis.mail import (
    Address, Attachment, Content, Envelope, MailResult, Mailable, Message,
    PendingMail,
)
from orionis.mail.contracts.manager import IMailManager
```

There is deliberately no `Mail` facade exported from `orionis.mail`.

### Values

| Value | Constructor or factory |
| --- | --- |
| `Address` | `Address(address: str, name: str | None = None)` |
| `Envelope` | `Envelope(*, subject="", from_address=None, to=(), cc=(), bcc=(), reply_to=())` |
| `Content` | `Content(*, view=None, html=None, text=None, text_view=None, data=None)` |
| `Attachment` | `Attachment.fromStorage(path, *, disk=None, name=None, mime_type=None)` |

Values are frozen and slotted. Address collections become tuples. Context
mapping/list/tuple/set containers are recursively copied into read-only mappings,
tuples and frozensets; cyclic container trees fail explicitly. Arbitrary context
objects, including services, retain identity: they are **not deep-copied**, and
the mail module does not mutate them. Result rejection maps are copied and made
read-only as well.

`Content.view` is an HTML view identifier; `html` is literal HTML. They are
mutually exclusive. Similarly, `text_view` and literal `text` are exclusive.
Declare at least one body. `""` is an intentionally declared body, not absence.
Both views use the same explicit `data`. Literals are never templates, and there
is no automatic HTML-to-text conversion.

### Synchronous composition

`Mail`, `IMailManager`, and `PendingMail` expose `mailer(name)`,
`fromAddress(address, name=None)`, `to(addresses, name=None)`, `cc(...)`, `bcc(...)`,
`replyTo(...)`, `subject(value)`, and `attach(attachment)`.

Every call returns an independent `PendingMail` immediately, without rendering,
attachment reads, or transport resolution. Do **not** await intermediate calls.
`Message` exposes the same envelope mutators except `mailer`, and returns the
**same mutable Message** each time; it is exclusive to one callback operation.

Use a single string, an `Address`, or a list/tuple of those for recipients. A
display `name` is valid only beside one string, never beside an `Address` or a
collection. Strings containing multiple comma-separated mailboxes are rejected;
use a collection. `fromAddress()` accepts exactly one sender and sets both `From`
and the transport sender. It never creates a separate `Sender` header.

Repeated `subject()` and `fromAddress()` calls replace values. Recipients and
attachments accumulate. Deduplication preserves order and local-part case;
domains are IDNA-normalized and case-normalized. Visible/Bcc conflicts fail.

### Asynchronous terminals

All terminals return `MailResult` and exist on the manager, facade and chains:

| Operation | Interpretation |
| --- | --- |
| `await Mail.send(mailable)` | Synchronous Mailable declarations; no `data` or callback accepted. |
| `await Mail.send(view, data=None, callback=None)` | A string always identifies an HTML view. |
| `await Mail.send(content, *, callback=None)` | A Content owns its data; an additional data argument is invalid. |
| `await Mail.raw(text, callback=None)` | Literal plain text. |
| `await Mail.html(html, callback=None)` | Literal HTML. |

Explicitly supplying even `None` for a forbidden argument is rejected rather
than ignored. No `from_`, `sender`, `setFrom`, `text`, `sendText` or `sendHtml`
aliases are provided.

A callback receives one operation-local `Message` exactly once. Functions,
methods and callable objects are supported. Return `None`, the received Message,
or an awaitable resolving to either. The awaitable is awaited before continuing.
Other results, including `False` or another Message, fail explicitly. Callback
exceptions prevent transport. Keep synchronous callbacks fast; mutators do no I/O.

For Mailables, declaration comes first, then explicit chain scalars override and
chain recipients/attachments append. For direct sends, the Message starts from
the chain; callback scalars override and its recipients/attachments append.

## Examples

These examples run after normal application startup. The acceptance fixtures
provide `emails.welcome`, `emails.invoice`, `emails/welcome.txt`, and storage
files `documents/guide.pdf` and `invoices/42.pdf`.

### Reusable Mailable

```python
from orionis.mail import Address, Attachment, Content, Envelope, MailResult, Mailable
from orionis.support.facades.mail import Mail


class WelcomeMail(Mailable):
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def envelope(self) -> Envelope:
        return Envelope(
            from_address=Address("no-reply@example.com", "Example App"),
            subject="Welcome",
        )

    def content(self) -> Content:
        return Content(
            view="emails.welcome",
            data={"name": self.name},
            text=f"Hello, {self.name}. Welcome to our application.",
        )

    def attachments(self) -> list[Attachment]:
        return [Attachment.fromStorage(
            "documents/guide.pdf", disk="local", name="guide.pdf",
            mime_type="application/pdf",
        )]


async def send_welcome() -> MailResult:
    return await (
        Mail.mailer("file").to(Address("ana@example.com", "Ana"))
        .send(WelcomeMail("Ana"))
    )
```

If `envelope()` already declares recipients, `await Mail.send(mailable)` is
enough. `envelope()` and `content()` are mandatory synchronous declarations;
`attachments()` defaults to an empty sequence. Sending never mutates a Mailable.

### Controller without a Mailable

```python
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.mail import Attachment, Message
from orionis.support.facades.mail import Mail


def configure_welcome(message: Message) -> None:
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
        result = await Mail.send(
            "emails.welcome", {"name": "Ana"}, configure_welcome,
        )
        return response.json({
            "message_id": result.message_id,
            "status": result.status,
        })
```

The controller returns a real HTTP response, not a MailResult or an unawaited
operation. `HttpResponse` is the framework's annotation alias, not an
`isinstance()` target.

### Fluent service with an attachment

```python
from orionis.mail import Attachment, Content, MailResult
from orionis.support.facades.mail import Mail


class InvoiceDeliveryService:
    __slots__ = ()

    async def sendInvoice(
        self, recipient: str, invoice_number: str, attachment_path: str,
    ) -> MailResult:
        return await (
            Mail.mailer("file")
            .fromAddress("billing@example.com", "Example Billing")
            .to(recipient).subject(f"Invoice {invoice_number}")
            .attach(Attachment.fromStorage(
                attachment_path, disk="local", name=f"invoice-{invoice_number}.pdf",
                mime_type="application/pdf",
            ))
            .send(Content(
                view="emails.invoice", data={"invoice_number": invoice_number},
                text=f"Your invoice {invoice_number} is attached.",
            ))
        )
```

### Literal text and HTML

```python
from orionis.support.facades.mail import Mail


async def send_notifications() -> None:
    await (
        Mail.fromAddress("notifications@example.com", "Example App")
        .to("ana@example.com").subject("Report ready")
        .raw("Your report is ready.")
    )
    await (
        Mail.fromAddress("notifications@example.com", "Example App")
        .to("ana@example.com").subject("Report ready")
        .html("<h1>Your report is ready.</h1>")
    )
```

`Mail.raw(text, callback)` and `Mail.html(html, callback)` can also start an
operation directly, including attachments configured by the callback.

### Asynchronous callback

```python
from orionis.mail import MailResult, Message
from orionis.support.facades.mail import Mail


class NotificationService:
    __slots__ = ()

    async def configureMessage(self, message: Message) -> None:
        message.fromAddress("notifications@example.com", "Example App")
        message.to("ana@example.com")
        message.subject("Notification")

    async def sendNotification(self) -> MailResult:
        return await Mail.mailer("file").raw(
            "Your notification is ready.", self.configureMessage,
        )
```

### Independent concurrent chains

```python
import asyncio
from orionis.support.facades.mail import Mail


async def send_independent_messages() -> None:
    base = (
        Mail.mailer("file")
        .fromAddress("notifications@example.com", "Example App")
        .subject("Notification")
    )
    first = base.to("ana@example.com")
    second = base.to("luis@example.com")
    await asyncio.gather(first.raw("Hello, Ana."), second.raw("Hello, Luis."))
```

`base` remains recipient-free; `first` and `second` do not share recipients.

### Dependency injection

```python
from orionis.mail import MailResult
from orionis.mail.contracts.manager import IMailManager


class AlertService:
    __slots__ = ("__mail",)

    def __init__(self, mail: IMailManager) -> None:
        self.__mail = mail

    async def sendAlert(self, recipient: str) -> MailResult:
        return await (
            self.__mail.fromAddress("alerts@example.com", "Example App")
            .to(recipient).subject("Service alert")
            .raw("A service alert requires your attention.")
        )
```

The facade and DI use the same singleton. Import constructor contracts at runtime
and do not use postponed string annotations in DI-built services.

## Views and attachments

Views are rendered to `str` through the existing `IViewEngine.render(template,
context)` contract, not an HTTP response or PendingView. Loaders, caching,
extensions, filters, escaping, and naming conventions remain those of Orionis.
Independent templates work without an HTTP request. Context is explicit per send
and never installed into template globals.

```python
from orionis.mail import Content, MailResult
from orionis.support.facades.mail import Mail


async def send_two_views() -> MailResult:
    return await (
        Mail.mailer("file").fromAddress("no-reply@example.com")
        .to("ana@example.com")
        .send(Content(
            view="emails.welcome", text_view="emails/welcome.txt",
            data={"name": "Ana"},
        ))
    )
```

Text views retain the configured engine's escaping behavior. Use a slash path
for a template with an explicit non-HTML extension, such as `emails/welcome.txt`.
No second Jinja environment is created by the mail module.

`Attachment.fromStorage()` validates declarations but performs no I/O. During
preparation it resolves the explicit/default disk, obtains a file through the
storage API, opens its async binary stream, reads bytes and closes it. It never
uses a reconstructed local path or public URL. Empty bytes are valid; missing,
unreadable or non-binary failure values abort the whole send.

Explicit MIME wins, then valid storage MIME metadata, then filename inference,
then `application/octet-stream`. Explicit names win; otherwise only the logical
path's basename is visible. Controls, path separators, and unsafe MIME parameters
are rejected. Read/open errors retain their cause, and a close error cannot hide
an earlier read error. Any failure prevents transport.

## MIME and privacy

- `EmailMessage` produces plain text, HTML, `multipart/alternative`, and
  `multipart/mixed` with correctly nested alternatives and binary attachments.
- Unicode subjects, visible names, body text, and attachment filenames are
  supported. Each operation generates Date from `DateTime.now()` and one
  Message-ID, retained in the result.
- To/Cc headers and the transport recipient union are separate. Bcc participates
  in that union but never appears in serialized MIME or `.eml` headers.
- Bcc-only messages work. A mailbox cannot appear in both To/Cc and Bcc.
- Header values reject CR/LF and other controls. Mailboxes use the standard email
  parser rather than an improvised regular expression. Domain case is normalized;
  local-part case is preserved.
- Non-ASCII mailbox local parts, including Reply-To, require SMTPUTF8 and
  8BITMIME. The transport negotiates these explicitly or fails without removing
  characters. Unicode display names alone do not require SMTPUTF8.

Rendering and every attachment read finish before any SMTP connection or file
publication. Message does not expose a mutable `EmailMessage` escape hatch.

## Results and errors

`MailResult` is a frozen slotted value with these public attributes:

| Attribute | Type |
| --- | --- |
| `message_id` | `str` |
| `mailer` | `str` |
| `driver` | `str` |
| `status` | `MailStatus` |
| `recipients` | `tuple[str, ...]` |
| `accepted_recipients` | `tuple[str, ...]` |
| `rejected_recipients` | `Mapping[str, tuple[int, str]]` |
| `file_path` | `Path | None` |

`MailStatus`, from `orionis.mail.enums.status`, is a `StrEnum` with the members
`ACCEPTED`, `PARTIAL`, and `STORED`, so `result.status == "stored"` keeps working
and the value serializes as plain text.

`accepted` means SMTP accepted DATA for all intended recipients. `partial` means
it accepted for some and rejected others. Rejections retain their SMTP code with
bounded, control-free, credential-redacted reasons. A failed DATA transaction or
total refusal raises an exception, never a falsely successful result.

`stored` means file publication completed. Its accepted/rejected collections are
empty, while `recipients` retains the intended envelope and `file_path` references
the final file. SMTP results have no file path. None of these states confirms
mailbox delivery or reading.

Exceptions live in `orionis.mail.exceptions`:

| Exception | Meaning |
| --- | --- |
| `MailException` | Common mail failure base. |
| `MailConfigurationException` | Unknown/malformed mailer, driver, factory, or selected transport options. |
| `MailCompositionException` | Invalid API combinations, headers, Mailable declarations, callbacks, views, or MIME. |
| `MailAttachmentException` | Composition subclass for unsafe or unreadable attachments. |
| `MailTransportException` | SMTP transaction or file publication failure. |

SMTP failures report the stage, exception type and response code when available.
Raw protocol exceptions are suppressed from tracebacks because they can include
credentials or private server responses. No SMTP sessions, URLs with credentials,
passwords, or MIME content are logged by this module. Connection closure is
attempted in every path without masking the primary error.

## Extending drivers

`IMailManager.extend(driver, factory)` registers a unique driver name and returns
`None`. Replacing a built-in or duplicate custom driver is an explicit error.
Every factory has the same typed signature, exported as `TransportFactory` from
`orionis.mail.types`:

```python
from collections.abc import Awaitable, Callable, Mapping
from orionis.foundation.contracts.application import IApplication
from orionis.mail.contracts.transport import IMailTransport

type TransportFactory = Callable[
    [IApplication, Mapping[str, object]],
    IMailTransport | Awaitable[IMailTransport],
]
```

Factories receive the container and a detached, read-only selected configuration
including `driver`. They may await `app.make()`/`app.build()` for dependencies.
Synchronous factories must remain quick and nonblocking. Registration itself
does not instantiate transports; resolution occurs only during a terminal send,
after successful preparation.

This usable extension example reuses the existing file transport rather than
adding a third backend to the framework:

```python
from collections.abc import Mapping
from pathlib import Path
from orionis.container.providers import ServiceProvider
from orionis.foundation.contracts.application import IApplication
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.exceptions import MailConfigurationException
from orionis.mail.transports.file import FileTransport


async def archive_factory(
    app: IApplication, config: Mapping[str, object],
) -> IMailTransport:
    output = config.get("path")
    if not isinstance(output, str) or not output.strip():
        error_msg = "An archive output path is required."
        raise MailConfigurationException(error_msg)
    path = Path(output)
    if not path.is_absolute():
        path = app.basePath / path
    return await app.build(FileTransport, path=path)


class ArchiveProvider(ServiceProvider):
    __slots__ = ()

    async def boot(self) -> None:
        manager = await self.app.make(IMailManager)
        manager.extend("custom_archive", archive_factory)
```

Register that provider with normal `app.withProviders(...)` **before** `create()`.
Set a mailer's `driver` to `custom_archive` and give it a `path`. The tests also
exercise a recording transport, defined only in tests, registered through a real
provider and central configuration.

A new transport implements async
`send(message: PreparedMail, *, mailer: str, driver: str) -> MailResult`.
`PreparedMail`, from `orionis.mail.entities.prepared`, provides `message_id`, `sender`,
`recipients`, `mime: bytes`, and `smtp_utf8: bool`. It contains no views or logical
storage paths. Shared custom transports must likewise avoid mutable operation
state and preserve the result/privacy/error contracts.

## Startup and scripts

`MailProvider` is eager and belongs to `CORE_PROVIDERS`. `register()` binds the
composer and `IMailManager`; `boot()` awaits `Mail.pin()`. Normal HTTP ASGI/RSGI
startup and CLI startup therefore make fluent facade entries synchronous from
their first application call. No transport is opened or operationally validated
at boot. Startup constructors use injected contracts, not unpinned facades.

A bare `from bootstrap.app import app` loads configuration and registrations,
but does **not** run normal runtime startup hooks. Prefer an Orionis command for
scripts requiring the application's full startup, views, or custom providers.
For a standalone raw/HTML script requiring only the mail component, explicit
component boot is supported:

```python
from bootstrap.app import app
from orionis.aio import Loop
from orionis.mail.provider import MailProvider
from orionis.support.facades.mail import Mail


async def main() -> None:
    await MailProvider(app).boot()
    await (
        Mail.mailer("file").fromAddress("no-reply@example.com")
        .to("ana@example.com").raw("Sent from an explicitly booted script.")
    )


if __name__ == "__main__":
    Loop.run(main())
```

This minimal script does not run other providers' boot hooks. For views, their
provider must also be booted so configured globals/filters/extensions are ready;
application-specific hooks and custom drivers must be initialized too. Use normal
CLI startup when those dependencies are involved. Never rely on an unpinned
facade's `_FacadeDispatch` as a PendingMail.

After adding this provider to an existing compiled checkout, invalidate only
`storage/framework/bootstrap` (or the existing optimize-clear mechanism). The
bootstrap cache does not automatically watch framework source changes.

## Concurrency and limits

- Each facade entry and chain derivation is independent. A Message is mutable
  **per operation**; retaining it does not permit changing an already snapshotted
  message. Mailables are declarative and may be reused without module mutations.
- Every SMTP send has its own connection. Blocking SMTP, TLS, MIME serialization
  and file publication run through `Loop.execute()`, outside the event loop.
- MIME and attachments can be fully materialized in memory; this is **not**
  end-to-end streaming. Account for concurrent message sizes and encoding copies.
- Callback/render cancellation propagates before transport. Storage preparation
  retains ownership of an in-flight stream until it finishes and closes, then
  propagates cancellation; a stuck storage backend can delay that cleanup.
- Cancelling an SMTP/file worker's awaiting task does not necessarily stop the
  worker. SMTP may have accepted the message; a file may still be published.
  Workers retain responsibility for connection/temporary cleanup.
- Timeouts, cancellation and disconnects are not proof of non-delivery. There
  are no automatic retries. `timeout=None` can keep a worker, and process shutdown
  waiting for it, blocked indefinitely.
- This release has no queues, scheduling, retry/failover/load balancing,
  HTTP delivery providers, tracking/webhooks, inline images, mail Markdown,
  generators, or public fake API. No placeholder methods expose those features.

## Verification

[The mail tests](../../../tests/mail) use the framework runner and explicit
network doubles, with no external credentials or real outgoing SMTP. They cover
the original bootstrap, named dictionary configuration, both composition styles,
DI/facades, actual Jinja rendering, local and pathless storage, MIME/privacy,
SMTP modes and failures, atomic file publication and concurrent cancellation.

[The isolated application fixture](../../../tests/mail/fixtures/application.py)
executes the examples after both normal HTTP lifespan and CLI startup, including
a real controller response and a provider-registered custom test transport.
[The type fixture](../../../tests/mail/fixtures/typecheck.py) checks public
overloads from consumer code. The only localized SMTP type suppressions reflect
typeshed's float-only timeout annotation; tests verify that Python 3.14 accepts
`None` in both real SMTP constructors without opening a connection.

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe reactor test --start-dir=tests/mail --verbosity=1
.\.venv\Scripts\python.exe -m ruff check orionis/mail tests/mail
uvx pyright --pythonpath .venv/Scripts/python.exe --pythonversion 3.14 orionis/mail orionis/support/facades/mail.pyi tests/mail/fixtures/typecheck.py
```

Live SMTP-server interoperability and non-local filesystems require deployment
verification; the suite does not claim certification of external providers.
