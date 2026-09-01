from __future__ import annotations
from orionis.test import TestCase
from orionis.container.contracts.deferrable_provider import IDeferrableProvider
from orionis.container.providers.deferrable_provider import DeferrableProvider

# ---------------------------------------------------------------------------
# Module-level doubles
# ---------------------------------------------------------------------------

_ALIAS = "x-orionis-probe"

class _ConcreteDeferred(DeferrableProvider):
    """Concrete provider declaring both a type and an alias."""

    @classmethod
    def provides(cls) -> list[type | str]:
        """Return the services published by this provider."""
        return [str, _ALIAS]

class _EmptyDeferred(DeferrableProvider):
    """Concrete provider that publishes no service at all."""

    @classmethod
    def provides(cls) -> list[type | str]:
        """Return an empty service list."""
        return []

# ===========================================================================
# Contract compliance
# ===========================================================================

class TestDeferrableProviderContract(TestCase):

    def testConcreteProviderSatisfiesTheDeferrableContract(self) -> None:
        """
        Satisfy the IDeferrableProvider contract with a concrete provider.

        Returns
        -------
        None
            This method does not return a value.
        """
        provider = _ConcreteDeferred()
        self.assertIsInstance(provider, DeferrableProvider)
        self.assertIsInstance(provider, IDeferrableProvider)

# ===========================================================================
# provides()
# ===========================================================================

class TestDeferrableProviderProvides(TestCase):

    def testBaseProvidesRaisesNotImplementedError(self) -> None:
        """
        Raise NotImplementedError when provides() is not overridden.

        The base implementation is a sentinel forcing every subclass to
        declare the services it publishes.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(NotImplementedError) as ctx:
            DeferrableProvider.provides()
        self.assertIn("provides", str(ctx.exception))

    def testOverriddenProvidesReturnsTheDeclaredServices(self) -> None:
        """
        Return the declared service types and aliases from provides().

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(_ConcreteDeferred.provides(), [str, _ALIAS])

    def testOverriddenProvidesMayReturnAnEmptyList(self) -> None:
        """
        Allow provides() to declare that nothing is published.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(_EmptyDeferred.provides(), [])
