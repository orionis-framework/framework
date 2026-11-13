# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Exercise literal string transformations and boundary inputs."""

from datetime import timedelta
from typing import get_type_hints

from orionis.support.types.stringable import Stringable
from orionis.test.cases import TestCase


class TestStringableRegressions(TestCase):
    """Verify transformations independently of regex and platform side effects."""

    def testSplitWithoutPatternPreservesNativeWhitespaceRules(self) -> None:
        """
        Support the inherited no-argument split operation and its whitespace rules.

        Returns
        -------
        None
            Match native splitting for empty text, whitespace and bounded splits.
        """
        for text in ("", "  one\t two\nthree  ", "one\u00a0two"):
            with self.subTest(text=text):
                value = Stringable(text)
                self.assertEqual(value.split(), text.split())
                self.assertEqual(value.split(None, 1), text.split(None, 1))

    def testSplitRejectsInvalidChunkSizesAndLimits(self) -> None:
        """
        Reject chunk sizes and limits that cannot describe a split operation.

        Returns
        -------
        None
            Raise explicit validation errors rather than silently returning no data.
        """
        value = Stringable("abcdef")
        for pattern, limit, error in (
            (0, -1, ValueError),
            (-2, -1, ValueError),
            (True, -1, TypeError),
            (2, 0.5, TypeError),
        ):
            with self.subTest(pattern=pattern, limit=limit), self.assertRaises(error):
                value.split(pattern, limit)

    def testLiteralReplacementsPreserveBackslashes(self) -> None:
        """Treat literal replacements and separators as data."""
        cases = (
            (
                lambda: Stringable("ABC").replace("abc", r"\1", case_sensitive=False),
                r"\1",
            ),
            (lambda: Stringable("a\\\\b").deduplicate("\\"), "a\\b"),
            (lambda: Stringable("oneTwo three").snake("\\"), "one\\two\\three"),
            (lambda: Stringable("one two").slug("\\"), "one\\two"),
            (lambda: Stringable("oneTwo three").snake(""), "onetwothree"),
            (lambda: Stringable("one two").slug(""), "onetwo"),
        )
        for operation, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(operation(), expected)

    def testSequentialReplacementDoesNotRescanInsertedText(self) -> None:
        """Apply replacements to successive occurrences in the original input."""
        self.assertEqual(
            Stringable("? ?").replaceArray("?", ["?first", "second"]),
            "?first second",
        )

    def testRegexReplacementHonorsZeroAndRejectsInvalidLimit(self) -> None:
        """Treat zero as no replacements and reject limits below minus one."""
        for limit in (0, -2):
            with self.subTest(limit=limit):
                if limit == 0:
                    self.assertEqual(
                        Stringable("aaa").replaceMatches("a", "x", limit),
                        "aaa",
                    )
                else:
                    with self.assertRaises(ValueError):
                        Stringable("aaa").replaceMatches("a", "x", limit)

    def testEmptySuffixPreservesExistingText(self) -> None:
        """Handle empty suffixes consistently with native string operations."""
        self.assertEqual(Stringable("text").chopEnd(""), "text")
        self.assertEqual(Stringable("text").replaceEnd("", "!"), "text!")

    def testScanReturnsWholeCapturesAndEscapesFormatLiterals(self) -> None:
        """Parse only supported placeholders and retain each complete value."""
        cases = (
            ("id=123", "id=%d", ["123"]),
            ("value=(hello)", "value=(%s)", ["hello"]),
            ("valueX123", "value.%d", []),
            ("-12 -1.25", "%d %f", ["-12", "-1.25"]),
        )
        for value, pattern, expected in cases:
            with self.subTest(pattern=pattern):
                self.assertEqual(Stringable(value).scan(pattern), expected)

    def testCaseSensitivePatternsArePlatformIndependent(self) -> None:
        """Respect case sensitivity even on Windows."""
        self.assertFalse(Stringable("Report.TXT").isPattern("report.*"))
        self.assertTrue(
            Stringable("Report.TXT").isPattern("report.*", ignore_case=True),
        )

    def testMatchAcceptsSinglePassIterables(self) -> None:
        """Consume iterable patterns once before matching."""
        self.assertTrue(Stringable("abc").isMatch(iter(("x", "abc"))))

    def testUlidRejectsOverflowAndAcceptsMaximum(self) -> None:
        """Require the 26-character encoding to fit in 128 bits."""
        self.assertTrue(Stringable("7" + "Z" * 25).isUlid())
        for value in ("8" + "0" * 25, "Z" * 26, "0" + "\u017f" * 25):
            with self.subTest(value=value):
                self.assertFalse(Stringable(value).isUlid())

    def testDateWithoutFormatParsesIsoAndPreservesOffset(self) -> None:
        """Parse ISO dates while retaining explicit timezone information."""
        result = Stringable("2025-01-02T03:04:05+02:00").toDate(None)
        self.assertEqual(result.utcoffset(), timedelta(hours=2))
        self.assertEqual((result.year, result.month, result.day), (2025, 1, 2))

    def testCryptAnnotationsDescribeReturnedStrings(self) -> None:
        """Describe the existing facade return type accurately."""
        for operation in (Stringable.encrypt, Stringable.decrypt):
            with self.subTest(operation=operation.__name__):
                self.assertIs(get_type_hints(operation)["return"], str)

    def testStripTagsHonorsAllowlistAndQuotedDelimiters(self) -> None:
        """Keep only explicitly allowed markup and parse quoted attributes."""
        self.assertEqual(
            Stringable("<b>Hello</b><i>world</i>&amp;").stripTags("<b>"),
            "<b>Hello</b>world&",
        )
        self.assertEqual(Stringable('<b title="1 > 0">Hello</b>').stripTags(), "Hello")

    def testNegativeSubstringOffsetsUseCharacterLengths(self) -> None:
        """Measure length from the normalized negative start position."""
        self.assertEqual(Stringable("abcdef").substr(-2, 2), "ef")
        self.assertEqual(Stringable("aaaaaa").substrCount("a", -2, 2), 2)
