from dataclasses import replace
from typing import TYPE_CHECKING, Self
from orionis.mail.entities.address import Address, addresses, one_address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.options import MailOptions
from orionis.mail.exceptions import MailCompositionException
from orionis.mail.functions import header_value

if TYPE_CHECKING:
    from orionis.mail.types import Recipients

class Message:
    """
    Configure one direct send without exposing a mutable MIME message.

    The instance belongs to a single operation: a callback receives it once,
    and the options it holds are snapshotted before preparation starts.
    """

    __slots__ = ("_options",)

    def __init__(self, options: MailOptions | None = None) -> None:
        """
        Initialize an operation-local mutable configurator.

        Parameters
        ----------
        options : MailOptions | None
            Initial immutable snapshot supplied by PendingMail.

        Returns
        -------
        None
            Retain an immutable snapshot, replaced by each mutator.
        """
        self._options = options if options is not None else MailOptions()

    def fromAddress(self, address: str | Address, name: str | None = None) -> Self:
        """
        Replace the From header and the transport sender.

        Parameters
        ----------
        address : str | Address
            Exactly one sender mailbox.
        name : str | None
            Display name for a string mailbox only.

        Returns
        -------
        Self
            This configurator.
        """
        self._options = replace(
            self._options,
            from_address=one_address(address, name),
        )
        return self

    def to(self, addresses: Recipients, name: str | None = None) -> Self:
        """
        Append primary visible recipients.

        Parameters
        ----------
        addresses : Recipients
            One mailbox or a list/tuple of mailboxes.
        name : str | None
            Display name for one string mailbox only.

        Returns
        -------
        Self
            This configurator.
        """
        return self._appendRecipients("to", addresses, name)

    def cc(self, addresses: Recipients, name: str | None = None) -> Self:
        """
        Append carbon-copy recipients.

        Parameters
        ----------
        addresses : Recipients
            One mailbox or a list/tuple of mailboxes.
        name : str | None
            Display name for one string mailbox only.

        Returns
        -------
        Self
            This configurator.
        """
        return self._appendRecipients("cc", addresses, name)

    def bcc(self, addresses: Recipients, name: str | None = None) -> Self:
        """
        Append hidden transport recipients.

        Parameters
        ----------
        addresses : Recipients
            One mailbox or a list/tuple of mailboxes.
        name : str | None
            Display name for one string mailbox only.

        Returns
        -------
        Self
            This configurator.
        """
        return self._appendRecipients("bcc", addresses, name)

    def replyTo(self, addresses: Recipients, name: str | None = None) -> Self:
        """
        Append Reply-To mailboxes without adding transport recipients.

        Parameters
        ----------
        addresses : Recipients
            One mailbox or a list/tuple of mailboxes.
        name : str | None
            Display name for one string mailbox only.

        Returns
        -------
        Self
            This configurator.
        """
        return self._appendRecipients("reply_to", addresses, name)

    def subject(self, value: str) -> Self:
        """
        Replace the literal subject, including with an empty string.

        Parameters
        ----------
        value : str
            Subject without control characters.

        Returns
        -------
        Self
            This configurator.
        """
        self._options = replace(self._options, subject=header_value(value, "Subject"))
        return self

    def attach(self, attachment: Attachment) -> Self:
        """
        Append a deferred storage attachment.

        Parameters
        ----------
        attachment : Attachment
            Safe immutable attachment declaration.

        Returns
        -------
        Self
            This configurator.

        Raises
        ------
        MailCompositionException
            If the supplied object is not an Attachment.
        """
        if not isinstance(attachment, Attachment):
            error_msg = "attach() requires an Attachment declaration."
            raise MailCompositionException(error_msg)
        self._options = replace(
            self._options,
            attachments=(*self._options.attachments, attachment),
        )
        return self

    def _appendRecipients(
        self,
        field: str,
        value: Recipients,
        name: str | None,
    ) -> Self:
        """
        Append normalized recipients to one internal address field.

        Parameters
        ----------
        field : str
            Internal recipient collection name.
        value : Recipients
            Supplied recipient declaration.
        name : str | None
            Optional single-mailbox display name.

        Returns
        -------
        Self
            This configurator with its snapshot replaced.
        """
        added = addresses(value, name)
        current = getattr(self._options, field)
        self._options = replace(self._options, **{field: (*current, *added)})
        return self

    def _snapshot(self) -> MailOptions:
        """
        Return the immutable current declaration for preparation.

        Returns
        -------
        MailOptions
            A snapshot unaffected by later mutations of this Message.
        """
        return self._options
