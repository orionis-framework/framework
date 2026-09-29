from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING
from orionis.mail.functions import sanitize_reason

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path
    from orionis.mail.enums.status import MailStatus

@dataclass(frozen=True, slots=True, kw_only=True)
class MailResult:
    """
    Report SMTP acceptance or file storage, never final mailbox delivery.

    All recipient collections are copied. Rejection reasons are bounded,
    single-line text; transports must redact credentials before constructing
    the result. Stored messages have no SMTP acceptance or rejection entries.

    Parameters
    ----------
    message_id : str
        Message-ID of the transmitted or stored message.
    mailer : str
        Selected configuration name.
    driver : str
        Registered transport implementation name.
    status : MailStatus
        Confirmed outcome of the operation.
    recipients : tuple[str, ...]
        Intended transport recipients.
    accepted_recipients : tuple[str, ...]
        Recipients confirmed by an SMTP transaction.
    rejected_recipients : Mapping[str, tuple[int, str]]
        Rejected recipients mapped to their SMTP code and sanitized reason.
    file_path : Path | None
        Published file for stored messages, or None for SMTP.
    """

    message_id: str
    mailer: str
    driver: str
    status: MailStatus
    recipients: tuple[str, ...]
    accepted_recipients: tuple[str, ...] = ()
    rejected_recipients: Mapping[str, tuple[int, str]] = field(default_factory=dict)
    file_path: Path | None = None

    def __post_init__(self) -> None:
        """
        Detach recipient collections and sanitize SMTP rejection reasons.

        Returns
        -------
        None
            Store immutable snapshots owned by this result.
        """
        object.__setattr__(self, "recipients", tuple(self.recipients))
        object.__setattr__(self, "accepted_recipients", tuple(self.accepted_recipients))
        object.__setattr__(
            self,
            "rejected_recipients",
            MappingProxyType({
                address: (code, sanitize_reason(reason))
                for address, (code, reason) in self.rejected_recipients.items()
            }),
        )
