from __future__ import annotations
import inspect
from orionis.console.contracts.kernel import IKernelCLI
from orionis.console.kernel import KernelCLI
from orionis.test import TestCase

class TestIKernelCLIContract(TestCase):

    # ------------------------------------------------------------------ #
    #  Abstract structure                                                #
    # ------------------------------------------------------------------ #

    def testIKernelCLIIsAbstractClass(self) -> None:
        """Test that IKernelCLI is an abstract base class.

        Ensures the interface cannot be used directly but must be
        sub-classed with concrete implementations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(IKernelCLI))

    def testCannotInstantiateIKernelCLIDirectly(self) -> None:
        """Test that direct instantiation of IKernelCLI raises TypeError.

        Ensures that abstract methods prevent creating a bare interface
        object without a concrete implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            IKernelCLI()  # type: ignore[abstract]

    def testHasTwoAbstractMethods(self) -> None:
        """Test that IKernelCLI declares exactly two abstract methods.

        Ensures the interface surface is minimal: boot and handle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(IKernelCLI.__abstractmethods__), 2)

    # ------------------------------------------------------------------ #
    #  boot() abstract method                                            #
    # ------------------------------------------------------------------ #

    def testBootIsAbstract(self) -> None:
        """Test that 'boot' is listed as an abstract method.

        Ensures that any subclass must provide a concrete boot()
        implementation to be instantiable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("boot", IKernelCLI.__abstractmethods__)

    def testBootIsAsync(self) -> None:
        """Test that the 'boot' method on the interface is a coroutine function.

        Ensures that the abstract contract defines an async method so
        implementations know they must use async def.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(IKernelCLI.boot))

    def testBootHasApplicationParameter(self) -> None:
        """Test that 'boot' declares an 'application' parameter.

        Ensures the method signature matches the expected interface:
        boot(self, application).

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IKernelCLI.boot)
        self.assertIn("application", sig.parameters)

    def testBootApplicationParamHasNoDefault(self) -> None:
        """Test that the 'application' parameter of boot has no default value.

        Ensures callers are required to always supply the application
        instance explicitly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IKernelCLI.boot)
        param = sig.parameters["application"]
        self.assertIs(param.default, inspect.Parameter.empty)

    # ------------------------------------------------------------------ #
    #  handle() abstract method                                          #
    # ------------------------------------------------------------------ #

    def testHandleIsAbstract(self) -> None:
        """Test that 'handle' is listed as an abstract method.

        Ensures that any subclass must provide a concrete handle()
        implementation to be instantiable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("handle", IKernelCLI.__abstractmethods__)

    def testHandleIsAsync(self) -> None:
        """Test that the 'handle' method on the interface is a coroutine function.

        Ensures that the abstract contract defines an async method so
        implementations know they must use async def.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(IKernelCLI.handle))

    def testHandleHasArgsParameter(self) -> None:
        """Test that 'handle' declares an 'args' parameter.

        Ensures the method signature matches the expected interface:
        handle(self, args).

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IKernelCLI.handle)
        self.assertIn("args", sig.parameters)

    def testHandleArgsDefaultIsNone(self) -> None:
        """Test that the 'args' parameter of handle defaults to None.

        Ensures that callers may invoke handle() without arguments to
        trigger the default help listing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IKernelCLI.handle)
        param = sig.parameters["args"]
        self.assertIsNone(param.default)

    # ------------------------------------------------------------------ #
    #  KernelCLI conformance                                             #
    # ------------------------------------------------------------------ #

    def testKernelCLIImplementsIKernelCLI(self) -> None:
        """Test that KernelCLI is a subclass of IKernelCLI.

        Ensures the concrete implementation correctly inherits from and
        satisfies the abstract interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(KernelCLI, IKernelCLI))

    def testKernelCLIIsNotAbstract(self) -> None:
        """Test that KernelCLI is not abstract and can be instantiated.

        Ensures all abstract methods declared in IKernelCLI are
        implemented in KernelCLI.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(inspect.isabstract(KernelCLI))

    def testKernelCLIImplementsAllAbstractMethods(self) -> None:
        """Test that KernelCLI provides implementations for every abstract method.

        Iterates over IKernelCLI.__abstractmethods__ and verifies that
        each one is present on KernelCLI as a callable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for method_name in IKernelCLI.__abstractmethods__:
            method = getattr(KernelCLI, method_name, None)
            self.assertIsNotNone(
                method,
                msg=f"KernelCLI is missing implementation of '{method_name}'",
            )
            self.assertTrue(
                inspect.isfunction(method) or inspect.iscoroutinefunction(method),
                msg=f"'{method_name}' on KernelCLI is not callable",
            )
