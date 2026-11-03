"""Group the mail contracts components and public imports."""

from orionis.mail.contracts.manager import IMailManager
from orionis.mail.contracts.transport import IMailTransport

__all__ = [
    "IMailManager",
    "IMailTransport",
]
