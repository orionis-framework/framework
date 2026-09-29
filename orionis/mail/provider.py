from orionis.container.providers.service_provider import ServiceProvider
from orionis.mail.composer import MailComposer
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.manager import MailManager
from orionis.support.facades.mail import Mail

class MailProvider(ServiceProvider):
    """
    Register mail eagerly so synchronous fluent facade entries work immediately.

    The provider never opens a connection or validates transport options: a
    mailer is resolved when an operation is actually sent.
    """

    __slots__ = ()

    def register(self) -> None:
        """
        Bind the shared composer and manager without resolving transports.

        Returns
        -------
        None
            Register services used by both the CLI and HTTP runtimes.
        """
        self.app.singleton(MailComposer, MailComposer)
        self.app.singleton(IMailManager, MailManager)

    async def boot(self) -> None:
        """
        Pin the facade without validating SMTP or opening a connection.

        Returns
        -------
        None
            Make the fluent facade methods synchronous passthroughs.
        """
        await Mail.pin()
