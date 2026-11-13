# ruff: noqa: FBT003, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep established public and external protocol names and signatures.
"""Protect abstract reflection validation, name mangling, and mutation semantics."""

import inspect
from abc import ABC, abstractmethod
from typing import get_type_hints

from orionis.introspection.abstract.contracts.reflection import IReflectionAbstract
from orionis.introspection.abstract.reflection import ReflectionAbstract
from orionis.test import TestCase


def _perform(_receiver: object) -> None:
    """Provide an abstract method body for dynamically declared fixtures.

    Parameters
    ----------
    _receiver : object
        Instance supplied when the fixture method is bound.

    Returns
    -------
    None
        This function does not return a value.
    """


def _abstract_type(name: str = "Contract") -> type:
    """Create an independent abstract class with one removable method.

    Parameters
    ----------
    name : str
        Class name used by Python's private-name mangling rules.

    Returns
    -------
    type
        Abstract class isolated from the other regression scenarios.
    """
    return type(name, (ABC,), {"perform": abstractmethod(_perform)})


class TestAbstractRegressions(TestCase):
    """Exercise public abstract reflection against real Python class behavior."""

    def testRejectsNonClassInputsWithTheDeclaredError(self) -> None:
        """Reject objects lacking a class name through the public TypeError contract."""
        for value in (None, 7, object()):
            with (
                self.subTest(value_type=type(value).__name__),
                self.assertRaises(TypeError),
            ):
                ReflectionAbstract(value)

    def testNormalizesOnlyActualPrivateNamePrefixes(self) -> None:
        """Preserve protected and public names containing the class-name text."""
        for name in ("Contract", "___"):
            with self.subTest(class_name=name):
                target = _abstract_type(name)
                private_name = (
                    "_Contract__private" if name == "Contract" else "__private"
                )
                annotations = {
                    "_ContractHelper": str,
                    "public_Contract_value": int,
                    private_name: bool,
                }
                target.__annotations__ = annotations
                for attribute, value in zip(
                    annotations,
                    ("protected", 2, True),
                    strict=True,
                ):
                    setattr(target, attribute, value)
                reflection = ReflectionAbstract(target)
                self.assertEqual(reflection.getPrivateAttributes(), {"__private": True})
                self.assertEqual(
                    reflection.getProtectedAttributes()["_ContractHelper"],
                    "protected",
                )
                self.assertEqual(
                    reflection.getAnnotations(),
                    {
                        "_ContractHelper": str,
                        "public_Contract_value": int,
                        "__private": bool,
                    },
                )
                reflection.setAttribute("__private", False)
                self.assertIs(getattr(target, private_name), False)
                reflection.removeAttribute("__private")
                self.assertNotIn(private_name, vars(target))

    def testRemovedMethodsCannotBeReturnedFromWarmCaches(self) -> None:
        """Reject a removed method after warming both signature representations."""
        target = _abstract_type()
        reflection = ReflectionAbstract(target)
        reflection.getMethodSignature("perform")
        reflection.methodSignature("perform")
        reflection.removeMethod("perform")
        with self.subTest(surface="inspect"), self.assertRaises(ValueError):
            reflection.getMethodSignature("perform")
        with self.subTest(surface="dependencies"), self.assertRaises(AttributeError):
            reflection.methodSignature("perform")

    def testRemovingAbstractMethodsUpdatesPythonAbstractness(self) -> None:
        """Recompute abstract declarations when the wrapper removes a method."""
        target = _abstract_type()
        self.assertTrue(inspect.isabstract(target))
        ReflectionAbstract(target).removeMethod("perform")
        self.assertFalse(inspect.isabstract(target))
        self.assertIsInstance(target(), target)

    def testReplacingPropertiesRefreshesTheirCachedMetadata(self) -> None:
        """Expose the replacement getter's signature and documentation."""

        def initial(_receiver: object) -> int:
            """Return the original property value.

            Parameters
            ----------
            _receiver : object
                Instance whose property is accessed.

            Returns
            -------
            int
                Original value.
            """
            return 1

        def replacement(_receiver: object) -> str:
            """Return the replacement property value.

            Parameters
            ----------
            _receiver : object
                Instance whose property is accessed.

            Returns
            -------
            str
                Replacement value.
            """
            return "updated"

        target = _abstract_type()
        target.value = property(initial)
        reflection = ReflectionAbstract(target)
        self.assertIs(reflection.getPropertySignature("value").return_annotation, int)
        self.assertEqual(reflection.getPropertyDocstring("value"), initial.__doc__)

        reflection.setAttribute("value", property(replacement))

        self.assertIs(reflection.getPropertySignature("value").return_annotation, str)
        self.assertEqual(reflection.getPropertyDocstring("value"), replacement.__doc__)

    def testPublicContractAnnotationsResolveAtRuntime(self) -> None:
        """Resolve actual signature types from the interface and its implementation."""
        for owner in (IReflectionAbstract, ReflectionAbstract):
            for name in (
                "getMethodSignature",
                "constructorSignature",
                "methodSignature",
            ):
                with self.subTest(owner=owner.__name__, method=name):
                    self.assertIn("return", get_type_hints(getattr(owner, name)))

    def testIdentityRefreshPreservesDeclaredPrivateNames(self) -> None:
        """Refresh mutable class identity without renaming compiled private members."""
        target = _abstract_type()
        target._Contract__private = "retained"
        reflection = ReflectionAbstract(target)
        reflection.setAttribute("__name__", "RenamedContract")
        reflection.setAttribute("__module__", "controlled_module")
        with self.subTest(change="wrapper"):
            self.assertEqual(reflection.getClassName(), "RenamedContract")
            self.assertEqual(reflection.getModuleName(), "controlled_module")
        target.__name__ = "CurrentContract"
        target.__module__ = __name__
        reflection.clearCache()
        with self.subTest(change="external"):
            self.assertEqual(reflection.getClassName(), "CurrentContract")
            self.assertEqual(reflection.getModuleName(), __name__)
            self.assertEqual(
                reflection.getModuleWithClassName(),
                f"{__name__}.CurrentContract",
            )
        self.assertEqual(reflection.getPrivateAttributes(), {"__private": "retained"})
