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

    def testValueAfterLiteralReferencePasses(self) -> None:
        """
        Return True when the value comes after the referenced date.

        Validates the comparison against a parsable date string.
        """
        rule = After("2024-01-01")
        self.assertTrue(rule.enforce("born", _MOMENT, _OWNER))
        self.assertFalse(rule.enforce("born", _EARLIER, _OWNER))

    def testEqualMomentFails(self) -> None:
        """
        Return False when the value equals the referenced moment.

        Validates that the comparison is strict.
        """
        self.assertFalse(After(_MOMENT).enforce("born", _MOMENT, _OWNER))

    def testSiblingFieldIsResolved(self) -> None:
        """
        Resolve a string reference as a sibling field when one exists.

        Validates the cross-field comparison path.
        """
        rule = After("start")
        instance = SimpleNamespace(start=_MOMENT)
        self.assertTrue(rule.enforce("end", _LATER, instance))
        self.assertFalse(rule.enforce("end", _EARLIER, instance))

    def testDefaultReferenceIsTheCurrentMoment(self) -> None:
        """
        Compare against the current moment when no reference is supplied.

        Validates that future dates pass and past dates fail.
        """
        rule = After()
        self.assertTrue(rule.enforce("when", DateTime.now().add(days=1), _OWNER))
        self.assertFalse(rule.enforce("when", DateTime.now().subtract(days=1), _OWNER))

    def testRelativeKeywordsAreAccepted(self) -> None:
        """
        Accept the relative keywords understood by the temporal helper.

        Validates that ``yesterday`` resolves to a concrete moment.
        """
        rule = After("yesterday")
        self.assertTrue(rule.enforce("when", DateTime.now(), _OWNER))

    def testStringValueIsParsed(self) -> None:
        """
        Parse a textual value before comparing it with the reference.

        Validates that ISO strings are supported as field values.
        """
        rule = After("2024-01-01")
        self.assertTrue(rule.enforce("born", "2024-06-15", _OWNER))
        self.assertFalse(rule.enforce("born", "2023-06-15", _OWNER))

    def testDateValueIsSupported(self) -> None:
        """
        Accept a plain ``date`` as the value under validation.

        Validates the promotion of dates to the configured timezone.
        """
        rule = After("2024-01-01")
        self.assertTrue(rule.enforce("born", date(2024, 6, 15), _OWNER))

    def testUnresolvableReferenceFails(self) -> None:
        """
        Return False when the reference cannot be resolved into a moment.

        Validates that an unknown field name never passes silently.
        """
        self.assertFalse(After("missing").enforce("born", _MOMENT, _OWNER))

    def testNonDateValuePasses(self) -> None:
        """
        Return True when the value is not a moment at all.

        Validates that type reporting is delegated to the type layer.
        """
        rule = After("2024-01-01")
        self.assertTrue(rule.enforce("born", None, _OWNER))
        self.assertTrue(rule.enforce("born", 123, _OWNER))

class TestAfterOrEqual(TestCase):

    def testEqualMomentPasses(self) -> None:
        """
        Return True when the value equals the referenced moment.

        Validates that the bound is inclusive.
        """
        self.assertTrue(AfterOrEqual(_MOMENT).enforce("born", _MOMENT, _OWNER))

    def testLaterMomentPasses(self) -> None:
        """
        Return True when the value comes after the referenced moment.

        Validates the ordinary success path.
        """
        self.assertTrue(AfterOrEqual(_MOMENT).enforce("born", _LATER, _OWNER))

    def testEarlierMomentFails(self) -> None:
        """
        Return False when the value comes before the referenced moment.

        Validates that earlier dates are rejected.
        """
        self.assertFalse(AfterOrEqual(_MOMENT).enforce("born", _EARLIER, _OWNER))

    def testUnresolvableReferenceFails(self) -> None:
        """
        Return False when the reference cannot be resolved into a moment.

        Validates that an unknown field name never passes silently.
        """
        self.assertFalse(AfterOrEqual("missing").enforce("born", _MOMENT, _OWNER))

