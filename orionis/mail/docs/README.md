# orionis.mail

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.mail initializer exports 9 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.mail/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| Address | from orionis.mail import Address | [entities/address.py](../entities/address.py) | Address | Represent one mailbox with an optional Unicode display name. Parameters ---------- address : str Single addr-spec, never a comma-separated list or a display-name form. name : str / None Optional visible name. |
| Address.asHeader | from orionis.mail import Address | [entities/address.py](../entities/address.py) | def asHeader(self) -> HeaderAddress | Build a standard immutable address header value. Returns ------- HeaderAddress The mailbox with its optional display name. |
| Attachment | from orionis.mail import Attachment | [entities/attachment.py](../entities/attachment.py) | Attachment | Describe a storage attachment without opening it or resolving a disk. Parameters ---------- path : str Logical disk-relative path, normalized on declaration. disk : str / None Configured disk name, or None for the default disk. name : str / None Visible basename overriding the logical path's basename. mime_type : str / None Explicit MIME type overriding storage metadata and inference. |
| Attachment.fromStorage | from orionis.mail import Attachment | [entities/attachment.py](../entities/attachment.py) | def fromStorage(cls, path: str, *, disk: str / None, name: str / None, mime_type: str / None) -> Self | Declare a file to resolve through Orionis storage when sending. Parameters ---------- path : str Logical disk-relative path. disk : str / None Configured disk name, or None for the default disk. name : str / None Visible basename overriding the logical path's basename. mime_type : str / None Explicit MIME type overriding storage metadata and inference. Returns ------- Self An immutable attachment declaration, with no I/O performed. Raises ------ MailAttachmentException If the declaration contains unsafe paths or metadata. |
| Content | from orionis.mail import Content | [entities/content.py](../entities/content.py) | Content | Declare literal bodies or views with one explicit isolated context. Parameters ---------- view : str / None HTML template identifier, mutually exclusive with html. html : str / None Literal HTML, never interpreted as a template. text : str / None Literal plain text, mutually exclusive with text_view. text_view : str / None Plain-text template identifier. data : Mapping[str, object] / None Context shared by both views, with copied read-only containers. |
| Envelope | from orionis.mail import Envelope | [entities/envelope.py](../entities/envelope.py) | Envelope | Store normalized immutable headers and intended recipients. Parameters ---------- subject : str Literal subject, including an intentionally empty subject. from_address : Address / None From header and transport sender. to : tuple[Address, ...] Primary visible recipients. cc : tuple[Address, ...] Additional visible recipients. bcc : tuple[Address, ...] Hidden transport recipients. reply_to : tuple[Address, ...] Reply destinations, which are never transport recipients. |
| Envelope.recipients | from orionis.mail import Envelope | [entities/envelope.py](../entities/envelope.py) | def recipients(self) -> tuple[str, ...] | Return the stable deduplicated transport recipient union. Returns ------- tuple[str, ...] To, Cc, and Bcc addresses without Reply-To. |
| MailResult | from orionis.mail import MailResult | [entities/result.py](../entities/result.py) | MailResult | Report SMTP acceptance or file storage, never final mailbox delivery. All recipient collections are copied. Rejection reasons are bounded, single-line text; transports must redact credentials before constructing the result. Stored messages have no SMTP acceptance or rejection entries. Parameters ---------- message_id : str Message-ID of the transmitted or stored message. mailer : str Selected configuration name. driver : str Registered transport implementation name. status : MailStatus Confirmed outcome of the operation. recipients : tuple[str, ...] Intended transport recipients. accepted_recipients : tuple[str, ...] Recipients confirmed by an SMTP transaction. rejected_recipients : Mapping[str, tuple[int, str]] Rejected recipients mapped to their SMTP code and sanitized reason. file_path : Path / None Published file for stored messages, or None for SMTP. |
| MailStatus | from orionis.mail import MailStatus | [enums/status.py](../enums/status.py) | MailStatus | Enumerate the outcomes a transport can confirm for one operation. Members inherit from :class:`str`, so they compare equal to the plain status strings exposed in results and serialized payloads. No member confirms mailbox delivery or that a recipient read the message. Attributes ---------- ACCEPTED : str SMTP accepted the message for every intended recipient. PARTIAL : str SMTP accepted the message for some recipients and rejected others. STORED : str The file transport published the complete message on disk. |
| Mailable | from orionis.mail import Mailable | [mailable.py](../mailable.py) | Mailable | Declare reusable mail without I/O or per-send mutation. Subclasses describe headers, bodies, and attachments synchronously. Pass an instance to ``Mail.send()`` when it is already constructed, or pass its class to let the application container inject constructor dependencies. Rendering, attachment reads, and transport happen afterwards, so the same instance can be sent concurrently without being modified. |
| Mailable.envelope | from orionis.mail import Mailable | [mailable.py](../mailable.py) | def envelope(self) -> Envelope | Declare headers and recipients synchronously. Returns ------- Envelope Immutable envelope, augmented by explicit PendingMail data. |
| Mailable.content | from orionis.mail import Mailable | [mailable.py](../mailable.py) | def content(self) -> Content | Declare literal bodies or views synchronously. Returns ------- Content Content whose rendering is deferred until sending. |
| Mailable.attachments | from orionis.mail import Mailable | [mailable.py](../mailable.py) | def attachments(self) -> Sequence[Attachment] | Declare deferred storage attachments synchronously. Returns ------- Sequence[Attachment] Empty by default; subclasses may return their own declarations. |
| Message | from orionis.mail import Message | [message.py](../message.py) | Message | Configure one direct send without exposing a mutable MIME message. The instance belongs to a single operation: a callback receives it once, and the options it holds are snapshotted before preparation starts. |
| Message.fromAddress | from orionis.mail import Message | [message.py](../message.py) | def fromAddress(self, address: str / Address, name: str / None) -> Self | Replace the From header and the transport sender. Parameters ---------- address : str / Address Exactly one sender mailbox. name : str / None Display name for a string mailbox only. Returns ------- Self This configurator. |
| Message.to | from orionis.mail import Message | [message.py](../message.py) | def to(self, addresses: Recipients, name: str / None) -> Self | Append primary visible recipients. Parameters ---------- addresses : Recipients One mailbox or a list/tuple of mailboxes. name : str / None Display name for one string mailbox only. Returns ------- Self This configurator. |
| Message.cc | from orionis.mail import Message | [message.py](../message.py) | def cc(self, addresses: Recipients, name: str / None) -> Self | Append carbon-copy recipients. Parameters ---------- addresses : Recipients One mailbox or a list/tuple of mailboxes. name : str / None Display name for one string mailbox only. Returns ------- Self This configurator. |
| Message.bcc | from orionis.mail import Message | [message.py](../message.py) | def bcc(self, addresses: Recipients, name: str / None) -> Self | Append hidden transport recipients. Parameters ---------- addresses : Recipients One mailbox or a list/tuple of mailboxes. name : str / None Display name for one string mailbox only. Returns ------- Self This configurator. |
| Message.replyTo | from orionis.mail import Message | [message.py](../message.py) | def replyTo(self, addresses: Recipients, name: str / None) -> Self | Append Reply-To mailboxes without adding transport recipients. Parameters ---------- addresses : Recipients One mailbox or a list/tuple of mailboxes. name : str / None Display name for one string mailbox only. Returns ------- Self This configurator. |
| Message.subject | from orionis.mail import Message | [message.py](../message.py) | def subject(self, value: str) -> Self | Replace the literal subject, including with an empty string. Parameters ---------- value : str Subject without control characters. Returns ------- Self This configurator. |
| Message.attach | from orionis.mail import Message | [message.py](../message.py) | def attach(self, attachment: Attachment) -> Self | Append a deferred storage attachment. Parameters ---------- attachment : Attachment Safe immutable attachment declaration. Returns ------- Self This configurator. Raises ------ MailCompositionException If the supplied object is not an Attachment. |
| PendingMail | from orionis.mail import PendingMail | [pending.py](../pending.py) | PendingMail | Build independent chains; every fluent call returns a new operation. A chain never builds a Mailable, renders, reads attachments, or resolves a transport: those steps belong to the asynchronous terminals. Deriving a chain copies its immutable options, so concurrent branches never share recipients. |
| PendingMail.mailer | from orionis.mail import PendingMail | [pending.py](../pending.py) | def mailer(self, name: str) -> PendingMail | Select a mailer on an independent derived chain. Parameters ---------- name : str Central configuration name, not a driver name. Returns ------- PendingMail A new operation; resolution remains deferred until sending. Raises ------ MailConfigurationException If the name is not a non-empty string. |
| PendingMail.fromAddress | from orionis.mail import PendingMail | [pending.py](../pending.py) | def fromAddress(self, address: str / Address, name: str / None) -> PendingMail | Replace the sender on a new independent chain. Parameters ---------- address : str / Address Exactly one sender mailbox. name : str / None Optional name for a string mailbox only. Returns ------- PendingMail Derived operation with an explicit From and transport sender. |
| PendingMail.to | from orionis.mail import PendingMail | [pending.py](../pending.py) | def to(self, addresses: Recipients, name: str / None) -> PendingMail | Append visible recipients on an independent chain. Parameters ---------- addresses : Recipients One mailbox or a list/tuple of mailboxes. name : str / None Optional name for a single string mailbox only. Returns ------- PendingMail Derived operation retaining previous recipients. |
| PendingMail.cc | from orionis.mail import PendingMail | [pending.py](../pending.py) | def cc(self, addresses: Recipients, name: str / None) -> PendingMail | Append carbon-copy recipients on an independent chain. Parameters ---------- addresses : Recipients One mailbox or a list/tuple of mailboxes. name : str / None Optional name for a single string mailbox only. Returns ------- PendingMail Derived operation retaining previous recipients. |
| PendingMail.bcc | from orionis.mail import PendingMail | [pending.py](../pending.py) | def bcc(self, addresses: Recipients, name: str / None) -> PendingMail | Append hidden recipients on an independent chain. Parameters ---------- addresses : Recipients One mailbox or a list/tuple of mailboxes. name : str / None Optional name for a single string mailbox only. Returns ------- PendingMail Derived operation retaining previous recipients. |
| PendingMail.replyTo | from orionis.mail import PendingMail | [pending.py](../pending.py) | def replyTo(self, addresses: Recipients, name: str / None) -> PendingMail | Append Reply-To mailboxes on an independent chain. Parameters ---------- addresses : Recipients One mailbox or a list/tuple of mailboxes. name : str / None Optional name for a single string mailbox only. Returns ------- PendingMail Derived operation retaining previous reply destinations. |
| PendingMail.subject | from orionis.mail import PendingMail | [pending.py](../pending.py) | def subject(self, value: str) -> PendingMail | Replace the subject on an independent chain. Parameters ---------- value : str Literal subject, possibly empty. Returns ------- PendingMail Derived operation with an explicit subject. |
| PendingMail.attach | from orionis.mail import PendingMail | [pending.py](../pending.py) | def attach(self, attachment: Attachment) -> PendingMail | Append a deferred storage attachment on an independent chain. Parameters ---------- attachment : Attachment Storage attachment declaration. Returns ------- PendingMail Derived operation retaining previous attachments. |
| PendingMail.send | from orionis.mail import PendingMail | [pending.py](../pending.py) | async def send(self, mailable: Mailable / type[Mailable]) -> MailResult | Public method without a docstring. |
| PendingMail.send | from orionis.mail import PendingMail | [pending.py](../pending.py) | async def send(self, view: str, data: Mapping[str, object] / None, callback: MessageCallback / None) -> MailResult | Public method without a docstring. |
| PendingMail.send | from orionis.mail import PendingMail | [pending.py](../pending.py) | async def send(self, content: Content, *, callback: MessageCallback / None) -> MailResult | Public method without a docstring. |
| PendingMail.send | from orionis.mail import PendingMail | [pending.py](../pending.py) | async def send(self, value: Mailable / type[Mailable] / str / Content, data: object, callback: object) -> MailResult | Send a reusable Mailable, an HTML view, or explicit Content. Parameters ---------- value : Mailable / type[Mailable] / str / Content Declaration, resolvable Mailable class, or HTML view identifier. data : Mapping[str, object] / None View context, accepted only when value is a string. callback : MessageCallback / None Operation-local configurator, not accepted for a Mailable. Returns ------- MailResult Confirmed SMTP acceptance or file publication result. Raises ------ MailCompositionException If arguments, container resolution, declarations, callbacks, or content are invalid. MailException If preparation or transport fails. |
| PendingMail.raw | from orionis.mail import PendingMail | [pending.py](../pending.py) | async def raw(self, text: str, callback: MessageCallback / None) -> MailResult | Send literal plain text through the shared preparation pipeline. Parameters ---------- text : str Literal text, never rendered as a template. callback : MessageCallback / None Optional sync or async operation-local configurator. Returns ------- MailResult Transport outcome. Raises ------ MailCompositionException If the body, callback, or resulting envelope is invalid. MailException If preparation or transport fails. |
| PendingMail.html | from orionis.mail import PendingMail | [pending.py](../pending.py) | async def html(self, html: str, callback: MessageCallback / None) -> MailResult | Send literal HTML through the shared preparation pipeline. Parameters ---------- html : str Literal HTML, never rendered as a template. callback : MessageCallback / None Optional sync or async operation-local configurator. Returns ------- MailResult Transport outcome. Raises ------ MailCompositionException If the body, callback, or resulting envelope is invalid. MailException If preparation or transport fails. |

## Usage examples

    from orionis.mail import Address

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
