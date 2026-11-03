"""Expose independent composition and centrally configured mail delivery."""

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
    """Declare that this class introduces no additional instance slots."""

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
        orionis.mail.PendingMail
            A synchronous chain with lazy transport resolution.

        Raises
        ------
        orionis.mail.exceptions.MailConfigurationException
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
        address : str | orionis.mail.entities.Address
            From header and transport sender.
        name : str | None
            Optional display name, valid only with a string address.

        Returns
        -------
        orionis.mail.PendingMail
            A synchronous chain without I/O.

        Raises
        ------
        orionis.mail.exceptions.MailCompositionException
            If the mailbox is invalid or a name is supplied twice.
        """

    @abstractmethod
    def to(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Start an independent chain with primary recipients.

        Parameters
        ----------
        addresses : orionis.mail.types.Recipients
            Single mailbox or list/tuple of mailboxes.
        name : str | None
            Display name for a single string mailbox only.

        Returns
        -------
        orionis.mail.PendingMail
            A synchronous independent chain.

        Raises
        ------
        orionis.mail.exceptions.MailCompositionException
            If a mailbox is invalid or combined with an ambiguous name.
        """

    @abstractmethod
    def cc(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Start an independent chain with carbon-copy recipients.

        Parameters
        ----------
        addresses : orionis.mail.types.Recipients
            Single mailbox or list/tuple of mailboxes.
        name : str | None
            Display name for a single string mailbox only.

        Returns
        -------
        orionis.mail.PendingMail
            A synchronous independent chain.

        Raises
        ------
        orionis.mail.exceptions.MailCompositionException
            If a mailbox is invalid or combined with an ambiguous name.
        """

    @abstractmethod
    def bcc(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Start an independent chain with hidden recipients.

        Parameters
        ----------
        addresses : orionis.mail.types.Recipients
            Single mailbox or list/tuple of mailboxes.
        name : str | None
            Display name for a single string mailbox only.

        Returns
        -------
        orionis.mail.PendingMail
            A synchronous independent chain.

        Raises
        ------
        orionis.mail.exceptions.MailCompositionException
            If a mailbox is invalid or combined with an ambiguous name.
        """

    @abstractmethod
    def replyTo(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Start an independent chain with reply destinations.

        Parameters
        ----------
        addresses : orionis.mail.types.Recipients
            Single mailbox or list/tuple of mailboxes.
        name : str | None
            Display name for a single string mailbox only.

        Returns
        -------
        orionis.mail.PendingMail
            A synchronous independent chain.

        Raises
        ------
        orionis.mail.exceptions.MailCompositionException
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
        orionis.mail.PendingMail
            A synchronous independent chain.

        Raises
        ------
        orionis.mail.exceptions.MailCompositionException
            If the subject is not text or contains control characters.
        """

    @abstractmethod
    def attach(self, attachment: Attachment) -> PendingMail:
        """
        Start an independent chain with a deferred attachment.

        Parameters
        ----------
        attachment : orionis.mail.entities.Attachment
            Storage attachment declaration.

        Returns
        -------
        orionis.mail.PendingMail
            A synchronous independent chain.

        Raises
        ------
        orionis.mail.exceptions.MailCompositionException
            If the value is not an attachment declaration.
        """

    @overload
    async def send(self, mailable: Mailable | type[Mailable], /) -> MailResult:
        ...

    @overload
    async def send(
        self,
        view: str,
        /,
        data: Mapping[str, object] | None = None,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        ...

    @overload
    async def send(
        self,
        content: Content,
        /,
        *,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        ...

    @abstractmethod
    async def send(
        self,
        value: Mailable | type[Mailable] | str | Content,
        /,
        data: object = MISSING,
        callback: object = MISSING,
    ) -> MailResult:
        """
        Send a Mailable, an HTML view, or Content through one pipeline.

        Parameters
        ----------
        value
            A Mailable instance or class, an HTML view name, or explicit content.
        data : collections.abc.Mapping[str, object] | None
            Explicit view data, allowed only with a string view name.
        callback : orionis.mail.types.MessageCallback | None
            Sync or async Message configurator, forbidden with a Mailable.

        Returns
        -------
        orionis.mail.entities.MailResult
            Confirmed acceptance, partial acceptance, or file storage.

        Raises
        ------
        orionis.mail.exceptions.MailException
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
        callback : orionis.mail.types.MessageCallback | None
            Optional operation-local configurator.

        Returns
        -------
        orionis.mail.entities.MailResult
            Transport outcome.

        Raises
        ------
        orionis.mail.exceptions.MailException
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
        callback : orionis.mail.types.MessageCallback | None
            Optional operation-local configurator.

        Returns
        -------
        orionis.mail.entities.MailResult
            Transport outcome.

        Raises
        ------
        orionis.mail.exceptions.MailException
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
        factory : orionis.mail.types.TransportFactory
            Callable receiving the application and the normalized configuration
            and returning an IMailTransport or an awaitable of one.

        Returns
        -------
        None
            Register lazily without constructing a transport.

        Raises
        ------
        orionis.mail.exceptions.MailConfigurationException
            If the name or factory is invalid or the driver already exists.
        """
