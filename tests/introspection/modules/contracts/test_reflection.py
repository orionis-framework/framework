# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Validate the public IReflectionModule contract against its implementation."""

import inspect
from abc import ABC
from orionis.introspection.modules.contracts.reflection import IReflectionModule
from orionis.introspection.modules.reflection import ReflectionModule
from orionis.test import TestCase


class _Partial(IReflectionModule):
    """Implement one operation while leaving the rest abstract."""

    def clearCache(self) -> None:
        """Implement one operation without completing the contract."""


class TestIReflectionModule(TestCase):
    """Protect required operations and their real runtime signatures."""

    def testContractCannotBeInstantiated(self) -> None:
        """Require implementations to supply all abstract operations."""
        self.assertTrue(issubclass(IReflectionModule, ABC))
        self.assertTrue(inspect.isabstract(IReflectionModule))
        with self.assertRaises(TypeError):
            IReflectionModule()
        with self.assertRaises(TypeError):
            _Partial()

    def testRequiredOperations(self) -> None:
        """Preserve the complete public abstract surface."""
        expected = {
            "getModule",
            "hasClass",
            "getClass",
            "setClass",
            "removeClass",
            "getClasses",
            "getPublicClasses",
            "getProtectedClasses",
            "getPrivateClasses",
            "getConstant",
            "getConstants",
            "getPublicConstants",
            "getProtectedConstants",
            "getPrivateConstants",
            "getFunctions",
            "getPublicFunctions",
            "getPublicSyncFunctions",
            "getPublicAsyncFunctions",
            "getProtectedFunctions",
            "getProtectedSyncFunctions",
            "getProtectedAsyncFunctions",
            "getPrivateFunctions",
            "getPrivateSyncFunctions",
            "getPrivateAsyncFunctions",
            "getImports",
            "getFile",
            "getSourceCode",
            "clearCache",
        }
        self.assertEqual(IReflectionModule.__abstractmethods__, expected)

    def testConcreteImplementationSatisfiesTheContract(self) -> None:
        """Instantiate the real implementation with its supported target."""
        self.assertFalse(inspect.isabstract(ReflectionModule))
        reflected = ReflectionModule(__name__)
        self.assertIsInstance(reflected, IReflectionModule)

    def testRuntimeSignaturesMatchTheContract(self) -> None:
        """Resolve every annotation and preserve arguments, defaults and returns."""
        for name in sorted(IReflectionModule.__abstractmethods__):
            with self.subTest(method=name):
                expected = inspect.signature(
                    getattr(IReflectionModule, name),
                    eval_str=True,
                )
                actual = inspect.signature(
                    getattr(ReflectionModule, name),
                    eval_str=True,
                )
                self.assertEqual(actual, expected)
