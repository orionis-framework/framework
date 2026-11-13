# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect facade introspection and bounded dispatcher retention."""

import gc
import weakref
from typing import get_type_hints

from orionis.container.entities.invocation import InvocationPlan, callable_plan
from orionis.container.facades import meta
from orionis.container.facades.facade import Facade, ScopedFacade
from orionis.test import TestCase


class TestFacadeRegressions(TestCase):
    """Exercise missing protocol attributes without resolving an application."""

    def testRejectsMissingIntrospectionProtocolAttributes(self) -> None:
        """Keep Python probes from becoming callable service dispatchers."""
        for facade in (Facade, ScopedFacade):
            for name in ("__no_type_check__", "__wrapped__", "__signature__"):
                with (
                    self.subTest(facade=facade.__name__, name=name),
                    self.assertRaises(AttributeError),
                ):
                    getattr(facade, name)

    def testReleasesEvictedFacadeClasses(self) -> None:
        """Bound class retention when applications generate many facade types."""
        self.addCleanup(meta._dispatcher_for.cache_clear)
        first = None
        for index in range(1100):
            facade = type(f"EphemeralFacade{index}", (Facade,), {})
            if first is None:
                first = weakref.ref(facade)
            _ = facade.dynamic_method
        del facade
        gc.collect()
        self.assertIsNone(first())

    def testResolvesFacadeAndInvocationAnnotations(self) -> None:
        """Retain runtime types used to inspect dispatch and invocation plans."""
        for target, parameter in (
            (Facade, "_application"),
            (ScopedFacade, "_application"),
            (meta._FacadeDispatch.__await__, "return"),
            (meta._FacadeDispatch.__aexit__, "traceback"),
            (InvocationPlan, "arguments"),
            (callable_plan, "target"),
        ):
            with self.subTest(target=target.__qualname__):
                self.assertIn(parameter, get_type_hints(target))
