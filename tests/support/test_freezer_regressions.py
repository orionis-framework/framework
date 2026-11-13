# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect immutable snapshots containing shared and cyclic references."""

from types import MappingProxyType

from orionis.support.structures.freezer import FreezeThaw
from orionis.test import TestCase


class TestFreezerRegressions(TestCase):
    """Preserve graph identity without publishing mutable intermediate values."""

    def testSharedValuesAreFrozenIndependentlyOfTraversalOrder(self) -> None:
        """Resolve shared descendants before every parent references them."""
        for shared in ([1], {"value": 1}):
            for reverse in (False, True):
                with self.subTest(kind=type(shared).__name__, reverse=reverse):
                    pairs = [("nested", {"shared": shared}), ("direct", shared)]
                    original = dict(reversed(pairs) if reverse else pairs)
                    frozen = FreezeThaw.freeze(original)
                    direct = frozen["direct"]
                    self.assertIs(frozen["nested"]["shared"], direct)
                    expected_type = (
                        tuple if isinstance(shared, list) else MappingProxyType
                    )
                    self.assertIsInstance(direct, expected_type)
                    with self.assertRaises(TypeError):
                        direct[0] = 2
                    thawed = FreezeThaw.thaw(frozen)
                    self.assertIs(thawed["nested"]["shared"], thawed["direct"])
                    self.assertIsNot(thawed["direct"], shared)

    def testMappingCyclesRemainImmutableAndPreserveIdentity(self) -> None:
        """Mapping proxies can safely close a cycle through nested sequences."""
        direct = {}
        direct["self"] = direct
        sequence = []
        indirect = {"sequence": sequence}
        sequence.append(indirect)
        for original in (direct, indirect):
            with self.subTest(direct=original is direct):
                frozen = FreezeThaw.freeze(original)
                reference = (
                    frozen["self"] if original is direct else frozen["sequence"][0]
                )
                self.assertIs(reference, frozen)
                with self.assertRaises(TypeError):
                    reference["injected"] = True

    def testSequenceOnlyCyclesCannotExposeMutableIntermediateValues(self) -> None:
        """Reject a cycle that ordinary immutable tuples cannot represent."""
        original = []
        original.append(original)
        with self.assertRaisesRegex(ValueError, "cycl"):
            FreezeThaw.freeze(original)
        self.assertIs(original[0], original)