class TestBefore(TestCase):

    def testEarlierMomentPasses(self) -> None:
        """
        Return True when the value comes before the referenced moment.

        Validates the ordinary success path.
        """
        self.assertTrue(Before(_MOMENT).enforce("born", _EARLIER, _OWNER))

    def testEqualMomentFails(self) -> None:
        """
        Return False when the value equals the referenced moment.

        Validates that the comparison is strict.
        """
        self.assertFalse(Before(_MOMENT).enforce("born", _MOMENT, _OWNER))

    def testSiblingFieldIsResolved(self) -> None:
        """
        Resolve a string reference as a sibling field when one exists.

        Validates the cross-field comparison path.
        """
        rule = Before("end")
        instance = SimpleNamespace(end=_MOMENT)
        self.assertTrue(rule.enforce("start", _EARLIER, instance))
        self.assertFalse(rule.enforce("start", _LATER, instance))

    def testDefaultReferenceIsTheCurrentMoment(self) -> None:
        """
        Compare against the current moment when no reference is supplied.

        Validates that past dates pass and future dates fail.
        """
        rule = Before()
        self.assertTrue(rule.enforce("when", DateTime.now().subtract(days=1), _OWNER))
        self.assertFalse(rule.enforce("when", DateTime.now().add(days=1), _OWNER))

    def testNonDateValuePasses(self) -> None:
        """
        Return True when the value is not a moment at all.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Before(_MOMENT).enforce("born", None, _OWNER))

class TestBeforeOrEqual(TestCase):

    def testEqualMomentPasses(self) -> None:
        """
        Return True when the value equals the referenced moment.

        Validates that the bound is inclusive.
        """
        self.assertTrue(BeforeOrEqual(_MOMENT).enforce("born", _MOMENT, _OWNER))

    def testEarlierMomentPasses(self) -> None:
        """
        Return True when the value comes before the referenced moment.

        Validates the ordinary success path.
        """
        self.assertTrue(BeforeOrEqual(_MOMENT).enforce("born", _EARLIER, _OWNER))

    def testLaterMomentFails(self) -> None:
        """
        Return False when the value comes after the referenced moment.

        Validates that later dates are rejected.
        """
        self.assertFalse(BeforeOrEqual(_MOMENT).enforce("born", _LATER, _OWNER))

    def testUnresolvableReferenceFails(self) -> None:
        """
        Return False when the reference cannot be resolved into a moment.

        Validates that an unknown field name never passes silently.
        """
        self.assertFalse(BeforeOrEqual("missing").enforce("born", _MOMENT, _OWNER))

class TestDateFormat(TestCase):

    def testMatchingFormatPasses(self) -> None:
        """
        Return True when the value matches the configured format.

        Validates the single-format success path.
        """
        self.assertTrue(DateFormat("YYYY-MM-DD").enforce("born", "2024-01-31", _OWNER))

    def testAnyConfiguredFormatIsAccepted(self) -> None:
        """
        Return True when the value matches one of several formats.

        Validates that every configured format is attempted.
        """
        rule = DateFormat("YYYY-MM-DD", "DD/MM/YYYY")
        self.assertTrue(rule.enforce("born", "2024-01-31", _OWNER))
        self.assertTrue(rule.enforce("born", "31/01/2024", _OWNER))

    def testMismatchedFormatFails(self) -> None:
        """
        Return False when the value matches none of the formats.

        Validates that a different layout is rejected.
        """
        rule = DateFormat("YYYY-MM-DD")
        self.assertFalse(rule.enforce("born", "31/01/2024", _OWNER))
        self.assertFalse(rule.enforce("born", "not-a-date", _OWNER))

    def testNonStringValuePasses(self) -> None:
        """
        Return True when the value is not a string.

        Validates that type reporting is delegated to the type layer.
        """
        rule = DateFormat("YYYY-MM-DD")
        self.assertTrue(rule.enforce("born", _MOMENT + timedelta(days=1), _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """
        Raise ValueError when no format is supplied.

        Validates that the rule refuses a configuration with no effect.
        """
        with self.assertRaises(ValueError):
            DateFormat()
