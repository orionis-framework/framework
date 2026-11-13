# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Validate the public IReflectionConcrete contract against its implementation."""

import inspect
from abc import ABC
from orionis.introspection.concretes.contracts.reflection import IReflectionConcrete
from orionis.introspection.concretes.reflection import ReflectionConcrete
from orionis.test import TestCase


class _Target:
    """Supply an ordinary user-defined reflection target."""


class _Partial(IReflectionConcrete):
    """Implement one operation while leaving the rest abstract."""

    def clearCache(self) -> None:
        """Implement one operation without completing the contract."""


class TestIReflectionConcrete(TestCase):
    """Protect required operations and their real runtime signatures."""

    def testContractCannotBeInstantiated(self) -> None:
        """Require implementations to supply all abstract operations."""
        self.assertTrue(issubclass(IReflectionConcrete, ABC))
        self.assertTrue(inspect.isabstract(IReflectionConcrete))
        with self.assertRaises(TypeError):
            IReflectionConcrete()
        with self.assertRaises(TypeError):
            _Partial()

    def testRequiredOperations(self) -> None:
        """Preserve the complete public abstract surface."""
        expected = {
            "getClass",
            "getClassName",
            "getModuleName",
            "getModuleWithClassName",
            "getDocstring",
            "getBaseClasses",
            "getSourceCode",
            "getFile",
            "getAnnotations",
            "hasAttribute",
            "getAttribute",
            "setAttribute",
            "removeAttribute",
            "getAttributes",
            "getPublicAttributes",
            "getProtectedAttributes",
            "getPrivateAttributes",
            "getDunderAttributes",
            "getMagicAttributes",
            "hasMethod",
            "setMethod",
            "removeMethod",
            "getMethodSignature",
            "getMethods",
            "getPublicMethods",
            "getPublicSyncMethods",
            "getPublicAsyncMethods",
            "getProtectedMethods",
            "getProtectedSyncMethods",
            "getProtectedAsyncMethods",
            "getPrivateMethods",
            "getPrivateSyncMethods",
            "getPrivateAsyncMethods",
            "getPublicClassMethods",
            "getPublicClassSyncMethods",
            "getPublicClassAsyncMethods",
            "getProtectedClassMethods",
            "getProtectedClassSyncMethods",
            "getProtectedClassAsyncMethods",
            "getPrivateClassMethods",
            "getPrivateClassSyncMethods",
            "getPrivateClassAsyncMethods",
            "getPublicStaticMethods",
            "getPublicStaticSyncMethods",
            "getPublicStaticAsyncMethods",
            "getProtectedStaticMethods",
            "getProtectedStaticSyncMethods",
            "getProtectedStaticAsyncMethods",
            "getPrivateStaticMethods",
            "getPrivateStaticSyncMethods",
            "getPrivateStaticAsyncMethods",
            "getDunderMethods",
            "getMagicMethods",
            "getProperties",
            "getPublicProperties",
            "getProtectedProperties",
            "getPrivateProperties",
            "getProperty",
            "getPropertySignature",
            "getPropertyDocstring",
            "getConstructorSignature",
            "constructorSignature",
            "methodSignature",
            "clearCache",
        }
        self.assertEqual(IReflectionConcrete.__abstractmethods__, expected)

    def testConcreteImplementationSatisfiesTheContract(self) -> None:
        """Instantiate the real implementation with its supported target."""
        self.assertFalse(inspect.isabstract(ReflectionConcrete))
        reflected = ReflectionConcrete(_Target)
        self.assertIsInstance(reflected, IReflectionConcrete)

    def testRuntimeSignaturesMatchTheContract(self) -> None:
        """Resolve every annotation and preserve arguments, defaults and returns."""
        for name in sorted(IReflectionConcrete.__abstractmethods__):
            with self.subTest(method=name):
                expected = inspect.signature(
                    getattr(IReflectionConcrete, name),
                    eval_str=True,
                )
                actual = inspect.signature(
                    getattr(ReflectionConcrete, name),
                    eval_str=True,
                )
                self.assertEqual(actual, expected)
