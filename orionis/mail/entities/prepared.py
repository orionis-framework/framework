from dataclasses import dataclass

@dataclass(frozen=True, slots=True, kw_only=True)
class PreparedMail:
    """
    Carry immutable MIME bytes and a separate validated transport envelope.

    Transports consume this value without seeing templates, Mailable classes,
    storage paths, or a mutable ``EmailMessage``.

    Parameters
    ----------
    message_id : str
        Message-ID generated once for the operation.
    sender : str
        Envelope sender used by the transport.
    recipients : tuple[str, ...]
        Deduplicated union of To, Cc, and Bcc addresses.
    mime : bytes
        Serialized message without any Bcc header.
    smtp_utf8 : bool
        Whether an envelope mailbox or a visible addr-spec needs SMTPUTF8.
    """

    message_id: str
    sender: str
    recipients: tuple[str, ...]
    mime: bytes
    smtp_utf8: bool
