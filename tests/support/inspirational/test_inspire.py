from orionis.support.inspirational.inspire import Inspire
from orionis.support.inspirational.quotes import INSPIRATIONAL_QUOTES
from orionis.test import TestCase

_VALID_CUSTOM_QUOTES = [
    {"quote": "Test quote one.", "author": "Author A"},
    {"quote": "Test quote two.", "author": "Author B"},
    {"quote": "Test quote three.", "author": "Author C"},
]

# ===========================================================================
# TestInspireInit
# ===========================================================================

class TestInspireInit(TestCase):

    def testDefaultConstructionSucceeds(self) -> None:
        """
        Test that Inspire can be instantiated with no arguments.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire()
        self.assertIsInstance(inspire, Inspire)

    def testNoneQuotesUsesDefaultList(self) -> None:
        """
        Test that passing None as quotes falls back to INSPIRATIONAL_QUOTES.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire(quotes=None)
        internal = inspire._quotes  # type: ignore[attr-defined]
        self.assertIs(internal, INSPIRATIONAL_QUOTES)

    def testEmptyListUsesDefaultList(self) -> None:
        """
        Test that passing an empty list falls back to INSPIRATIONAL_QUOTES.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire(quotes=[])
        internal = inspire._quotes  # type: ignore[attr-defined]
        self.assertIs(internal, INSPIRATIONAL_QUOTES)

    def testValidCustomQuotesAreStored(self) -> None:
        """
        Test that a valid custom quotes list is stored as-is.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire(quotes=_VALID_CUSTOM_QUOTES)
        internal = inspire._quotes  # type: ignore[attr-defined]
        self.assertEqual(internal, _VALID_CUSTOM_QUOTES)

    def testSingleValidQuoteIsAccepted(self) -> None:
        """
        Test that a list containing a single valid quote dict is accepted.

        Returns
        -------
        None
            This method does not return a value.
        """
        single = [{"quote": "One is enough.", "author": "Solo"}]
        inspire = Inspire(quotes=single)
        self.assertIsInstance(inspire, Inspire)

    def testNonDictItemRaisesTypeError(self) -> None:
        """
        Test that passing a list with a non-dict item raises TypeError.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            Inspire(quotes=["not a dict"])  # type: ignore[list-item]

    def testIntItemInListRaisesTypeError(self) -> None:
        """
        Test that passing a list with an integer element raises TypeError.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(TypeError):
            Inspire(quotes=[42])  # type: ignore[list-item]

    def testMissingQuoteKeyRaisesValueError(self) -> None:
        """
        Test that a dict missing the 'quote' key raises ValueError.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(ValueError):
            Inspire(quotes=[{"author": "Someone"}])

    def testMissingAuthorKeyRaisesValueError(self) -> None:
        """
        Test that a dict missing the 'author' key raises ValueError.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(ValueError):
            Inspire(quotes=[{"quote": "A quote"}])

    def testEmptyDictRaisesValueError(self) -> None:
        """
        Test that a list containing an empty dict raises ValueError.

        Returns
        -------
        None
            This method does not return a value.
        """
        with self.assertRaises(ValueError):
            Inspire(quotes=[{}])

    def testPartiallyValidListRaisesErrorOnBadItem(self) -> None:
        """
        Test that validation fails even if only one dict in the list is invalid.

        Returns
        -------
        None
            This method does not return a value.
        """
        mixed = [
            {"quote": "Good one.", "author": "Good Author"},
            {"author": "Bad — no quote key"},  # Missing 'quote'
        ]
        with self.assertRaises(ValueError):
            Inspire(quotes=mixed)


# ===========================================================================
# TestInspireRandom
# ===========================================================================


class TestInspireRandom(TestCase):
    """Tests for the Inspire.random method."""

    def testRandomReturnsDict(self) -> None:
        """
        Test that random() returns a dict.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire()
        result = inspire.random()
        self.assertIsInstance(result, dict)

    def testRandomResultHasQuoteKey(self) -> None:
        """
        Test that the dict returned by random() contains a 'quote' key.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire()
        result = inspire.random()
        self.assertIn("quote", result)

    def testRandomResultHasAuthorKey(self) -> None:
        """
        Test that the dict returned by random() contains an 'author' key.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire()
        result = inspire.random()
        self.assertIn("author", result)

    def testRandomQuoteValueIsNonEmptyString(self) -> None:
        """
        Test that the 'quote' value in the returned dict is a non-empty string.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire()
        result = inspire.random()
        self.assertIsInstance(result["quote"], str)
        self.assertGreater(len(result["quote"].strip()), 0)

    def testRandomAuthorValueIsNonEmptyString(self) -> None:
        """
        Test that the 'author' value in the returned dict is a non-empty string.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire()
        result = inspire.random()
        self.assertIsInstance(result["author"], str)
        self.assertGreater(len(result["author"].strip()), 0)

    def testRandomWithCustomQuotesReturnsItemFromList(self) -> None:
        """
        Test that random() returns one of the provided custom quotes.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire(quotes=_VALID_CUSTOM_QUOTES)
        result = inspire.random()
        self.assertIn(result, _VALID_CUSTOM_QUOTES)

    def testRandomCalledRepeatedlyAlwaysReturnsValid(self) -> None:
        """
        Test that random() returns valid dicts across multiple calls.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire(quotes=_VALID_CUSTOM_QUOTES)
        for _ in range(20):
            result = inspire.random()
            self.assertIn("quote", result)
            self.assertIn("author", result)

    def testRandomWithSingleQuoteAlwaysReturnsThatQuote(self) -> None:
        """
        Test that random() returns the only available quote when the list has one entry.

        Returns
        -------
        None
            This method does not return a value.
        """
        single = [{"quote": "Unique.", "author": "Solo"}]
        inspire = Inspire(quotes=single)
        for _ in range(5):
            result = inspire.random()
            self.assertEqual(result, single[0])

    def testRandomFallbackWhenInternalListIsEmpty(self) -> None:
        """
        Test that random() returns the fallback dict when the internal list is cleared.

        Both _quotes and _count are patched to zero to exercise the fallback
        code path that guards against an empty sequence.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire(quotes=_VALID_CUSTOM_QUOTES)
        # Patch both attributes so random() enters the fallback branch.
        inspire._quotes = []  # type: ignore[attr-defined]
        inspire._count = 0  # type: ignore[attr-defined]
        result = inspire.random()
        self.assertIsInstance(result, dict)
        self.assertIn("quote", result)
        self.assertIn("author", result)

    def testFallbackQuoteIsNonEmpty(self) -> None:
        """
        Test that the fallback quote and author are non-empty strings.

        Both _quotes and _count are patched to zero to enter the fallback branch.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire(quotes=_VALID_CUSTOM_QUOTES)
        inspire._quotes = []  # type: ignore[attr-defined]
        inspire._count = 0  # type: ignore[attr-defined]
        result = inspire.random()
        self.assertGreater(len(result["quote"].strip()), 0)
        self.assertGreater(len(result["author"].strip()), 0)

    def testRandomDefaultInspireReturnsResultFromDefaultList(self) -> None:
        """
        Test that the result of random() on a default Inspire belongs to INSP_QUOTES.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire()
        result = inspire.random()
        self.assertIn(result, INSPIRATIONAL_QUOTES)

    def testRandomResultHasExactlyTwoKeys(self) -> None:
        """
        Test that the dict returned by random() has exactly 'quote' and 'author' keys.

        Returns
        -------
        None
            This method does not return a value.
        """
        inspire = Inspire()
        result = inspire.random()
        self.assertEqual(set(result.keys()), {"quote", "author"})
