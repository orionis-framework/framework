from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from orionis.http.payload.uploaded_file import UploadedFile
from orionis.schemas.rules.measure import KILOBYTE, is_file, measure, read_content
from orionis.schemas.rules.temporal import parse_moment, resolve_moment, to_datetime
from orionis.support.facades.datetime import DateTime
from orionis.test import TestCase

def _upload(data: bytes) -> UploadedFile:
    """
    Build an uploaded file holding the given content.

    Parameters
    ----------
    data : bytes
        Content written into the upload buffer.

    Returns
    -------
    UploadedFile
        Upload ready to be handed to a helper.
    """
    upload = UploadedFile("a.txt", "text/plain")
    upload.write(data)
    return upload

class TestIsFile(TestCase):

    def testUploadedFileIsDetected(self) -> None:
        """Return True for an object implementing the upload protocol.

        Validates the structural detection used to stay decoupled from
        the HTTP payload package.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(is_file(_upload(b"a")))

    def testForeignObjectsAreRejected(self) -> None:
        """Return False for objects missing part of the upload protocol.

        Validates that partial look-alikes are not treated as files.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for value in ("text", b"bytes", None, SimpleNamespace(read=print)):
            self.assertFalse(is_file(value))

class TestReadContent(TestCase):

    def testUploadContentIsReturned(self) -> None:
        """Return the whole buffered content of an uploaded file.

        Validates that the buffer is rewound before reading.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(read_content(_upload(b"payload")), b"payload")

    def testForeignValueReturnsNone(self) -> None:
        """Return None when the value is not a readable upload.

        Validates that plain data never reaches the reading path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(read_content("text"))
        self.assertIsNone(read_content(None))

class TestMeasure(TestCase):

    def testNumbersReturnTheirMagnitude(self) -> None:
        """Return the number itself for every numeric type.

        Validates that integers, floats and decimals are comparable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(measure(42), 42)
        self.assertEqual(measure(2.5), 2.5)
        self.assertEqual(measure(Decimal("1.50")), 1.5)

    def testSizedValuesReturnTheirLength(self) -> None:
        """Return the length for strings and collections.

        Validates the size semantics applied to sized values.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(measure("abc"), 3)
        self.assertEqual(measure([1, 2]), 2)
        self.assertEqual(measure({"a": 1}), 1)
        self.assertEqual(measure(b"abcd"), 4)

    def testUploadsAreMeasuredInKilobytes(self) -> None:
        """Return the upload size expressed in kilobytes.

        Validates that files use a different unit from collections.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(measure(_upload(b"x" * KILOBYTE)), 1)

    def testBooleansAndForeignObjectsReturnNone(self) -> None:
        """Return None for values that carry no comparable size.

        Validates that booleans are never measured as integers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(measure(True))
        self.assertIsNone(measure(False))
        self.assertIsNone(measure(None))
        self.assertIsNone(measure(object()))

class TestToDatetime(TestCase):

    def testDatetimeIsConvertedToTheConfiguredTimezone(self) -> None:
        """Return a timezone-aware moment for a naive datetime.

        Validates that naive values are anchored to the configured zone.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        moment = to_datetime(datetime(2024, 6, 15, 12))
        self.assertIsNotNone(moment)
        self.assertIsNotNone(moment.tzinfo)
        self.assertEqual(moment.year, 2024)

    def testDateIsPromotedToMidnight(self) -> None:
        """Return the start of the day for a plain date.

        Validates that dates are promoted without losing the day.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        moment = to_datetime(date(2024, 6, 15))
        self.assertIsNotNone(moment)
        self.assertEqual(moment.day, 15)
        self.assertEqual(moment.hour, 0)

    def testStringIsParsed(self) -> None:
        """Return a moment for a parsable date string.

        Validates the textual coercion path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        moment = to_datetime("2024-06-15")
        self.assertIsNotNone(moment)
        self.assertEqual(moment.month, 6)

    def testForeignValuesReturnNone(self) -> None:
        """Return None when the value does not represent a moment.

        Validates that unrelated types are rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(to_datetime(None))
        self.assertIsNone(to_datetime(123))
        self.assertIsNone(to_datetime("not-a-date"))

class TestParseMoment(TestCase):

    def testRelativeKeywordsAreResolved(self) -> None:
        """Resolve every supported relative keyword into a concrete moment.

        Validates the ordering between yesterday, today and tomorrow.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        yesterday = parse_moment("yesterday")
        today = parse_moment("TODAY")
        tomorrow = parse_moment(" tomorrow ")
        now = parse_moment("now")
        self.assertIsNotNone(now)
        self.assertLess(yesterday, today)
        self.assertLess(today, tomorrow)

    def testMidnightIsUsedForDayKeywords(self) -> None:
        """Resolve the day keywords to the start of their day.

        Validates that the time component is cleared.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        today = parse_moment("today")
        self.assertEqual(today.hour, 0)
        self.assertEqual(today.minute, 0)

    def testInvalidTextReturnsNone(self) -> None:
        """Return None when the text is not a parsable date.

        Validates that parser errors never escape the helper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(parse_moment("not-a-date"))
        self.assertIsNone(parse_moment(""))

class TestResolveMoment(TestCase):

    def testNoneResolvesToTheCurrentMoment(self) -> None:
        """Resolve a missing reference into the current moment.

        Validates the default comparison target used by the date rules.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        resolved = resolve_moment(None, SimpleNamespace())
        self.assertIsNotNone(resolved)
        self.assertLess(abs((DateTime.now() - resolved).total_seconds()), 5)

    def testSiblingFieldTakesPrecedenceOverParsing(self) -> None:
        """Resolve a string reference as a sibling field when one exists.

        Validates that field lookup is attempted before date parsing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = SimpleNamespace(start=datetime(2024, 6, 15))
        resolved = resolve_moment("start", instance)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.day, 15)

    def testLiteralDateIsParsedWhenNoSiblingExists(self) -> None:
        """Parse a string reference when the instance has no such field.

        Validates the fallback to textual parsing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        resolved = resolve_moment("2024-06-15", SimpleNamespace())
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.month, 6)

    def testUnresolvableReferenceReturnsNone(self) -> None:
        """Return None when the reference names nothing and parses to nothing.

        Validates that the date rules can detect a broken configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(resolve_moment("missing", SimpleNamespace()))
