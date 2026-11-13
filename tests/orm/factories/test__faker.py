# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from faker import Faker
from orionis.orm.factories._faker import create_faker
from orionis.orm.factories.fake import Fake
from orionis.test import TestCase


class TestFactoryProvider(TestCase):
    """Use the guaranteed Faker dependency with independent factory state."""

    def testProviderUsesInstalledFaker(self) -> None:
        """Expose native Faker data through the public facade.

        Returns
        -------
        None
            No return value.
        """
        native = Faker("es_CO")
        native.seed_instance(42)
        fake = create_faker("es-CO", 42)
        self.assertIsInstance(fake, Fake)
        self.assertEqual(fake.locales, ["es_CO"])
        self.assertEqual(fake.name(), native.name())

    def testUnseededProvidersHaveIndependentRandomState(self) -> None:
        """Detach factory randomness even when no explicit seed is supplied.

        Returns
        -------
        None
            No return value.
        """
        first = create_faker("en_US", None)
        second = create_faker("en_US", None)
        state = second.random.getstate()
        self.assertIsNot(first.random, second.random)
        first.name()
        self.assertEqual(second.random.getstate(), state)
