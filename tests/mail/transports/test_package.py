import orionis.mail.transports as transports_package
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.transports.file import FileTransport, create_file_transport
from orionis.mail.transports.smtp import SmtpTransport, create_smtp_transport
from orionis.test import TestCase

class TestTransportsPackage(TestCase):

    def testExportsEveryBuiltInTransportAndFactory(self) -> None:
        """
        Publish each built-in transport next to its factory.

        Validates the shortcut import used by the manager.
        """
        self.assertEqual(
            sorted(transports_package.__all__),
            [
                "FileTransport",
                "SmtpTransport",
                "create_file_transport",
                "create_smtp_transport",
            ],
        )
        for name in transports_package.__all__:
            self.assertIs(
                getattr(transports_package, name),
                {
                    "FileTransport": FileTransport,
                    "SmtpTransport": SmtpTransport,
                    "create_file_transport": create_file_transport,
                    "create_smtp_transport": create_smtp_transport,
                }[name],
            )

    def testEveryTransportImplementsTheSharedContract(self) -> None:
        """
        Keep both transports behind the single delivery contract.

        Validates that the manager can use them interchangeably.
        """
        for transport in (FileTransport, SmtpTransport):
            self.assertTrue(issubclass(transport, IMailTransport))
            self.assertNotIn("__dict__", dir(transport))
