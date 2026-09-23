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
