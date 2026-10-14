# Configuring SMTP, file, and custom transports

Mail separates message declarations, MIME composition, and transport. Prepare sender, content, and delivery policy before the first send.

## Select a mailer

A mailer name identifies an entry in `mail.mailers`; `driver` identifies its implementation. `Mail.mailer("archive")` selects an entry and does not register a transport. Conventional `smtp` and `file` entries can infer their driver; other names require explicit `driver`. The manager resolves selection on each send and passes a normalized configuration copy to the factory.

`config/mail.py` includes SMTP and file entities. The top-level `Mail` entity also accepts an arbitrary mailer mapping; `Mailers` is the conventional field set. For another transport, declare a mapping like this and register its factory before sending. This block validates configuration only and does not change the active application configuration:

```python
from orionis.foundation.config.mail import Mail

config = Mail(
    default="archive",
    from_address={"address": "notifications@example.com", "name": "Reports"},
    mailers={
        "archive": {"driver": "custom_archive", "path": "storage/mail/archive"},
        "file": {"driver": "file", "path": "storage/mail"},
    },
)
assert config.default == "archive"
```

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

An `smtps://` URL forces SSL; an `smtp://` URL retains configured encryption. URL credentials replace credentials as a pair when present. Named mailers may be added to `mailers`; conventional entries named `smtp` and `file` infer their driver, while other names require an explicit `driver`.



## Operate SMTP

`TLS` means mandatory STARTTLS; `SSL` uses implicit TLS; `none` or an empty string disables TLS. There is no silent STARTTLS-to-plaintext fallback. TLS verifies hostnames and certificates using the system context and minimum TLS 1.2. The backend exposes no option to skip verification.

An `smtps://` URL selects SSL and port 465 unless an explicit port is supplied. An `smtp://` URL replaces the host and any explicit port but retains configured encryption and port when not overridden: it does not force plaintext. URL credentials replace username/password as a pair. Reserved characters must be URL-encoded. Paths, queries, and fragments are rejected; hosts must be valid and ports integers from 1 through 65535.

Username and password must both be present or both empty. `timeout` accepts a positive integer or `None`; set a bounded timeout for real operations because `None` leaves socket timeout behavior unbounded. International mailbox local parts require SMTPUTF8 and 8BITMIME; IDNA domain normalization alone does not require them. Errors avoid exposing credentials, but still do not log complete configuration objects or URLs.

## Use file for development or archives

The transport writes MIME to a private temporary file, flushes/fsyncs, then publishes through a random-named hard link without overwriting an existing file. Only then does it return `STORED` and `file_path`. The filesystem must support hard links; an unsupported mount fails explicitly. Relative paths resolve against the base path, absolute paths remain absolute, and anchored-but-relative Windows paths are rejected.

`.eml` files contain bodies, attachments, and visible addresses; protect them as application data. Publication does not send mail or schedule a worker. Define rotation, retention, and deletion outside this module: mail files are not cleaned automatically. Consumer cancellation does not guarantee that publication already running in the executor stops.


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

## Implement and register a transport

Implement async `IMailTransport.send(prepared, *, mailer, driver) -> MailResult`. It receives `PreparedMail` with complete MIME and separate sender/recipient data: use that transport envelope to preserve Bcc, and do not infer delivery recipients from visible headers. Composition is validated before transport creation.

A factory receives `(app, normalized_config)` and may be sync or async. It must return an `IMailTransport` instance; an unrelated object with a similarly named method is insufficient. `extend(name, factory)` rejects empty names, duplicates, and built-in `smtp`/`file` drivers. Registration is shared; finish during boot. Results must describe real evidence and must not claim SMTP acceptance before confirmation.

The following factory reuses file transport at another destination. The second block assumes `archive_factory` has been defined by the first:


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

### Register the custom driver

```python
from orionis.mail.manager import MailManager


def register_archive(manager: MailManager) -> None:
    manager.extend("custom_archive", archive_factory)
```

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

## Implementation reference for extensions

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

---

[Index](README.md) · [foundation](../../../foundation/docs/en/README.md) · [container](../../../container/docs/en/README.md) · [storage](../../../storage/docs/en/README.md)
