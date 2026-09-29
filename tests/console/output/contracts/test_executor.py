from __future__ import annotations
import inspect
from orionis.console.output.contracts.executor import IExecutor
from orionis.console.output.executor import Executor
from orionis.test import TestCase

class TestIExecutorContract(TestCase):

    # ------------------------------------------------------------------ #
    #  Abstract class characteristics                                    #
    # ------------------------------------------------------------------ #

    def testIsAbstractClass(self) -> None:
        """Verify that IExecutor is an abstract class.

        Ensures that IExecutor has at least one abstract method and
        therefore cannot be instantiated directly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(IExecutor))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Ensure that IExecutor cannot be instantiated directly.

        Verifies that attempting to create an instance raises TypeError
        due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            IExecutor()  # type: ignore[abstract]

    # ------------------------------------------------------------------ #
    #  Abstract methods presence                                         #
    # ------------------------------------------------------------------ #

    def testAbstractMethodsAreDefined(self) -> None:
        """Verify that IExecutor declares exactly the expected abstract methods.

        Ensures the interface exposes running, done, and fail so that any
        consumer can rely on those capabilities being present in every
        concrete implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        expected = {"running", "done", "fail"}
        missing = expected - IExecutor.__abstractmethods__
        self.assertFalse(missing, f"Missing abstract methods: {missing}")

    def testHasExactlyThreeAbstractMethods(self) -> None:
        """Verify that IExecutor declares exactly three abstract methods.

        Ensures the interface surface area is stable and no undocumented
        abstract methods have been added or removed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(IExecutor.__abstractmethods__), 3)

    # ------------------------------------------------------------------ #
    #  Method signatures                                                 #
    # ------------------------------------------------------------------ #

    def testRunningSignatureHasProgramParam(self) -> None:
        """Verify that running() declares a program parameter.

        Ensures the interface mandates that implementors accept the
        name of the running process as a required positional argument.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.running)
        self.assertIn("program", sig.parameters)

    def testRunningSignatureHasTimeParam(self) -> None:
        """Verify that running() declares an optional time parameter.

        Ensures the interface allows callers to supply an execution
        duration string alongside the program name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.running)
        self.assertIn("time", sig.parameters)

    def testRunningTimeParamHasDefaultEmptyString(self) -> None:
        """Verify that the time parameter of running() defaults to empty string.

        Ensures callers are not forced to supply a time value when the
        duration is not yet known.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.running)
        self.assertEqual(sig.parameters["time"].default, "")

    def testDoneSignatureHasProgramParam(self) -> None:
        """Verify that done() declares a program parameter.

        Ensures the interface mandates that implementors accept the
        name of the completed process as a required positional argument.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.done)
        self.assertIn("program", sig.parameters)

    def testDoneSignatureHasTimeParam(self) -> None:
        """Verify that done() declares an optional time parameter.

        Ensures the interface allows callers to report the total execution
        duration alongside the completion event.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.done)
        self.assertIn("time", sig.parameters)

    def testDoneTimeParamHasDefaultEmptyString(self) -> None:
        """Verify that the time parameter of done() defaults to empty string.

        Ensures callers can report completion without providing a duration
        when the timing information is unavailable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.done)
        self.assertEqual(sig.parameters["time"].default, "")

    def testFailSignatureHasProgramParam(self) -> None:
        """Verify that fail() declares a program parameter.

        Ensures the interface mandates that implementors accept the
        name of the failed process as a required positional argument.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.fail)
        self.assertIn("program", sig.parameters)

    def testFailSignatureHasTimeParam(self) -> None:
        """Verify that fail() declares an optional time parameter.

        Ensures the interface allows callers to report the elapsed
        duration before failure alongside the program name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.fail)
        self.assertIn("time", sig.parameters)

    def testFailTimeParamHasDefaultEmptyString(self) -> None:
        """Verify that the time parameter of fail() defaults to empty string.

        Ensures callers can report a failure without providing a duration
        when timing information is not available.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IExecutor.fail)
        self.assertEqual(sig.parameters["time"].default, "")

    # ------------------------------------------------------------------ #
    #  Concrete class conformance                                        #
    # ------------------------------------------------------------------ #

    def testExecutorIsSubclassOfIExecutor(self) -> None:
        """Verify that Executor is a subclass of IExecutor.

        Ensures the concrete implementation declares IExecutor as its
        base class, satisfying the Liskov Substitution Principle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Executor, IExecutor))

    def testExecutorImplementsAllAbstractMethods(self) -> None:
        """Verify that Executor implements every abstract method of IExecutor.

        Ensures no abstract method from the interface remains unimplemented
        in the concrete class so it can be freely instantiated.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor_methods = {
            name
            for name, _ in inspect.getmembers(Executor, predicate=inspect.isfunction)
        }
        for method_name in IExecutor.__abstractmethods__:
            self.assertIn(method_name, executor_methods)

    def testExecutorCanBeInstantiated(self) -> None:
        """Verify that Executor can be instantiated without errors.

        Ensures the concrete class fully satisfies the abstract interface
        contract so object creation succeeds unconditionally.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        try:
            executor = Executor()
        except TypeError as exc:
            self.fail(f"Executor() raised TypeError unexpectedly: {exc}")
        self.assertIsInstance(executor, Executor)

    def testExecutorIsInstanceOfIExecutor(self) -> None:
        """Verify that an Executor instance satisfies isinstance(obj, IExecutor).

        Ensures polymorphic usage is valid: code accepting an IExecutor
        can transparently receive an Executor instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        executor = Executor()
        self.assertIsInstance(executor, IExecutor)
