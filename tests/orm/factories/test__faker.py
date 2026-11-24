# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from faker import Faker
from datetime import UTC
from unittest.mock import patch
from orionis.orm.factories._faker import create_faker
from orionis.orm.factories.fake import Fake
from orionis.test import TestCase
from orionis.support.facades import DateTime


class TestFactoryProvider(TestCase):
    """
    Verify Faker setup for model factories.

    Check locale, timezone and random state across independent generators.
    """

    def testTemporalProvidersUseApplicationZoneUnlessOverridden(self) -> None:
        """
        Apply defaults to each provider view while honoring explicit arguments.

        Returns
        -------
        None
            Assert the timezone of each generated value.
        """
        with patch.object(DateTime, "getTimezone", return_value="America/Bogota"):
            fake = create_faker("en_US", 42)
            self.assertEqual(fake.dateTime().tzinfo, DateTime.getZoneInfo())
            self.assertEqual(fake.unique.dateTime().tzinfo, DateTime.getZoneInfo())
            self.assertEqual(
                fake.optional.dateTime(prob=1).tzinfo, DateTime.getZoneInfo(),
            )
            self.assertEqual(fake.dateTime(UTC).tzinfo, UTC)
            self.assertIsNone(fake.dateTime(tzinfo=None).tzinfo)

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
