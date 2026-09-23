import inspect
import typing
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.manager import MailManager
from orionis.test import TestCase

# Public operations every mail manager implementation must provide.
_EXPECTED_SURFACE = frozenset({
    "attach",
    "bcc",
    "cc",
    "extend",
    "fromAddress",
    "html",
    "mailer",
    "raw",
    "replyTo",
    "send",
    "subject",
    "to",
})

class TestIMailManagerContract(TestCase):

    def testDeclaresTheDocumentedPublicSurface(self) -> None:
        """
        Declare exactly the documented composition and delivery operations.

        Validates that no infrastructure method leaks into the contract.
        """
        self.assertEqual(IMailManager.__abstractmethods__, _EXPECTED_SURFACE)

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots so implementations stay dictionary free.

        Validates the memory contract shared by framework interfaces.
        """
        self.assertEqual(IMailManager.__slots__, ())

    def testTerminalOperationsAreCoroutines(self) -> None:
        """
        Declare only the terminal operations as coroutine methods.

        Validates that composition never requires an intermediate await.
        """
        for name in ("send", "raw", "html"):
            self.assertTrue(
                inspect.iscoroutinefunction(getattr(IMailManager, name)),
                msg=name,
            )
        for name in ("mailer", "fromAddress", "to", "subject", "attach", "extend"):
            self.assertFalse(
                inspect.iscoroutinefunction(getattr(IMailManager, name)),
                msg=name,
            )

    def testImplementationMatchesEveryDeclaredSignature(self) -> None:
        """
        Keep the parameters of the manager aligned with the contract.

        Validates names, order, and default values of each operation.
        """
        for name in sorted(_EXPECTED_SURFACE):
            declared = inspect.signature(
                getattr(IMailManager, name),
                annotation_format=inspect.Format.STRING,
            )
            implemented = inspect.signature(
                getattr(MailManager, name),
                annotation_format=inspect.Format.STRING,
            )
            self.assertEqual(
                list(declared.parameters),
                list(implemented.parameters),
                msg=name,
            )
            self.assertEqual(
                [parameter.default for parameter in declared.parameters.values()],
                [parameter.default for parameter in implemented.parameters.values()],
                msg=name,
            )

    def testSendDeclaresThreeOverloads(self) -> None:
        """
        Expose the Mailable, view, and Content overloads of send.

        Validates the typed surface consumers rely on.
        """
        overloads = typing.get_overloads(IMailManager.send)
        self.assertEqual(len(overloads), 3)
        self.assertEqual(
            [list(inspect.signature(item).parameters)[1] for item in overloads],
            ["mailable", "view", "content"],
        )

    def testManagerImplementsTheContract(self) -> None:
        """
        Register the concrete manager as an implementation of the contract.

        Validates that dependency injection can resolve it by contract.
        """
        self.assertTrue(issubclass(MailManager, IMailManager))
        self.assertEqual(MailManager.__abstractmethods__, frozenset())
