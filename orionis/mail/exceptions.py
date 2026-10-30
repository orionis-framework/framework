from typing import Self

class MailException(Exception):
    """Represent a failure in the mail subsystem."""

    __slots__ = ()

class MailConfigurationException(MailException):
    """Report invalid mailer settings or driver registrations."""

    __slots__ = ()

class MailCompositionException(MailException):
    """Report invalid declarations, callbacks, views, or MIME content."""

    __slots__ = ()

class MailAttachmentException(MailCompositionException):
    """Report unsafe metadata or an unreadable storage attachment."""

    __slots__ = ()

class MailTransportException(MailException):
    """Report a failed transaction without implying non-delivery."""

    __slots__ = ()

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
        self.failed_index = failed_index
