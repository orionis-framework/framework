# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify runtime metadata on the real factory and provider interfaces."""

from inspect import isfunction
from typing import get_type_hints

from orionis.orm.factories.factory import Factory
from orionis.orm.factories.fake import Fake, OptionalFake, UniqueFake
from orionis.orm.factories.sequence import Sequence
from orionis.test import TestCase


class TestFactoryRuntimeAnnotations(TestCase):
    """Inspect factory methods and properties using Python's typing API."""

    def testFactoryAndProviderAnnotationsResolveAtRuntime(self) -> None:
        """Resolve provider and collection types without substituting placeholders.

        Returns
        -------
        None
            No return value.
        """
        for cls in (Factory, Fake, UniqueFake, OptionalFake, Sequence):
            for name, member in vars(cls).items():
                function = member.fget if isinstance(member, property) else member
                if isfunction(function) and name != "__annotate_func__":
                    with self.subTest(owner=cls.__name__, method=name):
                        self.assertTrue(get_type_hints(function))
