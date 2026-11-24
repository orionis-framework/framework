# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from collections.abc import Mapping
from typing import overload
from orionis.container.facades.facade import Facade
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.result import MailResult
from orionis.mail.mailable import Mailable
from orionis.mail.pending import PendingMail
from orionis.mail.types import MessageCallback, Recipients, TransportFactory

class Mail(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IMailManager]:
        """Return the contract registered for the mail manager."""

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IMailManager:
        """Resolve the mail manager from the application container."""

    @classmethod
    def mailer(cls, name: str) -> PendingMail:
        """Start an independent chain selecting a named mailer."""

    @classmethod
    def fromAddress(
        cls,
        address: str | Address,
        name: str | None = None,
    ) -> PendingMail:
        """Start an independent chain with exactly one sender."""

    @classmethod
    def to(cls, addresses: Recipients, name: str | None = None) -> PendingMail:
        """Start an independent chain with primary recipients."""

    @classmethod
    def cc(cls, addresses: Recipients, name: str | None = None) -> PendingMail:
        """Start an independent chain with carbon-copy recipients."""

    @classmethod
    def bcc(cls, addresses: Recipients, name: str | None = None) -> PendingMail:
        """Start an independent chain with hidden recipients."""

    @classmethod
    def replyTo(cls, addresses: Recipients, name: str | None = None) -> PendingMail:
        """Start an independent chain with reply destinations."""

    @classmethod
    def subject(cls, value: str) -> PendingMail:
        """Start an independent chain with a literal subject."""

    @classmethod
    def attach(cls, attachment: Attachment) -> PendingMail:
        """Start an independent chain with a deferred attachment."""

    @overload
    @classmethod
    async def send(cls, mailable: Mailable | type[Mailable], /) -> MailResult:
        """Send a reusable mail declaration through the configured transport."""

    @overload
    @classmethod
    async def send(
        cls,
        view: str,
        /,
        data: Mapping[str, object] | None = None,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """Render and send an HTML template with optional message customization."""

    @overload
    @classmethod
    async def send(
        cls,
        content: Content,
        /,
        *,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """Send explicit message content with optional customization."""

    @classmethod
    async def raw(
        cls,
        text: str,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """Send literal plain text without template interpretation."""

    @classmethod
    async def html(
        cls,
        html: str,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """Send literal HTML without template interpretation."""

    @classmethod
    def extend(cls, driver: str, factory: TransportFactory) -> None:
        """Register a transport factory for a custom mail driver."""
