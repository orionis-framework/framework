"""Provide mail operations.

Includes ``MailException``, ``MailConfigurationException``,
``MailCompositionException``, ``MailAttachmentException``.
"""

from typing import Self


class MailException(Exception):
    """Represent a failure in the mail subsystem."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class MailConfigurationException(MailException):
    """Report invalid mailer settings or driver registrations."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class MailCompositionException(MailException):
    """Report invalid declarations, callbacks, views, or MIME content."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class MailAttachmentException(MailCompositionException):
    """Report unsafe metadata or an unreadable storage attachment."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class MailTransportException(MailException):
    """Report a failed transaction without implying non-delivery."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""


class MailBatchException(MailTransportException):
    """Expose accepted batch results and the first uncertain transaction index."""

    def __init__(self: Self, message: str, completed: tuple, failed_index: int) -> None:
        """
        Retain partial outcomes without retrying ambiguous SMTP deliveries.

        Parameters
        ----------
        message : str
            Description of the delivery failure.
        completed : tuple
            Successful results recorded before the batch failed.
        failed_index : int
            Zero-based index of the first unsuccessful delivery.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        super().__init__(message)
        self.completed = completed
        """Successful results recorded before the batch failed."""
        self.failed_index = failed_index
        """Zero-based index of the first unsuccessful delivery."""
