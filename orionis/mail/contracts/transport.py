"""Send already prepared mail without knowing views or storage declarations."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.mail.entities.prepared import PreparedMail
    from orionis.mail.entities.result import MailResult

class IMailTransport(ABC):
    """
    Send already prepared mail without knowing views or storage declarations.

    Implementations receive immutable MIME bytes plus a separate transport
    envelope, so they never resolve templates, disks, or Mailable classes.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    async def send(
        self,
        message: PreparedMail,
        *,
        mailer: str,
        driver: str,
    ) -> MailResult:
        """
        Transmit or store one complete message.

        Parameters
        ----------
        message : orionis.mail.entities.PreparedMail
            Immutable MIME bytes plus a separate transport envelope.
        mailer : str
            Selected configuration name.
        driver : str
            Registered transport implementation name.

        Returns
        -------
        orionis.mail.entities.MailResult
            Confirmed acceptance, partial acceptance, or storage result.

        Raises
        ------
        orionis.mail.exceptions.MailTransportException
            If the operation fails or all recipients are rejected.
        """
