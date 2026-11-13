# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect refreshed metadata on an existing callable reflection wrapper."""

from orionis.introspection.callables.reflection import ReflectionCallable
from orionis.test import TestCase


class TestCallableRegressions(TestCase):
    """Refresh mutable callable metadata through the public cache lifecycle."""

    def testRefreshesNamesAndDocstringsWhenClearingTheCache(self) -> None:
        """Refresh mutable Python function attributes after explicit invalidation."""

        def original() -> None:
            """Represent a callable whose descriptive metadata can change."""

        reflection = ReflectionCallable(original)
        original.__name__ = "renamed"
        original.__module__ = "synthetic.module"
        original.__doc__ = "Updated callable documentation."
        reflection.clearCache()
        self.assertEqual(reflection.getName(), original.__name__)
        self.assertEqual(reflection.getModuleName(), original.__module__)
        self.assertEqual(reflection.getDocstring(), original.__doc__)
        self.assertEqual(
            reflection.getModuleWithCallableName(),
            "synthetic.module.renamed",
        )
