from collections.abc import Mapping, Sequence
from dataclasses import replace
from inspect import isawaitable, iscoroutine
from typing import TYPE_CHECKING, cast, overload
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.envelope import Envelope
from orionis.mail.entities.options import MailOptions
from orionis.mail.exceptions import MailCompositionException, MailConfigurationException
from orionis.mail.mailable import Mailable
from orionis.mail.message import Message
from orionis.support.types.sentinel import MISSING

if TYPE_CHECKING:
    from orionis.mail.entities.address import Address
    from orionis.mail.entities.result import MailResult
    from orionis.mail.types import Delivery, MessageCallback, Recipients

class PendingMail:
    """
    Build independent chains; every fluent call returns a new operation.

    A chain never renders, reads attachments, or resolves a transport: those
    steps belong to the asynchronous terminals. Deriving a chain copies its
    immutable options, so concurrent branches never share recipients.
    """

    __slots__ = ("_delivery", "_options")

    def __init__(self, delivery: Delivery, options: MailOptions | None = None) -> None:
        """
        Bind an immutable declaration to the manager's delivery pipeline.

        Parameters
        ----------
        delivery : Delivery
            Shared preparation and transport entry point.
        options : MailOptions | None
            Immutable explicit options for this chain.

        Returns
        -------
        None
            Initialize a chain without performing I/O.
        """
        self._delivery = delivery
        self._options = options if options is not None else MailOptions()

    def mailer(self, name: str) -> PendingMail:
        """
        Select a mailer on an independent derived chain.

        Parameters
        ----------
        name : str
            Central configuration name, not a driver name.

        Returns
        -------
        PendingMail
            A new operation; resolution remains deferred until sending.

        Raises
        ------
        MailConfigurationException
            If the name is not a non-empty string.
        """
        if not isinstance(name, str) or not name.strip():
            error_msg = "Mailer names must be non-empty strings."
            raise MailConfigurationException(error_msg)
        return PendingMail(self._delivery, replace(self._options, mailer=name))

    def fromAddress(
        self,
        address: str | Address,
        name: str | None = None,
    ) -> PendingMail:
        """
        Replace the sender on a new independent chain.

        Parameters
        ----------
        address : str | Address
            Exactly one sender mailbox.
        name : str | None
            Optional name for a string mailbox only.

        Returns
        -------
        PendingMail
            Derived operation with an explicit From and transport sender.
        """
        return self._derive(Message(self._options).fromAddress(address, name))

    def to(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Append visible recipients on an independent chain.

        Parameters
        ----------
        addresses : Recipients
            One mailbox or a list/tuple of mailboxes.
        name : str | None
            Optional name for a single string mailbox only.

        Returns
        -------
        PendingMail
            Derived operation retaining previous recipients.
        """
        return self._derive(Message(self._options).to(addresses, name))

    def cc(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Append carbon-copy recipients on an independent chain.

        Parameters
        ----------
        addresses : Recipients
            One mailbox or a list/tuple of mailboxes.
        name : str | None
            Optional name for a single string mailbox only.

        Returns
        -------
        PendingMail
            Derived operation retaining previous recipients.
        """
        return self._derive(Message(self._options).cc(addresses, name))

    def bcc(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Append hidden recipients on an independent chain.

        Parameters
        ----------
        addresses : Recipients
            One mailbox or a list/tuple of mailboxes.
        name : str | None
            Optional name for a single string mailbox only.

        Returns
        -------
        PendingMail
            Derived operation retaining previous recipients.
        """
        return self._derive(Message(self._options).bcc(addresses, name))

    def replyTo(self, addresses: Recipients, name: str | None = None) -> PendingMail:
        """
        Append Reply-To mailboxes on an independent chain.

        Parameters
        ----------
        addresses : Recipients
            One mailbox or a list/tuple of mailboxes.
        name : str | None
            Optional name for a single string mailbox only.

        Returns
        -------
        PendingMail
            Derived operation retaining previous reply destinations.
        """
        return self._derive(Message(self._options).replyTo(addresses, name))

    def subject(self, value: str) -> PendingMail:
        """
        Replace the subject on an independent chain.

        Parameters
        ----------
        value : str
            Literal subject, possibly empty.

        Returns
        -------
        PendingMail
            Derived operation with an explicit subject.
        """
        return self._derive(Message(self._options).subject(value))

    def attach(self, attachment: Attachment) -> PendingMail:
        """
        Append a deferred storage attachment on an independent chain.

        Parameters
        ----------
        attachment : Attachment
            Storage attachment declaration.

        Returns
        -------
        PendingMail
            Derived operation retaining previous attachments.
        """
        return self._derive(Message(self._options).attach(attachment))

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

    async def send(
        self,
        value: Mailable | str | Content,
        /,
        data: object = MISSING,
        callback: object = MISSING,
    ) -> MailResult:
        """
        Send a reusable Mailable, an HTML view, or explicit Content.

        Parameters
        ----------
        value : Mailable | str | Content
            Declaration; a string always identifies an HTML view.
        data : Mapping[str, object] | None
            View context, accepted only when value is a string.
        callback : MessageCallback | None
            Operation-local configurator, not accepted for a Mailable.

        Returns
        -------
        MailResult
            Confirmed SMTP acceptance or file publication result.

        Raises
        ------
        MailCompositionException
            If arguments, declarations, callbacks, or content are invalid.
        MailException
            If preparation or transport fails.
        """
        if isinstance(value, Mailable):

            # A Mailable owns its context, so supplying either argument here
            # would silently drop it.
            if data is not MISSING or callback is not MISSING:
                error_msg = "send(mailable) accepts neither data nor callback."
                raise MailCompositionException(error_msg)
            return await self._sendMailable(value)

        if isinstance(value, Content):
            if data is not MISSING:
                error_msg = "Content carries its own data; extra data is invalid."
                raise MailCompositionException(error_msg)
            content = value
        elif isinstance(value, str):
            content = Content(
                view=value,
                data=None if data is MISSING else cast("Mapping[str, object]", data),
            )
        else:
            error_msg = "send() requires a Mailable, view identifier, or Content."
            raise MailCompositionException(error_msg)

        configured = None if callback is MISSING else callback
        return await self._sendDirect(content, configured)

    async def raw(
        self,
        text: str,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """
        Send literal plain text through the shared preparation pipeline.

        Parameters
        ----------
        text : str
            Literal text, never rendered as a template.
        callback : MessageCallback | None
            Optional sync or async operation-local configurator.

        Returns
        -------
        MailResult
            Transport outcome.

        Raises
        ------
        MailCompositionException
            If the body, callback, or resulting envelope is invalid.
        MailException
            If preparation or transport fails.
        """
        return await self._sendDirect(Content(text=text), callback)

    async def html(
        self,
        html: str,
        callback: MessageCallback | None = None,
    ) -> MailResult:
        """
        Send literal HTML through the shared preparation pipeline.

        Parameters
        ----------
        html : str
            Literal HTML, never rendered as a template.
        callback : MessageCallback | None
            Optional sync or async operation-local configurator.

        Returns
        -------
        MailResult
            Transport outcome.

        Raises
        ------
        MailCompositionException
            If the body, callback, or resulting envelope is invalid.
        MailException
            If preparation or transport fails.
        """
        return await self._sendDirect(Content(html=html), callback)

    def _derive(self, message: Message) -> PendingMail:
        """
        Detach a configurator's current snapshot into a new chain.

        Parameters
        ----------
        message : Message
            Temporary synchronous configurator.

        Returns
        -------
        PendingMail
            Independent operation with no render or transport side effects.
        """
        return PendingMail(self._delivery, message._snapshot())  # noqa: SLF001

    async def _sendDirect(self, content: Content, callback: object) -> MailResult:
        """
        Invoke one callback, freeze its declaration, and deliver.

        Parameters
        ----------
        content : Content
            Already validated content declaration.
        callback : object
            Configurator invoked exactly once and awaited when needed.

        Returns
        -------
        MailResult
            Shared delivery outcome.

        Raises
        ------
        MailCompositionException
            If a callback fails or returns anything other than None or itself.
        """
        message = Message(self._options)
        if callback is not None:
            await _run_callback(callback, message)

        options = message._snapshot()  # noqa: SLF001
        return await self._delivery(
            options.mailer,
            options.envelope(),
            content,
            options.attachments,
        )

    async def _sendMailable(self, mailable: Mailable) -> MailResult:
        """
        Merge reusable declarations with explicit fluent options.

        Parameters
        ----------
        mailable : Mailable
            Reusable synchronous declaration, never modified by sending.

        Returns
        -------
        MailResult
            Shared delivery outcome.

        Raises
        ------
        MailCompositionException
            If declaration methods fail or do not return their contracted types.
        """
        try:
            envelope = mailable.envelope()
            _assert_declaration(envelope, Envelope, "envelope")
            content = mailable.content()
            _assert_declaration(content, Content, "content")
            attachments = mailable.attachments()
            _assert_declaration(attachments, Sequence, "attachments")
            for attachment in attachments:
                _assert_declaration(attachment, Attachment, "attachment")
        except MailCompositionException:
            raise
        except Exception as exc:
            error_msg = "Mailable declaration failed before transport."
            raise MailCompositionException(error_msg) from exc

        return await self._delivery(
            self._options.mailer,
            self._options.envelope(envelope),
            content,
            (*attachments, *self._options.attachments),
        )

async def _run_callback(callback: object, message: Message) -> None:
    """
    Run one configurator exactly once and await an asynchronous result.

    Parameters
    ----------
    callback : object
        Function, method, or callable object supplied by the caller.
    message : Message
        Configurator exclusive to the current operation.

    Returns
    -------
    None
        Apply the callback mutations to the supplied message.

    Raises
    ------
    MailCompositionException
        If the callback is not callable, fails, or returns another value.
    """
    if not callable(callback):
        error_msg = "The mail callback must be callable."
        raise MailCompositionException(error_msg)

    configurator = cast("MessageCallback", callback)
    try:
        result = configurator(message)
        if isawaitable(result):
            result = await result
    except MailCompositionException:
        raise
    except Exception as exc:
        error_msg = "Mail configuration callback failed before transport."
        raise MailCompositionException(error_msg) from exc

    # Returning False never cancels an operation: only None or the received
    # message are valid outcomes.
    if result is not None and result is not message:
        error_msg = "Mail callbacks must return None or the received Message."
        raise MailCompositionException(error_msg)

def _assert_declaration(value: object, expected: type, label: str) -> None:
    """
    Reject invalid synchronous declarations without leaking coroutines.

    Parameters
    ----------
    value : object
        Declaration result.
    expected : type
        Required runtime type.
    label : str
        Declaration method or field name.

    Returns
    -------
    None
        Accept only the required type.

    Raises
    ------
    MailCompositionException
        If the declared value violates its synchronous contract.
    """
    if isinstance(value, expected):
        return

    # Close an async declaration so rejecting it never emits a warning about
    # a coroutine that was never awaited.
    if iscoroutine(value):
        value.close()

    error_msg = f"Mailable {label}() must return {expected.__name__} synchronously."
    raise MailCompositionException(error_msg)
