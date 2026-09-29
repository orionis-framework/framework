from __future__ import annotations
import inspect
from orionis.console.output.contracts.help_command import IHelpCommand
from orionis.console.output.help_command import HelpCommand
from orionis.test import TestCase

class TestIHelpCommandContract(TestCase):

    # ------------------------------------------------------------------ #
    #  Abstract class characteristics                                    #
    # ------------------------------------------------------------------ #

    def testIsAbstractClass(self) -> None:
        """Verify that IHelpCommand is recognised as an abstract class.

        Ensures that IHelpCommand defines abstract members and therefore
        cannot be instantiated without a concrete implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(IHelpCommand))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Ensure that IHelpCommand cannot be instantiated directly.

        Verifies that attempting to create an instance raises TypeError
        due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            IHelpCommand()  # type: ignore[abstract]

    # ------------------------------------------------------------------ #
    #  Abstract methods presence                                         #
    # ------------------------------------------------------------------ #

    def testAbstractMethodsAreDefined(self) -> None:
        """Verify that IHelpCommand declares parseActions and printActions.

        Ensures both capabilities are listed in __abstractmethods__ so
        every concrete subclass is forced to provide implementations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        expected = {"parseActions", "printActions"}
        missing = expected - IHelpCommand.__abstractmethods__
        self.assertFalse(missing, f"Missing abstract methods: {missing}")

    def testHasExactlyTwoAbstractMethods(self) -> None:
        """Verify that IHelpCommand declares exactly two abstract methods.

        Ensures the interface surface area is stable and that no extra
        or missing abstract methods have been introduced silently.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(IHelpCommand.__abstractmethods__), 2)

    # ------------------------------------------------------------------ #
    #  Method signatures                                                 #
    # ------------------------------------------------------------------ #

    def testParseActionsSignatureHasActionsParam(self) -> None:
        """Verify that parseActions declares an actions parameter.

        Ensures the interface mandates that implementors accept a list
        of argparse actions as the primary input.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IHelpCommand.parseActions)
        self.assertIn("actions", sig.parameters)

    def testPrintActionsSignatureHasCommandNameParam(self) -> None:
        """Verify that printActions declares a command_name parameter.

        Ensures the interface requires the name of the command to be
        passed so implementors can display it in the rendered output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IHelpCommand.printActions)
        self.assertIn("command_name", sig.parameters)

    def testPrintActionsSignatureHasActionsParam(self) -> None:
        """Verify that printActions declares an actions parameter.

        Ensures the interface requires a list of argparse actions so
        implementors can render the full help output from them.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IHelpCommand.printActions)
        self.assertIn("actions", sig.parameters)

    def testPrintActionsSignatureHasIsErrorParam(self) -> None:
        """Verify that printActions declares an is_error parameter.

        Ensures the interface supports toggling between the normal help
        output and the error output path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IHelpCommand.printActions)
        self.assertIn("is_error", sig.parameters)

    def testPrintActionsIsErrorDefaultIsFalse(self) -> None:
        """Verify that is_error defaults to False in printActions.

        Ensures callers that only want normal help output are not forced
        to pass is_error explicitly on every invocation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IHelpCommand.printActions)
        self.assertEqual(sig.parameters["is_error"].default, False)

    # ------------------------------------------------------------------ #
    #  Static method characteristics                                     #
    # ------------------------------------------------------------------ #

    def testParseActionsIsStaticOnInterface(self) -> None:
        """Verify that parseActions is a static method on IHelpCommand.

        Ensures the interface declares parseActions as a static member
        so implementors are required to mirror that binding style.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        raw = IHelpCommand.__dict__["parseActions"]
        # After @staticmethod @abstractmethod wrapping the descriptor
        # is a staticmethod around the abstract function
        self.assertIsInstance(raw, staticmethod)

    def testPrintActionsIsStaticOnInterface(self) -> None:
        """Verify that printActions is a static method on IHelpCommand.

        Ensures the interface declares printActions as a static member
        so implementors are required to mirror that binding style.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        raw = IHelpCommand.__dict__["printActions"]
        self.assertIsInstance(raw, staticmethod)

    # ------------------------------------------------------------------ #
    #  Concrete class conformance                                        #
    # ------------------------------------------------------------------ #

    def testHelpCommandIsSubclassOfIHelpCommand(self) -> None:
        """Verify that HelpCommand is a subclass of IHelpCommand.

        Ensures the concrete implementation declares IHelpCommand as its
        base class, satisfying the Liskov Substitution Principle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(HelpCommand, IHelpCommand))

    def testHelpCommandCanBeInstantiated(self) -> None:
        """Verify that HelpCommand can be instantiated without raising.

        Ensures the concrete class fully satisfies the abstract interface
        contract so object creation succeeds unconditionally.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        try:
            obj = HelpCommand()
        except TypeError as exc:
            self.fail(f"HelpCommand() raised TypeError unexpectedly: {exc}")
        self.assertIsInstance(obj, HelpCommand)

    def testHelpCommandIsInstanceOfIHelpCommand(self) -> None:
        """Verify that a HelpCommand instance satisfies isinstance(obj, IHelpCommand).

        Ensures polymorphic usage is valid: code accepting an IHelpCommand
        can transparently receive a HelpCommand instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        obj = HelpCommand()
        self.assertIsInstance(obj, IHelpCommand)

    def testHelpCommandImplementsParseActions(self) -> None:
        """Verify that HelpCommand provides a concrete parseActions implementation.

        Ensures the method is callable on the class and is not still abstract,
        allowing it to be used without subclassing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(HelpCommand.parseActions))

    def testHelpCommandImplementsPrintActions(self) -> None:
        """Verify that HelpCommand provides a concrete printActions implementation.

        Ensures the method is callable on the class and is not still abstract,
        allowing it to be used without subclassing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(HelpCommand.printActions))

    def testHelpCommandParseActionsIsStatic(self) -> None:
        """Verify that HelpCommand.parseActions is declared as a static method.

        Ensures the concrete implementation mirrors the interface's binding
        style, which is required for transparent substitution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        raw = HelpCommand.__dict__["parseActions"]
        self.assertIsInstance(raw, staticmethod)

    def testHelpCommandPrintActionsIsStatic(self) -> None:
        """Verify that HelpCommand.printActions is declared as a static method.

        Ensures the concrete implementation mirrors the interface's binding
        style, which is required for transparent substitution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        raw = HelpCommand.__dict__["printActions"]
        self.assertIsInstance(raw, staticmethod)
