# Declaring content, recipients, and attachments

Mail separates message declarations, MIME composition, and transport. Prepare sender, content, and delivery policy before the first send.

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




## Choose a reusable message or a direct send

A `Mailable` represents a reusable business notification, such as invoice confirmation. Implement synchronous `envelope()` and `content()` methods; optional `attachments()` returns a sequence of `Attachment` declarations. Prepare required data before constructing it: avoid queries or sending inside these methods. The manager invokes them when the async terminal runs.

For a one-off note use `raw(text)` or `html(html)`; for a template use `send("emails.welcome", data, callback)`. `html()` treats its input literally and does not process Jinja syntax. HTML and plain-text alternatives can coexist through `Content(view=..., text=...)` or `Content(view=..., text_view=...)`; the same `data` feeds both views. Do not combine `view` with `html` or `text_view` with `text` in one `Content`.

`Content` requires at least one body; an empty literal string is valid, an empty template identifier is not. Context must be a mapping with string keys. Owned containers are copied and frozen, but opaque objects retain identity: do not assume a model's internal state is frozen. A `Mailable` is an application class and may have mutable attributes; the guarantee is that the pipeline does not mutate its declaration while sending.

### Addresses, privacy, and precedence

Use `Address("ana@example.com", "Ana")` to separate a mailbox and its display name. Validation normalizes IDNA domains and rejects header control characters. An `Envelope` normalizes and deduplicates recipients. `reply_to` only sets reply destinations; it adds no transport recipient. A mailbox visible in To/Cc cannot also appear in Bcc.

Explicit chain options replace a mailable's sender and subject and append recipients and attachments. When no sender is declared, `mail.from_address` is used; if that is also absent, composition fails. Neither address validation nor SMTP acceptance verifies account existence.

The composer removes Bcc from MIME headers while retaining its recipients in the transport envelope. Do not expose a `MailResult`'s complete recipient list to users who must not see it.


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

## Attach storage content

`Attachment.fromStorage(path, disk=None, name=None, mime_type=None)` only declares intent. Paths are logical and disk-relative; display names are basenames without separators. The file opens during sending and may disappear or change between declaration and reading. Authorize document access before attaching it and use a configured disk, such as `local` for private data.

An explicit MIME type takes precedence over storage metadata; otherwise the filename is used for inference, falling back to `application/octet-stream`. This inference does not inspect content or provide antivirus scanning. This module has no remote-URL attachments, inline/CID attachments, or bytes-based attachment API. Store validated content first when that workflow is needed.

Every attachment is read completely and the resulting MIME message is built in memory. Even with a streaming driver, mail is not constant-memory: bound attachment count and combined size before sending. For large files, send an authorized or temporary link according to your policy.


### Declare a named storage attachment

```python
from orionis.mail import Attachment

attachment = Attachment.fromStorage(
    "reports/annual.pdf",
    disk="local",
    name="Annual Report.pdf",
    mime_type="application/pdf",
)
assert attachment.path == "reports/annual.pdf"
assert attachment.disk == "local"
assert attachment.name == "Annual Report.pdf"
print(attachment.mime_type)
```

### Value objects

- `Address(address, name=None)` accepts one addr-spec and normalizes its IDNA domain.
- `Envelope(...)` validates headers, normalizes/deduplicates recipients, and prevents a mailbox being both visible and Bcc.
- `Content(view=None, html=None, text=None, text_view=None, data=None)` requires at least one body and forbids view/literal conflicts for the same alternative.
- `Attachment.fromStorage(path, disk=None, name=None, mime_type=None)` declares deferred storage I/O with safe logical paths and metadata.
- `MailResult` returns message ID, mailer/driver, intended/accepted/rejected recipients, status, and optional file path.

### `Mailable`

Implement `envelope()` and `content()`; optionally implement `attachments()`. Pass an instance to `Mail.send()`, or pass the class so the container constructs it with dependency injection for each send.

---

[Index](README.md) · [view](../../../view/docs/en/README.md) · [storage](../../../storage/docs/en/README.md)
