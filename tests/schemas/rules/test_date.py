from datetime import date, datetime, timedelta
from types import SimpleNamespace
from orionis.schemas.rules.after import After
from orionis.schemas.rules.after_or_equal import AfterOrEqual
from orionis.schemas.rules.before import Before
from orionis.schemas.rules.before_or_equal import BeforeOrEqual
from orionis.schemas.rules.date_format import DateFormat
from orionis.support.facades.datetime import DateTime
from orionis.test import TestCase

# Shared owner instance for rules that never inspect sibling fields.
_OWNER = SimpleNamespace()

# Fixed moments used to keep the comparisons deterministic.
_MOMENT = datetime(2024, 6, 15, 12, 0, 0)
_EARLIER = datetime(2024, 1, 1, 0, 0, 0)
_LATER = datetime(2024, 12, 31, 0, 0, 0)

class TestAfter(TestCase):

    async def testValueAfterLiteralReferencePasses(self) -> None:
        """Return True when the value comes after the referenced date.

        Validates the comparison against a parsable date string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = After("2024-01-01")
        self.assertTrue(await rule.enforce("born", _MOMENT, _OWNER))
        self.assertFalse(await rule.enforce("born", _EARLIER, _OWNER))

    async def testEqualMomentFails(self) -> None:
        """Return False when the value equals the referenced moment.

        Validates that the comparison is strict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await After(_MOMENT).enforce("born", _MOMENT, _OWNER))

    async def testSiblingFieldIsResolved(self) -> None:
        """Resolve a string reference as a sibling field when one exists.

        Validates the cross-field comparison path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = After("start")
        instance = SimpleNamespace(start=_MOMENT)
        self.assertTrue(await rule.enforce("end", _LATER, instance))
        self.assertFalse(await rule.enforce("end", _EARLIER, instance))

    async def testDefaultReferenceIsTheCurrentMoment(self) -> None:
        """Compare against the current moment when no reference is supplied.

        Validates that future dates pass and past dates fail.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = After()
        self.assertTrue(await rule.enforce("when", DateTime.now().add(days=1), _OWNER))
        self.assertFalse(
            await rule.enforce("when", DateTime.now().subtract(days=1), _OWNER),
        )

    async def testRelativeKeywordsAreAccepted(self) -> None:
        """Accept the relative keywords understood by the temporal helper.

        Validates that ``yesterday`` resolves to a concrete moment.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = After("yesterday")
        self.assertTrue(await rule.enforce("when", DateTime.now(), _OWNER))

    async def testStringValueIsParsed(self) -> None:
        """Parse a textual value before comparing it with the reference.

        Validates that ISO strings are supported as field values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = After("2024-01-01")
        self.assertTrue(await rule.enforce("born", "2024-06-15", _OWNER))
        self.assertFalse(await rule.enforce("born", "2023-06-15", _OWNER))

    async def testDateValueIsSupported(self) -> None:
        """Accept a plain ``date`` as the value under validation.

        Validates the promotion of dates to the configured timezone.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = After("2024-01-01")
        self.assertTrue(await rule.enforce("born", date(2024, 6, 15), _OWNER))

    async def testUnresolvableReferenceFails(self) -> None:
        """Return False when the reference cannot be resolved into a moment.

        Validates that an unknown field name never passes silently.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await After("missing").enforce("born", _MOMENT, _OWNER))

    async def testNonDateValuePasses(self) -> None:
        """Return True when the value is not a moment at all.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = After("2024-01-01")
        self.assertTrue(await rule.enforce("born", None, _OWNER))
        self.assertTrue(await rule.enforce("born", 123, _OWNER))

class TestAfterOrEqual(TestCase):

    async def testEqualMomentPasses(self) -> None:
        """Return True when the value equals the referenced moment.

        Validates that the bound is inclusive.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await AfterOrEqual(_MOMENT).enforce("born", _MOMENT, _OWNER))

    async def testLaterMomentPasses(self) -> None:
        """Return True when the value comes after the referenced moment.

        Validates the ordinary success path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await AfterOrEqual(_MOMENT).enforce("born", _LATER, _OWNER))

    async def testEarlierMomentFails(self) -> None:
        """Return False when the value comes before the referenced moment.

        Validates that earlier dates are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await AfterOrEqual(_MOMENT).enforce("born", _EARLIER, _OWNER))

    async def testUnresolvableReferenceFails(self) -> None:
        """Return False when the reference cannot be resolved into a moment.

        Validates that an unknown field name never passes silently.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await AfterOrEqual("missing").enforce("born", _MOMENT, _OWNER))

class TestBefore(TestCase):

    async def testEarlierMomentPasses(self) -> None:
        """Return True when the value comes before the referenced moment.

        Validates the ordinary success path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Before(_MOMENT).enforce("born", _EARLIER, _OWNER))

    async def testEqualMomentFails(self) -> None:
        """Return False when the value equals the referenced moment.

        Validates that the comparison is strict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await Before(_MOMENT).enforce("born", _MOMENT, _OWNER))

    async def testSiblingFieldIsResolved(self) -> None:
        """Resolve a string reference as a sibling field when one exists.

        Validates the cross-field comparison path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Before("end")
        instance = SimpleNamespace(end=_MOMENT)
        self.assertTrue(await rule.enforce("start", _EARLIER, instance))
        self.assertFalse(await rule.enforce("start", _LATER, instance))

    async def testDefaultReferenceIsTheCurrentMoment(self) -> None:
        """Compare against the current moment when no reference is supplied.

        Validates that past dates pass and future dates fail.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = Before()
        self.assertTrue(
            await rule.enforce("when", DateTime.now().subtract(days=1), _OWNER),
        )
        self.assertFalse(await rule.enforce("when", DateTime.now().add(days=1), _OWNER))

    async def testNonDateValuePasses(self) -> None:
        """Return True when the value is not a moment at all.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await Before(_MOMENT).enforce("born", None, _OWNER))

