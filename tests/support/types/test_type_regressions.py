# ruff: noqa: PT009, S301
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Pickle input is produced locally from the canonical marker.
"""Verify copy identity and nonmutating mapping lookups."""

import copy
import pickle
from typing import get_type_hints

from orionis.support.types.dot_dict import DotDict
from orionis.support.types.sentinel import MISSING
from orionis.support.types.uniqueness import unique_items
from orionis.test.cases import TestCase


class TestSupportTypeRegressions(TestCase):
    """Exercise public data helpers with shared mutable structures."""

    def testMissingDictionaryDefaultDoesNotInsert(self) -> None:
        """Return the original default without creating a mapping entry."""
        source = DotDict()
        default = {"nested": []}
        self.assertIs(source.get("missing", default), default)
        self.assertEqual(source, {})

    def testCopyIsDeepAndPreservesSharedReferences(self) -> None:
        """Copy nested lists independently while retaining their shared identity."""
        shared = [{"value": []}]
        source = DotDict(first=shared, second=shared)
        result = source.copy()
        self.assertIs(result["first"], result["second"])
        self.assertIsNot(result["first"], shared)
        result["first"][0]["value"].append("new")
        self.assertEqual(shared, [{"value": []}])

    def testCopyPreservesMappingCycles(self) -> None:
        """Close copied mapping cycles on the copied root."""
        source = DotDict()
        source["self"] = source
        result = source.copy()
        self.assertIs(result["self"], result)

    def testMissingSentinelKeepsIdentityThroughCopyAndPickle(self) -> None:
        """Keep the canonical missing marker through standard copy protocols."""
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.subTest(operation=operation.__name__):
                result = operation(MISSING)
                if isinstance(result, bytes):
                    result = pickle.loads(result)
                self.assertIs(result, MISSING)

    def testUniquenessAnnotationsResolveAtRuntime(self) -> None:
        """Resolve the public selector annotation without caller namespaces."""
        self.assertIn("selector", get_type_hints(unique_items))
