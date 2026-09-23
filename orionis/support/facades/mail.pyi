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
    def mailer(name: str) -> PendingMail: ...
    @staticmethod
    def fromAddress(address: str | Address, name: str | None = None) -> PendingMail: ...
    @staticmethod
    def to(addresses: Recipients, name: str | None = None) -> PendingMail: ...
    @staticmethod
    def cc(addresses: Recipients, name: str | None = None) -> PendingMail: ...
    @staticmethod
    def bcc(addresses: Recipients, name: str | None = None) -> PendingMail: ...
    @staticmethod
    def replyTo(addresses: Recipients, name: str | None = None) -> PendingMail: ...
    @staticmethod
    def subject(value: str) -> PendingMail: ...
    @staticmethod
    def attach(attachment: Attachment) -> PendingMail: ...
    @overload
    @staticmethod
    async def send(mailable: Mailable, /) -> MailResult: ...
    @overload
    @staticmethod
    async def send(
        view: str,
        /,
        data: Mapping[str, object] | None = None,
        callback: MessageCallback | None = None,
    ) -> MailResult: ...
    @overload
    @staticmethod
    async def send(
        content: Content,
        /,
        *,
        callback: MessageCallback | None = None,
    ) -> MailResult: ...
    @staticmethod
    async def raw(text: str, callback: MessageCallback | None = None) -> MailResult: ...
    @staticmethod
    async def html(
        html: str,
        callback: MessageCallback | None = None,
    ) -> MailResult: ...
