# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Validate the public IReflectionAbstract contract against its implementation."""

import inspect
from abc import ABC, abstractmethod
from orionis.introspection.abstract.contracts.reflection import IReflectionAbstract
from orionis.introspection.abstract.reflection import ReflectionAbstract
from orionis.test import TestCase


class _Target(ABC):
    """Supply a real abstract class for the implementation."""

    @abstractmethod
    def execute(self) -> None:
        """Define the required operation."""


class _Partial(IReflectionAbstract):
    """Implement one operation while leaving the rest abstract."""

    def clearCache(self) -> None:
        """Implement one operation without completing the contract."""


class TestIReflectionAbstract(TestCase):
    """Protect required operations and their real runtime signatures."""

    def testContractCannotBeInstantiated(self) -> None:
        """Require implementations to supply all abstract operations."""
        self.assertTrue(issubclass(IReflectionAbstract, ABC))
        self.assertTrue(inspect.isabstract(IReflectionAbstract))
        with self.assertRaises(TypeError):
            IReflectionAbstract()
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
            "getPropertySignature",
            "getPropertyDocstring",
            "constructorSignature",
            "methodSignature",
            "clearCache",
        }
        self.assertEqual(IReflectionAbstract.__abstractmethods__, expected)

    def testConcreteImplementationSatisfiesTheContract(self) -> None:
        """Instantiate the real implementation with its supported target."""
        self.assertFalse(inspect.isabstract(ReflectionAbstract))
        reflected = ReflectionAbstract(_Target)
        self.assertIsInstance(reflected, IReflectionAbstract)

    def testRuntimeSignaturesMatchTheContract(self) -> None:
        """Resolve every annotation and preserve arguments, defaults and returns."""
        for name in sorted(IReflectionAbstract.__abstractmethods__):
            with self.subTest(method=name):
                expected = inspect.signature(
                    getattr(IReflectionAbstract, name),
                    eval_str=True,
                )
                actual = inspect.signature(
                    getattr(ReflectionAbstract, name),
                    eval_str=True,
                )
                self.assertEqual(actual, expected)
