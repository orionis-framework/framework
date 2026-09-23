import inspect
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.transports.file import FileTransport
from orionis.mail.transports.smtp import SmtpTransport
from orionis.test import TestCase

class TestIMailTransportContract(TestCase):

    def testDeclaresOnlyTheSendOperation(self) -> None:
        """
        Declare a single asynchronous operation for prepared messages.

        Validates that transports never expose composition concerns.
        """
        self.assertEqual(IMailTransport.__abstractmethods__, frozenset({"send"}))
        self.assertTrue(inspect.iscoroutinefunction(IMailTransport.send))

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots so implementations stay dictionary free.

        Validates the memory contract shared by framework interfaces.
        """
        self.assertEqual(IMailTransport.__slots__, ())

    def testMailerAndDriverAreKeywordOnly(self) -> None:
        """
        Require the mailer and driver names as keyword arguments.

        Validates the call shape used by the manager.
        """
        parameters = inspect.signature(
            IMailTransport.send,
            annotation_format=inspect.Format.STRING,
        ).parameters
        self.assertEqual(list(parameters), ["self", "message", "mailer", "driver"])
        self.assertIs(
            parameters["message"].kind,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
        for name in ("mailer", "driver"):
            self.assertIs(parameters[name].kind, inspect.Parameter.KEYWORD_ONLY)

    def testBuiltInTransportsImplementTheContract(self) -> None:
        """
        Implement the contract in both production transports.

        Validates that each one can be resolved through a factory.
        """
        for transport in (FileTransport, SmtpTransport):
            self.assertTrue(issubclass(transport, IMailTransport))
            self.assertEqual(transport.__abstractmethods__, frozenset())
            self.assertEqual(
                list(
                    inspect.signature(
                        transport.send,
                        annotation_format=inspect.Format.STRING,
                    ).parameters,
                ),
                ["self", "message", "mailer", "driver"],
            )
