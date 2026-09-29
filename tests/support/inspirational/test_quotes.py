from orionis.support.inspirational.quotes import INSPIRATIONAL_QUOTES
from orionis.test import TestCase

class TestInspirationalQuotesType(TestCase):

    def testIsATuple(self) -> None:
        """
        Test that INSPIRATIONAL_QUOTES is a tuple.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(INSPIRATIONAL_QUOTES, tuple)

    def testIsNotEmpty(self) -> None:
        """
        Test that INSPIRATIONAL_QUOTES contains at least one entry.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertGreater(len(INSPIRATIONAL_QUOTES), 0)

    def testAllItemsAreDicts(self) -> None:
        """
        Test that every item in INSPIRATIONAL_QUOTES is a dict.

        Returns
        -------
        None
            This method does not return a value.
        """
        for idx, item in enumerate(INSPIRATIONAL_QUOTES):
            self.assertIsInstance(item, dict, msg=f"Item at index {idx} is not a dict")

    def testAllDictsHaveQuoteKey(self) -> None:
        """
        Test that every dict in INSPIRATIONAL_QUOTES has a 'quote' key.

        Returns
        -------
        None
            This method does not return a value.
        """
        for idx, item in enumerate(INSPIRATIONAL_QUOTES):
            self.assertIn(
                "quote",
                item,
                msg=f"Item at index {idx} is missing 'quote' key",
            )

    def testAllDictsHaveAuthorKey(self) -> None:
        """
        Test that every dict in INSPIRATIONAL_QUOTES has an 'author' key.

        Returns
        -------
        None
            This method does not return a value.
        """
        for idx, item in enumerate(INSPIRATIONAL_QUOTES):
            self.assertIn(
                "author",
                item,
                msg=f"Item at index {idx} is missing 'author' key",
            )

    def testAllQuoteValuesAreNonEmptyStrings(self) -> None:
        """
        Test that the 'quote' value in every dict is a non-empty string.

        Returns
        -------
        None
            This method does not return a value.
        """
        for idx, item in enumerate(INSPIRATIONAL_QUOTES):
            self.assertIsInstance(
                item["quote"],
                str,
                msg=f"Item at index {idx}: 'quote' is not a str",
            )
            self.assertGreater(
                len(item["quote"].strip()),
                0,
                msg=f"Item at index {idx}: 'quote' is empty",
            )

    def testAllAuthorValuesAreNonEmptyStrings(self) -> None:
        """
        Test that the 'author' value in every dict is a non-empty string.

        Returns
        -------
        None
            This method does not return a value.
        """
        for idx, item in enumerate(INSPIRATIONAL_QUOTES):
            self.assertIsInstance(
                item["author"],
                str,
                msg=f"Item at index {idx}: 'author' is not a str",
            )
            self.assertGreater(
                len(item["author"].strip()),
                0,
                msg=f"Item at index {idx}: 'author' is empty",
            )

    def testEachItemHasExactlyTwoKeys(self) -> None:
        """
        Test that each dict in INSPIRATIONAL_QUOTES has exactly 'quote' and 'author'.

        Returns
        -------
        None
            This method does not return a value.
        """
        for idx, item in enumerate(INSPIRATIONAL_QUOTES):
            self.assertEqual(
                set(item.keys()),
                {"quote", "author"},
                msg=f"Item at index {idx} has unexpected keys: {set(item.keys())}",
            )

    def testListContainsMoreThanTenQuotes(self) -> None:
        """
        Test that INSPIRATIONAL_QUOTES contains more than ten entries.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertGreater(len(INSPIRATIONAL_QUOTES), 10)

    def testNoDuplicateQuotes(self) -> None:
        """
        Test that no two entries share the same 'quote' text.

        Returns
        -------
        None
            This method does not return a value.
        """
        quotes_text = [item["quote"] for item in INSPIRATIONAL_QUOTES]
        unique_quotes = set(quotes_text)
        self.assertEqual(
            len(quotes_text),
            len(unique_quotes),
            msg="INSPIRATIONAL_QUOTES contains duplicate 'quote' entries",
        )
