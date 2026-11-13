# ruff: noqa: TC001, TC003
# Keep extension hook annotations available for runtime inspection.
"""Declare reusable mail without I/O or per-send mutation."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.envelope import Envelope


class Mailable(ABC):
    """
    Declare reusable mail without I/O or per-send mutation.

    Subclasses describe headers, bodies, and attachments synchronously.
    Pass an instance to ``Mail.send()`` when it is already constructed, or pass
    its class to let the application container inject constructor dependencies.
    Rendering, attachment reads, and transport happen afterwards, so the same
    instance can be sent concurrently without being modified.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def envelope(self) -> Envelope:
        """
        Declare headers and recipients synchronously.

        Returns
        -------
        orionis.mail.entities.Envelope
            Immutable envelope, augmented by explicit PendingMail data.
        """

    @abstractmethod
    def content(self) -> Content:
        """
        Declare literal bodies or views synchronously.

        Returns
        -------
        orionis.mail.entities.Content
            Content whose rendering is deferred until sending.
        """

    def attachments(self) -> Sequence[Attachment]:
        """
        Declare deferred storage attachments synchronously.

        Returns
        -------
        collections.abc.Sequence[orionis.mail.entities.Attachment]
            Empty by default; subclasses may return their own declarations.
        """
        return ()
