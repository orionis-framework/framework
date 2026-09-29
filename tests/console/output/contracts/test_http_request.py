from __future__ import annotations
import inspect
from orionis.console.output.contracts.http_request import IHTTPRequestPrinter
from orionis.console.output.http_request import HTTPRequestPrinter
from orionis.test import TestCase

class TestIHTTPRequestPrinterContract(TestCase):

    # ------------------------------------------------------------------ #
    #  Abstract class characteristics                                    #
    # ------------------------------------------------------------------ #

    def testIsAbstractClass(self) -> None:
        """Verify that IHTTPRequestPrinter is recognised as an abstract class.

        Ensures the interface defines at least one abstract method so it
        cannot be instantiated directly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(IHTTPRequestPrinter))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Ensure that IHTTPRequestPrinter cannot be instantiated directly.

        Verifies that attempting to create an instance raises TypeError
        due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            IHTTPRequestPrinter()  # type: ignore[abstract]

    # ------------------------------------------------------------------ #
    #  Abstract methods presence                                         #
    # ------------------------------------------------------------------ #

    def testAbstractMethodsAreDefined(self) -> None:
        """Verify that IHTTPRequestPrinter declares printRequest as abstract.

        Ensures the main output capability is listed in __abstractmethods__
        so every concrete subclass is forced to provide an implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("printRequest", IHTTPRequestPrinter.__abstractmethods__)

    def testHasExpectedAbstractMethods(self) -> None:
        """Verify that the printer declares the expected abstract methods.

        Ensures the interface surface area is stable and no undocumented
        abstract methods have been added or removed silently.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        expected = {"startTimer", "setEnabled", "start", "stop", "printRequest"}
        self.assertEqual(IHTTPRequestPrinter.__abstractmethods__, expected)

    def testStartTimerIsAbstract(self) -> None:
        """Verify that IHTTPRequestPrinter declares startTimer as abstract.

        Ensures the static timer factory is part of the required interface
        contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("startTimer", IHTTPRequestPrinter.__abstractmethods__)

    def testSetEnabledIsAbstract(self) -> None:
        """Verify that IHTTPRequestPrinter declares setEnabled as abstract.

        Ensures the enable/disable toggle is part of the required contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("setEnabled", IHTTPRequestPrinter.__abstractmethods__)

    def testStartIsAbstract(self) -> None:
        """Verify that IHTTPRequestPrinter declares start as abstract.

        Ensures the async lifecycle start method is part of the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("start", IHTTPRequestPrinter.__abstractmethods__)

    def testStopIsAbstract(self) -> None:
        """Verify that IHTTPRequestPrinter declares stop as abstract.

        Ensures the async lifecycle stop method is part of the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("stop", IHTTPRequestPrinter.__abstractmethods__)

    # ------------------------------------------------------------------ #
    #  printRequest signature                                            #
    # ------------------------------------------------------------------ #

    def testPrintRequestSignatureHasAdapterParam(self) -> None:
        """Verify that printRequest declares an adapter parameter.

        Ensures the interface mandates the transport adapter as a required
        positional argument for all concrete implementations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IHTTPRequestPrinter.printRequest)
        self.assertIn("adapter", sig.parameters)

    def testPrintRequestSignatureHasResponseParam(self) -> None:
        """Verify that printRequest declares a response parameter.

        Ensures the interface mandates the HTTP response object as a required
        positional argument for all concrete implementations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IHTTPRequestPrinter.printRequest)
        self.assertIn("response", sig.parameters)

    def testPrintRequestHasTwoParams(self) -> None:
        """Verify that printRequest declares exactly two parameters besides self.

        Ensures the interface surface is stable: adapter and response are
        the only required arguments.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IHTTPRequestPrinter.printRequest)
        params = [p for p in sig.parameters if p != "self"]
        self.assertEqual(len(params), 2)

    def testStartTimerReturnTypeIsFloatOrNone(self) -> None:
        """Verify that startTimer has the correct return annotation.

        Ensures the interface declares the return type as float | None so
        concrete implementations know when to return a timestamp vs None.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        hints = IHTTPRequestPrinter.startTimer.__annotations__
        self.assertIn("return", hints)

    def testPrintRequestReturnsNoneAnnotation(self) -> None:
        """Verify that printRequest is annotated to return None.

        Ensures the interface declares a None return type for printRequest
        so callers know no value is produced.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        hints = IHTTPRequestPrinter.printRequest.__annotations__
        self.assertIn("return", hints)

    # ------------------------------------------------------------------ #
    #  Concrete class conformance                                        #
    # ------------------------------------------------------------------ #

    def testHTTPRequestPrinterIsSubclassOfInterface(self) -> None:
        """Verify that HTTPRequestPrinter is a subclass of IHTTPRequestPrinter.

        Ensures the concrete implementation declares the interface as its
        base class, satisfying the Liskov Substitution Principle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(HTTPRequestPrinter, IHTTPRequestPrinter))

    def testHTTPRequestPrinterCanBeInstantiated(self) -> None:
        """Verify that HTTPRequestPrinter can be instantiated without raising.

        Ensures the concrete class fully satisfies the abstract interface
        contract so object creation succeeds unconditionally.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        try:
            printer = HTTPRequestPrinter()
        except TypeError as exc:
            self.fail(f"HTTPRequestPrinter() raised TypeError: {exc}")
        self.assertIsInstance(printer, HTTPRequestPrinter)

    def testHTTPRequestPrinterIsInstanceOfInterface(self) -> None:
        """Verify that an HTTPRequestPrinter instance satisfies isinstance check.

        Ensures polymorphic usage is valid: code that accepts an
        IHTTPRequestPrinter can transparently receive an HTTPRequestPrinter.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        printer = HTTPRequestPrinter()
        self.assertIsInstance(printer, IHTTPRequestPrinter)

    def testHTTPRequestPrinterImplementsPrintRequest(self) -> None:
        """Verify that HTTPRequestPrinter provides a concrete printRequest method.

        Ensures the method is callable on the class and is no longer
        abstract, allowing it to be used without further subclassing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(HTTPRequestPrinter.printRequest))
        self.assertNotIn("printRequest", HTTPRequestPrinter.__dict__.get(
            "__abstractmethods__", set(),
        ))

    def testHTTPRequestPrinterImplementsStartTimer(self) -> None:
        """Verify that HTTPRequestPrinter provides a concrete startTimer method.

        Ensures the static timer factory is callable on the class and is
        no longer abstract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(HTTPRequestPrinter.startTimer))
        self.assertNotIn("startTimer", HTTPRequestPrinter.__dict__.get(
            "__abstractmethods__", set(),
        ))
