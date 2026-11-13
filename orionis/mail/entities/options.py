# ruff: noqa: TC001
# Keep dataclass fields and generated constructor annotations resolvable.
"""Snapshot the explicitly supplied options of one independent chain."""

from dataclasses import dataclass
from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.envelope import Envelope


@dataclass(frozen=True, slots=True)
class MailOptions:
    """
    Snapshot the explicitly supplied options of one independent chain.

    Attributes
    ----------
    mailer : str | None
        Selected configuration name, or None for the central default.
    from_address : orionis.mail.entities.Address | None
        Explicit sender replacing any declared one.
    subject : str | None
        Explicit subject replacing any declared one.
    to : tuple[orionis.mail.entities.Address, ``...``]
        Visible recipients appended to a declaration.
    cc : tuple[orionis.mail.entities.Address, ``...``]
        Carbon-copy recipients appended to a declaration.
    bcc : tuple[orionis.mail.entities.Address, ``...``]
        Hidden recipients appended to a declaration.
    reply_to : tuple[orionis.mail.entities.Address, ``...``]
        Reply destinations appended to a declaration.
    attachments : tuple[orionis.mail.entities.Attachment, ``...``]
        Deferred attachments appended to a declaration.
    """

    mailer: str | None = None
    from_address: Address | None = None
    subject: str | None = None
    to: tuple[Address, ...] = ()
    cc: tuple[Address, ...] = ()
    bcc: tuple[Address, ...] = ()
    reply_to: tuple[Address, ...] = ()
    attachments: tuple[Attachment, ...] = ()

    def envelope(self, base: Envelope | None = None) -> Envelope:
        """
        Overlay explicit scalars and append recipients to a declaration.

        Parameters
        ----------
        base : orionis.mail.entities.Envelope | None
            Optional reusable Mailable envelope.

        Returns
        -------
        orionis.mail.entities.Envelope
            Validated envelope owned by the operation.

        Raises
        ------
        orionis.mail.exceptions.MailCompositionException
            If the merged recipients violate Bcc privacy.
        """
        source = base if base is not None else Envelope()
        return Envelope(
            subject=source.subject if self.subject is None else self.subject,
            from_address=self.from_address or source.from_address,
            to=(*source.to, *self.to),
            cc=(*source.cc, *self.cc),
            bcc=(*source.bcc, *self.bcc),
            reply_to=(*source.reply_to, *self.reply_to),
        )
