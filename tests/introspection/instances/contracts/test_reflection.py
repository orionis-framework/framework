# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Validate the public IReflectionInstance contract against its implementation."""

import inspect
from abc import ABC
from orionis.introspection.instances.contracts.reflection import IReflectionInstance
from orionis.introspection.instances.reflection import ReflectionInstance
from orionis.test import TestCase


class _Target:
    """Supply an ordinary user-defined reflection target."""


class _Partial(IReflectionInstance):
    """Implement one operation while leaving the rest abstract."""

    def clearCache(self) -> None:
        """Implement one operation without completing the contract."""


class TestIReflectionInstance(TestCase):
    """Protect required operations and their real runtime signatures."""

    def testContractCannotBeInstantiated(self) -> None:
        """Require implementations to supply all abstract operations."""
        self.assertTrue(issubclass(IReflectionInstance, ABC))
        self.assertTrue(inspect.isabstract(IReflectionInstance))
        with self.assertRaises(TypeError):
            IReflectionInstance()
        with self.assertRaises(TypeError):
            _Partial()

    def testRequiredOperations(self) -> None:
        """Preserve the complete public abstract surface."""
        expected = {
            "getInstance",
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
            "getMethodDocstring",
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
            "constructorSignature",
            "methodSignature",
            "clearCache",
        }
        self.assertEqual(IReflectionInstance.__abstractmethods__, expected)

    def testConcreteImplementationSatisfiesTheContract(self) -> None:
        """Instantiate the real implementation with its supported target."""
        self.assertFalse(inspect.isabstract(ReflectionInstance))
        reflected = ReflectionInstance(_Target())
        self.assertIsInstance(reflected, IReflectionInstance)

    def testRuntimeSignaturesMatchTheContract(self) -> None:
        """Resolve every annotation and preserve arguments, defaults and returns."""
        for name in sorted(IReflectionInstance.__abstractmethods__):
            with self.subTest(method=name):
                expected = inspect.signature(
                    getattr(IReflectionInstance, name),
                    eval_str=True,
                )
                actual = inspect.signature(
                    getattr(ReflectionInstance, name),
                    eval_str=True,
                )
                self.assertEqual(actual, expected)
