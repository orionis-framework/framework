# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from collections.abc import Mapping
from typing import overload
from orionis.container.contracts.facade import IFacade
from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.result import MailResult
from orionis.mail.mailable import Mailable
from orionis.mail.pending import PendingMail
from orionis.mail.types import MessageCallback, Recipients

class Mail(IFacade):
    @staticmethod
    def mailer(name: str) -> PendingMail:
        """Start an independent chain selecting a named mailer."""

    @staticmethod
    def fromAddress(address: str | Address, name: str | None = None) -> PendingMail:
        """Start an independent chain with exactly one sender."""

    @staticmethod
    def to(addresses: Recipients, name: str | None = None) -> PendingMail:
        """Start an independent chain with primary recipients."""

    @staticmethod
    def cc(addresses: Recipients, name: str | None = None) -> PendingMail:
        """Start an independent chain with carbon-copy recipients."""

    @staticmethod
    def bcc(addresses: Recipients, name: str | None = None) -> PendingMail:
        """Start an independent chain with hidden recipients."""

    @staticmethod
    def replyTo(addresses: Recipients, name: str | None = None) -> PendingMail:
        """Start an independent chain with reply destinations."""

    @staticmethod
    def subject(value: str) -> PendingMail:
        """Start an independent chain with a literal subject."""

    @staticmethod
    def attach(attachment: Attachment) -> PendingMail:
        """Start an independent chain with a deferred attachment."""

    @overload
    @staticmethod
    async def send(mailable: Mailable | type[Mailable], /) -> MailResult:
        """Send a reusable mail declaration through the configured transport."""

    @overload
    @staticmethod
    async def send(
        view: str,
        /,
        data: Mapping[str, object] | None = None,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """Render and send an HTML template with optional message customization."""

    @overload
    @staticmethod
    async def send(
        content: Content,
        /,
        *,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """Send explicit message content with optional customization."""

    @staticmethod
    async def raw(text: str, callback: MessageCallback | None = None) -> MailResult:
        """Send literal plain text without template interpretation."""

    @staticmethod
    async def html(
        html: str,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """Send literal HTML without template interpretation."""
