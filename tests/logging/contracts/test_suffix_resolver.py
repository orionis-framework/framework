import inspect
from abc import ABC
from orionis.logging.contracts.suffix_resolver import SuffixResolver
from orionis.logging.handlers.chunked_suffix_resolver import ChunkedSuffixResolver
from orionis.logging.handlers.daily_suffix_resolver import DailySuffixResolver
from orionis.logging.handlers.hourly_suffix_resolver import HourlySuffixResolver
from orionis.logging.handlers.monthly_suffix_resolver import MonthlySuffixResolver
from orionis.logging.handlers.weekly_suffix_resolver import WeeklySuffixResolver
from orionis.test import TestCase

# Complete abstract surface published by the rotation contract.
_ABSTRACT_MEMBERS = frozenset({"getSuffix", "getNextRotationTime"})

# Every resolver strategy shipped with the framework.
_SHIPPED_RESOLVERS = (
    ChunkedSuffixResolver,
    DailySuffixResolver,
    HourlySuffixResolver,
    MonthlySuffixResolver,
    WeeklySuffixResolver,
)

class _IncompleteResolver(SuffixResolver):
    """Resolver implementing a single member of the contract on purpose."""

    __slots__ = ()

    def getSuffix(self, _dt: object = None) -> str:
        """Return a constant suffix."""
        return "suffix"

class TestSuffixResolverContract(TestCase):

    def testIsAnAbstractContract(self) -> None:
        """
        Expose the rotation contract as a non instantiable abstraction.

        Validates that handlers can only be configured with a concrete
        strategy.
        """
        self.assertTrue(issubclass(SuffixResolver, ABC))
        self.assertTrue(inspect.isabstract(SuffixResolver))
        with self.assertRaises(TypeError):
            SuffixResolver()

    def testDeclaresTheCompleteAbstractSurface(self) -> None:
        """
        Declare every member required from a rotation strategy.

        Validates the public contract shared by all suffix resolvers.
        """
        self.assertEqual(SuffixResolver.__abstractmethods__, _ABSTRACT_MEMBERS)

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots on the abstraction.

        Validates that implementations keep their instances free of a
        dictionary, as required by the framework conventions.
        """
        self.assertEqual(SuffixResolver.__slots__, ())

    def testEveryAbstractMemberIsDocumented(self) -> None:
        """
        Document every member of the contract.

        Validates that implementers always find the expected behaviour
        described in the abstraction itself.
        """
        for member in sorted(_ABSTRACT_MEMBERS):
            self.assertTrue(inspect.getdoc(getattr(SuffixResolver, member)))

    def testIncompleteImplementationCannotBeInstantiated(self) -> None:
        """
        Reject a strategy missing part of the contract.

        Validates that the abstraction is enforced at instantiation time.
        """
        with self.assertRaises(TypeError):
            _IncompleteResolver()

    def testEveryShippedResolverImplementsTheContract(self) -> None:
        """
        Bind every shipped strategy to the rotation contract.

        Validates that all resolvers can be injected into the rotating file
        handler.
        """
        for resolver_class in _SHIPPED_RESOLVERS:
            self.assertIsInstance(resolver_class(), SuffixResolver)

    def testEveryShippedResolverAvoidsInstanceDictionaries(self) -> None:
        """
        Keep every shipped strategy free of an instance dictionary.

        Validates that the declared slots are effective, which requires the
        abstraction to declare empty slots as well.
        """
        for resolver_class in _SHIPPED_RESOLVERS:
            self.assertFalse(hasattr(resolver_class(), "__dict__"))

    def testEveryShippedResolverMatchesTheContractSignatures(self) -> None:
        """
        Keep every shipped strategy aligned with the contract signatures.

        Validates that resolvers remain interchangeable from the point of view
        of the rotating file handler.
        """
        for member in sorted(_ABSTRACT_MEMBERS):
            expected = inspect.signature(getattr(SuffixResolver, member))
            for resolver_class in _SHIPPED_RESOLVERS:
                actual = inspect.signature(getattr(resolver_class, member))
                self.assertEqual(
                    list(actual.parameters),
                    list(expected.parameters),
                    msg=f"Signature drift on {resolver_class.__name__}.{member}.",
                )
