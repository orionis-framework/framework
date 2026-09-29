from dataclasses import dataclass
from typing import TYPE_CHECKING
from orionis.mail.entities.address import Address, addresses, one_address
from orionis.mail.exceptions import MailCompositionException
from orionis.mail.functions import header_value

if TYPE_CHECKING:
    from orionis.mail.types import Recipients

@dataclass(frozen=True, slots=True, init=False)
class Envelope:
    """
    Store normalized immutable headers and intended recipients.

    Parameters
    ----------
    subject : str
        Literal subject, including an intentionally empty subject.
    from_address : Address | None
        From header and transport sender.
    to : tuple[Address, ...]
        Primary visible recipients.
    cc : tuple[Address, ...]
        Additional visible recipients.
    bcc : tuple[Address, ...]
        Hidden transport recipients.
    reply_to : tuple[Address, ...]
        Reply destinations, which are never transport recipients.
    """

    subject: str
    from_address: Address | None
    to: tuple[Address, ...]
    cc: tuple[Address, ...]
    bcc: tuple[Address, ...]
    reply_to: tuple[Address, ...]

    def __init__(  # noqa: PLR0913
        self,
        *,
        subject: str = "",
        from_address: str | Address | None = None,
        to: Recipients = (),
        cc: Recipients = (),
        bcc: Recipients = (),
        reply_to: Recipients = (),
    ) -> None:
        """
        Normalize a declarative envelope without performing I/O.

        Parameters
        ----------
        subject : str
            Literal subject, including an empty subject.
        from_address : str | Address | None
            From header and transport sender.
        to : Recipients
            Primary visible recipients.
        cc : Recipients
            Additional visible recipients.
        bcc : Recipients
            Hidden transport recipients.
        reply_to : Recipients
            Reply destinations, not transport recipients.

        Returns
        -------
        None
            Copy and validate all address collections.

        Raises
        ------
        MailCompositionException
            If headers are invalid or a hidden recipient is also visible.
        """
        object.__setattr__(self, "subject", header_value(subject, "Subject"))
        object.__setattr__(
            self,
            "from_address",
            one_address(from_address) if from_address is not None else None,
        )
        object.__setattr__(self, "to", addresses(to))
        object.__setattr__(self, "cc", addresses(cc))
        object.__setattr__(self, "bcc", addresses(bcc))
        object.__setattr__(self, "reply_to", addresses(reply_to))

        # A mailbox listed as both visible and hidden makes the intended
        # privacy of the message ambiguous.
        visible = {item.address for item in (*self.to, *self.cc)}
        if any(item.address in visible for item in self.bcc):
            error_msg = "A recipient cannot be both visible (To/Cc) and Bcc."
            raise MailCompositionException(error_msg)

    def recipients(self) -> tuple[str, ...]:
        """
        Return the stable deduplicated transport recipient union.

        Returns
        -------
        tuple[str, ...]
            To, Cc, and Bcc addresses without Reply-To.
        """
        return tuple(
            dict.fromkeys(item.address for item in (*self.to, *self.cc, *self.bcc)),
        )
