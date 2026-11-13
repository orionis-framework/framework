# ruff: noqa: N805, PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Use a nonstandard receiver name to verify binding instead of name guessing.

import gc
import inspect
import weakref
from functools import wraps
from orionis.introspection.dependencies.reflection import (
    ReflectDependencies,
    _get_resolved_signature,
    _get_signature,
)
from orionis.test import TestCase


class _Controller:
    """Provide ordinary, class and static methods for reflection."""

    def handle(receiver, value: int = 7, /, *, label: str = "ok") -> tuple:
        """Return the explicit parameters.

        Parameters
        ----------
        receiver : _Controller
            Bound controller instance.
        value : int, optional
            Positional value.
        label : str, optional
            Keyword-only value.

        Returns
        -------
        tuple
            Provided value and label.
        """
        return value, label

    @classmethod
    def classAction(cls, value: int = 7) -> int:
        """Return a class action argument.

        Parameters
        ----------
        value : int, optional
            Input value.

        Returns
        -------
        int
            Input value.
        """
        return value

    @staticmethod
    def staticAction(value: int = 7) -> int:
        """Return a static action argument.

        Parameters
        ----------
        value : int, optional
            Input value.

        Returns
        -------
        int
            Input value.
        """
        return value


class TestSignatureCache(TestCase):
    """Exercise cached dependency signatures across request-owned instances."""

    def setUp(self) -> None:
        """Isolate global signature entries and release them after every case."""
        for cache in (_get_signature, _get_resolved_signature):
            cache.cache_clear()
            self.addCleanup(cache.cache_clear)

    def testBoundSignaturesDoNotRetainControllers(self) -> None:
        """Reuse one signature and release every transient controller.

        Returns
        -------
        None
            No return value.
        """
        # The test runner can populate signatures after setUp; measure only
        # controller reflection from this point onward.
        _get_signature.cache_clear()
        _get_resolved_signature.cache_clear()
        references = []
        for _ in range(1100):
            controller = _Controller()
            references.append(weakref.ref(controller))
            signature = ReflectDependencies(controller.handle).callableSignature()
            self.assertEqual(tuple(signature.ordered), ("value", "label"))
        del controller
        gc.collect()
        self.assertFalse(any(reference() is not None for reference in references))
        self.assertEqual(_get_resolved_signature.cache_info().misses, 1)
        self.assertEqual(_get_resolved_signature.cache_info().hits, 1099)
        self.assertEqual(_get_signature.cache_info().currsize, 1)

    def testBoundAndUnboundReceiversHaveDistinctSignatures(self) -> None:
        """Exclude a bound receiver without relying on its parameter name.

        Returns
        -------
        None
            No return value.
        """
        bound = ReflectDependencies(_Controller().handle).callableSignature()
        unbound = ReflectDependencies(_Controller.handle).callableSignature()
        self.assertEqual(tuple(bound.ordered), ("value", "label"))
        self.assertEqual(tuple(unbound.ordered), ("receiver", "value", "label"))
        self.assertTrue(bound.ordered["label"].is_keyword_only)

    def testClassAndStaticMethodsPreserveTheirArguments(self) -> None:
        """Resolve class and static descriptors through instances or classes.

        Returns
        -------
        None
            No return value.
        """
        for target in (_Controller, _Controller()):
            reflection = ReflectDependencies(target)
            for name in ("classAction", "staticAction"):
                self.assertEqual(
                    tuple(reflection.methodSignature(name).ordered),
                    ("value",),
                )

    def testWrappedAndCustomSignaturesKeepBoundSemantics(self) -> None:
        """Honor explicit signatures and wrapped methods before binding.

        Returns
        -------
        None
            No return value.
        """

        @wraps(_Controller.handle)
        def wrapped(*args: object, **kwargs: object) -> tuple:
            """Delegate to the original method.

            Parameters
            ----------
            *args : object
                Positional method arguments.
            **kwargs : object
                Keyword method arguments.

            Returns
            -------
            tuple
                Original method result.
            """
            return _Controller.handle(*args, **kwargs)

        custom = type("CustomController", (), {"handle": wrapped})
        wrapped.__signature__ = inspect.Signature(
            [
                inspect.Parameter("receiver", inspect.Parameter.POSITIONAL_ONLY),
                inspect.Parameter("count", inspect.Parameter.KEYWORD_ONLY, default=3),
            ],
        )
        reflected = ReflectDependencies(custom().handle).callableSignature()
        self.assertEqual(tuple(reflected.ordered), ("count",))
        self.assertEqual(reflected.ordered["count"].default, 3)