class TestBeforeOrEqual(TestCase):

    async def testEqualMomentPasses(self) -> None:
        """Return True when the value equals the referenced moment.

        Validates that the bound is inclusive.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await BeforeOrEqual(_MOMENT).enforce("born", _MOMENT, _OWNER))

    async def testEarlierMomentPasses(self) -> None:
        """Return True when the value comes before the referenced moment.

        Validates the ordinary success path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(await BeforeOrEqual(_MOMENT).enforce("born", _EARLIER, _OWNER))

    async def testLaterMomentFails(self) -> None:
        """Return False when the value comes after the referenced moment.

        Validates that later dates are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await BeforeOrEqual(_MOMENT).enforce("born", _LATER, _OWNER))

    async def testUnresolvableReferenceFails(self) -> None:
        """Return False when the reference cannot be resolved into a moment.

        Validates that an unknown field name never passes silently.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(
            await BeforeOrEqual("missing").enforce("born", _MOMENT, _OWNER),
        )

class TestDateFormat(TestCase):

    async def testMatchingFormatPasses(self) -> None:
        """Return True when the value matches the configured format.

        Validates the single-format success path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            await DateFormat("YYYY-MM-DD").enforce("born", "2024-01-31", _OWNER),
        )

    async def testAnyConfiguredFormatIsAccepted(self) -> None:
        """Return True when the value matches one of several formats.

        Validates that every configured format is attempted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = DateFormat("YYYY-MM-DD", "DD/MM/YYYY")
        self.assertTrue(await rule.enforce("born", "2024-01-31", _OWNER))
        self.assertTrue(await rule.enforce("born", "31/01/2024", _OWNER))

    async def testMismatchedFormatFails(self) -> None:
        """Return False when the value matches none of the formats.

        Validates that a different layout is rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = DateFormat("YYYY-MM-DD")
        self.assertFalse(await rule.enforce("born", "31/01/2024", _OWNER))
        self.assertFalse(await rule.enforce("born", "not-a-date", _OWNER))

    async def testNonStringValuePasses(self) -> None:
        """Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = DateFormat("YYYY-MM-DD")
        self.assertTrue(await rule.enforce("born", _MOMENT + timedelta(days=1), _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """Raise ValueError when no format is supplied.

        Validates that the rule refuses a configuration with no effect.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            DateFormat()
