# ruff: noqa: PT009, S102
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Compile a controlled fixture without inherited future flags to exercise PEP 649.
"""Preserve unresolved native Python 3.14 annotations during reflection."""

import sys
from annotationlib import ForwardRef
from types import ModuleType
from unittest.mock import patch

from orionis.container.container import Container
from orionis.introspection.abstract.reflection import ReflectionAbstract
from orionis.introspection.callables.reflection import ReflectionCallable
from orionis.introspection.concretes.reflection import ReflectionConcrete
from orionis.introspection.dependencies.reflection import ReflectDependencies
from orionis.introspection.instances.reflection import ReflectionInstance
from orionis.test import TestCase

_SOURCE = '''
from abc import ABC, abstractmethod

def deferred(known: int, missing: UndefinedDelayedType) -> tuple:
    """Return supplied values without evaluating their deferred annotations."""
    return known, missing

def build_closure():
    """Return a callable whose known type lives only in its closure."""
    class LocalType:
        """Represent a type unavailable from the module namespace."""
    def deferred(known: LocalType, missing: UndefinedDelayedType) -> None:
        """Receive a closure type and an unavailable native annotation."""
    return deferred, LocalType

class Abstract(ABC):
    """Declare deferred class fields and abstract members."""
    known: int
    missing: UndefinedDelayedType

    @abstractmethod
    def method(self, known: int, missing: UndefinedDelayedType) -> None:
        """Declare a method carrying an unknown native annotation."""

    @property
    @abstractmethod
    def item(self) -> UndefinedDelayedType:
        """Declare a property with an unresolved result type."""

class Concrete:
    """Declare deferred fields and ordinary members."""
    known: int
    missing: UndefinedDelayedType

    def method(self, known: int, missing: UndefinedDelayedType) -> None:
        """Declare a method carrying an unknown native annotation."""

    @property
    def item(self) -> UndefinedDelayedType:
        """Declare a property with an unresolved result type."""

class Constructed:
    """Accept explicit arguments despite an unknown deferred annotation."""

    def __init__(self, known: int, missing: UndefinedDelayedType) -> None:
        """Retain explicitly supplied constructor values."""
        self.values = known, missing
'''


class TestDeferredAnnotations(TestCase):
    """Inspect native deferred annotations without executing the callable."""

    def setUp(self) -> None:
        """Compile a module using the active interpreter's native annotation mode."""
        super().setUp()
        self.module = ModuleType("_orionis_native_annotations_regression")
        self.enterContext(
            patch.dict(sys.modules, {self.module.__name__: self.module}),
        )
        exec(
            compile(
                _SOURCE,
                "<native-deferred-annotations>",
                "exec",
                dont_inherit=True,
            ),
            vars(self.module),
        )

    def testPreservesUnknownNativeAnnotationsAndResolvesKnownTypes(self) -> None:
        """Keep unknown names conservative without losing a known parameter type."""
        closure, local_type = self.module.build_closure()
        for target, known_type in ((self.module.deferred, int), (closure, local_type)):
            with self.subTest(target=target.__qualname__, operation="dependencies"):
                signature = ReflectDependencies(target).callableSignature()
                self.assertIs(signature.ordered["known"].type, known_type)
                missing = signature.ordered["missing"]
                self.assertIs(missing.type, str)
                self.assertEqual(missing.class_name, "UndefinedDelayedType")
                self.assertEqual(missing.module_name, "typing")
                self.assertTrue(missing.resolved)
                self.assertFalse(missing.is_schema)
            with self.subTest(target=target.__qualname__, operation="wrapper"):
                signature = ReflectionCallable(target).getSignature()
                self.assertIs(signature.parameters["known"].annotation, known_type)
                missing = signature.parameters["missing"].annotation
                self.assertIsInstance(missing, ForwardRef)
                self.assertEqual(missing.__forward_arg__, "UndefinedDelayedType")

    def testPreservesDeferredClassAndMemberAnnotations(self) -> None:
        """Read fields, methods, and properties without requiring unknown names."""
        for wrapper in (
            ReflectionAbstract(self.module.Abstract),
            ReflectionConcrete(self.module.Concrete),
            ReflectionInstance(self.module.Concrete()),
        ):
            with self.subTest(wrapper=type(wrapper).__name__, operation="fields"):
                annotations = wrapper.getAnnotations()
                self.assertIs(annotations["known"], int)
                self.assertIsInstance(annotations["missing"], ForwardRef)
                self.assertEqual(
                    annotations["missing"].__forward_arg__,
                    "UndefinedDelayedType",
                )
            with self.subTest(wrapper=type(wrapper).__name__, operation="method"):
                signature = wrapper.getMethodSignature("method")
                self.assertIs(signature.parameters["known"].annotation, int)
                self.assertIsInstance(
                    signature.parameters["missing"].annotation,
                    ForwardRef,
                )
            with self.subTest(wrapper=type(wrapper).__name__, operation="property"):
                signature = wrapper.getPropertySignature("item")
                self.assertIsInstance(signature.return_annotation, ForwardRef)

    async def testInvokesAndBuildsWithExplicitNativeDeferredArguments(self) -> None:
        """Pass caller-owned values through native deferred callable and class plans."""
        container = object.__new__(Container)
        Container.__init__(container)
        missing = object()
        self.assertEqual(
            await container.invoke(self.module.deferred, 7, missing),
            (7, missing),
        )
        instance = await container.build(self.module.Constructed, 7, missing)
        self.assertEqual(instance.values, (7, missing))
