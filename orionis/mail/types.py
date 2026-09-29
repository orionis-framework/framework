from collections.abc import Awaitable, Callable, Mapping
from orionis.foundation.contracts.application import IApplication
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.envelope import Envelope
from orionis.mail.entities.result import MailResult
from orionis.mail.message import Message

# Accepted recipient declaration: one mailbox or a collection of mailboxes.
type Recipients = str | Address | list[str | Address] | tuple[str | Address, ...]

# Operation-local configurator invoked once for a direct send.
type MessageCallback = Callable[[Message], Message | Awaitable[Message | None] | None]

# Shared preparation and transport entry point owned by the manager.
type Delivery = Callable[
    [str | None, Envelope, Content, tuple[Attachment, ...]],
    Awaitable[MailResult],
]

# Driver factory registered through the manager extension point.
type TransportFactory = Callable[
    [IApplication, Mapping[str, object]],
    IMailTransport | Awaitable[IMailTransport],
]
