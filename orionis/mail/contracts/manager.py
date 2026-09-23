from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, overload
from orionis.support.types.sentinel import MISSING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.mail.entities.address import Address
    from orionis.mail.entities.attachment import Attachment
    from orionis.mail.entities.content import Content
    from orionis.mail.entities.result import MailResult
    from orionis.mail.mailable import Mailable
    from orionis.mail.pending import PendingMail
    from orionis.mail.types import MessageCallback, Recipients, TransportFactory

class IMailManager(ABC):
    """
    Expose independent composition and centrally configured mail delivery.

    Composition methods are synchronous and always return a new operation.
    Terminal operations are asynchronous and resolve the configured transport
    only after the message has been prepared.
    """

    __slots__ = ()

    @abstractmethod
    def mailer(self, name: str) -> PendingMail:
        """
        Start an independent chain selecting a named mailer.

        Parameters
        ----------
        name : str
            Configuration name, not a transport driver name.

        Returns
        -------
        PendingMail
            A synchronous chain with lazy transport resolution.

        Raises
        ------
        MailConfigurationException
            If the name is not a non-empty string.
        """

    @abstractmethod
    def fromAddress(
        self,
        address: str | Address,
        name: str | None = None,
    ) -> PendingMail:
        """
        Start an independent chain with exactly one sender.

        Parameters
        ----------
        address : str | Address
            From header and transport sender.
        name : str | None
            Optional display name, valid only with a string address.

        Returns
        -------
        PendingMail
            A synchronous chain without I/O.

        Raises
        ------
        MailCompositionException
            If the mailbox is invalid or a name is supplied twice.
        """

    @abstractmethod
    def to(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Start an independent chain with primary recipients.

        Parameters
        ----------
        addresses : Recipients
            Single mailbox or list/tuple of mailboxes.
        name : str | None
            Display name for a single string mailbox only.

        Returns
        -------
        PendingMail
            A synchronous independent chain.

        Raises
        ------
        MailCompositionException
            If a mailbox is invalid or combined with an ambiguous name.
        """

    @abstractmethod
    def cc(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Start an independent chain with carbon-copy recipients.

        Parameters
        ----------
        addresses : Recipients
            Single mailbox or list/tuple of mailboxes.
        name : str | None
            Display name for a single string mailbox only.

        Returns
        -------
        PendingMail
            A synchronous independent chain.

        Raises
        ------
        MailCompositionException
            If a mailbox is invalid or combined with an ambiguous name.
        """

    @abstractmethod
    def bcc(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Start an independent chain with hidden recipients.

        Parameters
        ----------
        addresses : Recipients
            Single mailbox or list/tuple of mailboxes.
        name : str | None
            Display name for a single string mailbox only.

        Returns
        -------
        PendingMail
            A synchronous independent chain.

        Raises
        ------
        MailCompositionException
            If a mailbox is invalid or combined with an ambiguous name.
        """

    @abstractmethod
    def replyTo(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Start an independent chain with reply destinations.

        Parameters
        ----------
        addresses : Recipients
            Single mailbox or list/tuple of mailboxes.
        name : str | None
            Display name for a single string mailbox only.

        Returns
        -------
        PendingMail
            A synchronous independent chain.

        Raises
        ------
        MailCompositionException
            If a mailbox is invalid or combined with an ambiguous name.
        """

    @abstractmethod
    def subject(self, value: str) -> PendingMail:
        """
        Start an independent chain with a literal subject.

        Parameters
        ----------
        value : str
            Subject without control characters.

        Returns
        -------
        PendingMail
            A synchronous independent chain.

        Raises
        ------
        MailCompositionException
            If the subject is not text or contains control characters.
        """

    @abstractmethod
    def attach(self, attachment: Attachment) -> PendingMail:
        """
        Start an independent chain with a deferred attachment.

        Parameters
        ----------
        attachment : Attachment
            Storage attachment declaration.

        Returns
        -------
        PendingMail
            A synchronous independent chain.

        Raises
        ------
        MailCompositionException
            If the value is not an attachment declaration.
        """

    @overload
    async def send(self, mailable: Mailable, /) -> MailResult: ...

    @overload
    async def send(
        self,
        view: str,
        /,
        data: Mapping[str, object] | None = None,
        callback: MessageCallback | None = None,
    ) -> MailResult: ...

    @overload
    async def send(
        self,
        content: Content,
        /,
        *,
        callback: MessageCallback | None = None,
    ) -> MailResult: ...

    @abstractmethod
    async def send(
        self,
        value: Mailable | str | Content,
        /,
        data: object = MISSING,
        callback: object = MISSING,
    ) -> MailResult:
        """
        Send a Mailable, an HTML view, or Content through one pipeline.

        Parameters
        ----------
        value : Mailable | str | Content
            A string always names an HTML view.
        data : Mapping[str, object] | None
            Explicit view data, allowed only with a string view name.
        callback : MessageCallback | None
            Sync or async Message configurator, forbidden with a Mailable.

        Returns
        -------
        MailResult
            Confirmed acceptance, partial acceptance, or file storage.

        Raises
        ------
        MailException
            If configuration, preparation, or transport fails.
        """

    @abstractmethod
    async def raw(
        self,
        text: str,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """
        Send literal plain text without template interpretation.

        Parameters
        ----------
        text : str
            Literal text, possibly empty.
        callback : MessageCallback | None
            Optional operation-local configurator.

        Returns
        -------
        MailResult
            Transport outcome.

        Raises
        ------
        MailException
            If configuration, preparation, or transport fails.
        """

    @abstractmethod
    async def html(
        self,
        html: str,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """
        Send literal HTML without template interpretation.

        Parameters
        ----------
        html : str
            Literal HTML, possibly empty.
        callback : MessageCallback | None
            Optional operation-local configurator.

        Returns
        -------
        MailResult
            Transport outcome.

        Raises
        ------
        MailException
            If configuration, preparation, or transport fails.
        """

    @abstractmethod
    def extend(self, driver: str, factory: TransportFactory) -> None:
        """
        Register one sync or async factory for a new driver.

        Parameters
        ----------
        driver : str
            Unique transport implementation name.
        factory : TransportFactory
            Callable receiving the application and the normalized configuration
            and returning an IMailTransport or an awaitable of one.

        Returns
        -------
        None
            Register lazily without constructing a transport.

        Raises
        ------
        MailConfigurationException
            If the name or factory is invalid or the driver already exists.
        """
