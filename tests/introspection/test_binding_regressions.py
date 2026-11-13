# ruff: noqa: N804, N805, PLW0211, PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Deliberately vary receiver names to test Python descriptor binding.
"""Preserve real parameters independently of conventional receiver names."""

from typing import get_type_hints
from orionis.container.container import Container
from orionis.introspection.dependencies.entities.argument import Argument
from orionis.introspection.dependencies.entities.signature import Signature
from orionis.introspection.dependencies.reflection import ReflectDependencies
from orionis.introspection.reflection import Reflection
from orionis.test import TestCase


def _named_parameters(self: int = 3, cls: int = 5) -> tuple[int, int]:
    """Return ordinary parameters named like conventional receivers."""
    return self, cls


class _UnusualReceiver:
    """Expose every ordinary descriptor with unconventional parameter names."""

    def __init__(receiver, self: int = 3, cls: int = 5) -> None:
        """Store the explicit constructor values."""
        receiver.values = self, cls

    def handle(receiver, self: int = 3, cls: int = 5) -> tuple[int, int]:
        """Return the two explicit method values."""
        return self, cls

    @staticmethod
    def staticAction(self: int = 3, cls: int = 5) -> tuple[int, int]:
        """Preserve all parameters of a static method."""
        return self, cls

    @classmethod
    def classAction(receiver, self: int = 3, cls: int = 5) -> tuple[int, int]:
        """Exclude only the automatically bound class receiver."""
        return self, cls


class TestBindingRegressions(TestCase):
    """Check reflection and injection against Python's actual binding rules."""

    def testReceiverNamesDoNotIdentifyDependencies(self) -> None:
        """Keep self and cls except where Python supplies the first receiver."""
        self.assertEqual(
            tuple(ReflectDependencies(_named_parameters).callableSignature().ordered),
            ("self", "cls"),
        )
        for target in (_UnusualReceiver, _UnusualReceiver()):
            reflection = ReflectDependencies(target)
            with self.subTest(target=type(target).__name__, operation="constructor"):
                self.assertEqual(
                    tuple(reflection.constructorSignature().ordered),
                    ("self", "cls"),
                )
            for method in ("handle", "staticAction", "classAction"):
                with self.subTest(target=type(target).__name__, method=method):
                    self.assertEqual(
                        tuple(reflection.methodSignature(method).ordered),
                        ("self", "cls"),
                    )
        unbound = ReflectDependencies(_UnusualReceiver.handle).callableSignature()
        self.assertEqual(tuple(unbound.ordered), ("receiver", "self", "cls"))

    async def testContainerUsesOnlyTheExplicitDependencies(self) -> None:
        """Invoke free functions and construct classes with valid defaults."""
        container = Container()
        self.assertEqual(await container.invoke(_named_parameters), (3, 5))
        instance = await container.build(_UnusualReceiver)
        self.assertEqual(instance.values, (3, 5))
        self.assertEqual(await container.invoke(instance.handle), (3, 5))

    def testEntityAndFactoryAnnotationsResolveAtRuntime(self) -> None:
        """Expose usable public annotations on entities and reflection factories."""
        for entity in (Argument, Signature):
            with self.subTest(entity=entity.__name__):
                self.assertTrue(get_type_hints(entity))
        for name in ("abstract", "concrete", "instance", "callable", "module"):
            with self.subTest(factory=name):
                self.assertIn("return", get_type_hints(getattr(Reflection, name)))

    def testUnhashableCallablesRemainInspectable(self) -> None:
        """Treat cache eligibility independently of the callable contract."""
        function = type(
            "UnhashableCallable",
            (),
            {"__hash__": None, "__call__": _UnusualReceiver.handle},
        )()
        signature = ReflectDependencies(function).callableSignature()
        self.assertEqual(tuple(signature.ordered), ("self", "cls"))
        self.assertEqual(signature.ordered["self"].default, 3)
