from __future__ import annotations
import inspect
from orionis.console.output.console import Console
from orionis.console.output.contracts.console import IConsole
from orionis.test import TestCase

class TestIConsoleContract(TestCase):
    """Test suite for the IConsole abstract interface contract."""

    # ------------------------------------------------------------------ #
    #  Abstract class characteristics                                    #
    # ------------------------------------------------------------------ #

    def testIsAbstractClass(self) -> None:
        """Verify that IConsole is an abstract class.

        Ensures that IConsole defines at least one abstract method and
        is therefore treated as abstract by the Python runtime.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(IConsole))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Ensure that IConsole cannot be instantiated directly.

        Verifies that attempting to create an instance of IConsole raises
        a TypeError due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            IConsole()  # type: ignore[abstract]

    # ------------------------------------------------------------------ #
    #  Abstract methods presence                                         #
    # ------------------------------------------------------------------ #

    def testAbstractMethodsAreDefined(self) -> None:
        """Verify that IConsole declares the expected set of abstract methods.

        Ensures every public capability advertised by the interface is
        present in __abstractmethods__ so consumers can rely on them.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        expected = {
            "success",
            "textSuccess",
            "textSuccessBold",
            "info",
            "textInfo",
            "textInfoBold",
            "warning",
            "textWarning",
            "textWarningBold",
            "fail",
            "error",
            "textError",
            "textErrorBold",
            "textMuted",
            "textMutedBold",
            "textUnderline",
            "clear",
            "clearLine",
            "line",
            "newLine",
            "write",
            "writeLine",
            "ask",
            "confirm",
            "secret",
            "table",
            "anticipate",
            "choice",
            "exception",
            "exitSuccess",
            "exitError",
            "dump",
        }
        missing = expected - IConsole.__abstractmethods__
        self.assertFalse(missing, f"Missing abstract methods: {missing}")

    def testProgressBarIsAbstractProperty(self) -> None:
        """Verify that progressBar is declared as an abstract property.

        Ensures the interface mandates an implementation of progressBar as
        a property, not a plain method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("progressBar", IConsole.__abstractmethods__)

    # ------------------------------------------------------------------ #
    #  Method signatures                                                 #
    # ------------------------------------------------------------------ #

    def testSuccessSignatureHasTimestampParam(self) -> None:
        """Verify that success() declares a timestamp parameter.

        Ensures the interface exposes optional timestamp control so
        implementors consistently support that feature.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IConsole.success)
        self.assertIn("timestamp", sig.parameters)

    def testInfoSignatureHasTimestampParam(self) -> None:
        """Verify that info() declares a timestamp parameter.

        Ensures the interface exposes optional timestamp control for the
        informational output method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IConsole.info)
        self.assertIn("timestamp", sig.parameters)

    def testConfirmSignatureHasDefaultParam(self) -> None:
        """Verify that confirm() declares a default parameter.

        Ensures the interface allows callers to specify a fallback answer
        when the user presses Enter without input.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IConsole.confirm)
        self.assertIn("default", sig.parameters)

    def testChoiceSignatureHasDefaultIndexParam(self) -> None:
        """Verify that choice() declares a default_index parameter.

        Ensures the interface supports a pre-selected default choice,
        which implementors must honour.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IConsole.choice)
        self.assertIn("default_index", sig.parameters)

    def testWriteSignatureHasSepEndFileFlush(self) -> None:
        """Verify that write() declares sep, end, file, and flush parameters.

        Ensures the interface mirrors the signature of the built-in print
        function so implementors can expose the same control surface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IConsole.write)
        for param in ("sep", "end", "file", "flush"):
            self.assertIn(param, sig.parameters)

    def testNewLineSignatureHasCountParam(self) -> None:
        """Verify that newLine() declares a count parameter.

        Ensures the interface lets callers specify the number of blank
        lines to emit in a single call.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IConsole.newLine)
        self.assertIn("count", sig.parameters)

    def testDumpSignatureHasForceExitParam(self) -> None:
        """Verify that dump() declares a force_exit parameter.

        Ensures the interface exposes process termination control so
        implementors can optionally abort execution after a dump.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IConsole.dump)
        self.assertIn("force_exit", sig.parameters)

    # ------------------------------------------------------------------ #
    #  Concrete class conformance                                        #
    # ------------------------------------------------------------------ #

    def testConsoleIsSubclassOfIConsole(self) -> None:
        """Verify that Console is a subclass of IConsole.

        Ensures the concrete implementation declares IConsole as its
        base class, satisfying the Liskov Substitution Principle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Console, IConsole))

    def testConsoleImplementsAllAbstractMethods(self) -> None:
        """Verify that Console implements every abstract method of IConsole.

        Ensures no abstract method from the interface remains unimplemented
        in the concrete class, including abstract properties, so that the
        class can be freely instantiated.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        console_members = {
            name
            for name, _ in inspect.getmembers(
                Console,
                predicate=lambda m: inspect.isfunction(m) or isinstance(m, property),
            )
        }
        for method_name in IConsole.__abstractmethods__:
            self.assertIn(method_name, console_members)

    def testConsoleCanBeInstantiated(self) -> None:
        """Verify that Console can be instantiated without errors.

        Ensures the concrete class fully satisfies the abstract interface
        contract so that object creation succeeds unconditionally.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        try:
            console = Console()
        except TypeError as exc:
            self.fail(f"Console() raised TypeError unexpectedly: {exc}")
        self.assertIsInstance(console, Console)

    def testConsoleIsInstanceOfIConsole(self) -> None:
        """Verify that a Console instance satisfies isinstance(obj, IConsole).

        Ensures polymorphic usage is valid: any code accepting an IConsole
        can transparently receive a Console instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        console = Console()
        self.assertIsInstance(console, IConsole)
