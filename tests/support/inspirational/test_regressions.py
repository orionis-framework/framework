# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect fallback selection when an owned caller list changes."""

from orionis.support.inspirational.inspire import Inspire
from orionis.test import TestCase


class TestInspireRegressions(TestCase):
    """Exercise quote selection through the public constructor and method."""

    def testReturnFallbackAfterCallerClearsQuotes(self) -> None:
        """Return a usable fallback after the supplied list becomes empty."""
        quotes = [{"quote": "Keep learning.", "author": "Example"}]
        inspire = Inspire(quotes)
        quotes.clear()
        fallback = inspire.random()
        self.assertTrue(fallback["quote"])
        self.assertTrue(fallback["author"])
        replacement = {"quote": "Try again.", "author": "Example"}
        quotes.append(replacement)
        self.assertEqual(inspire.random(), replacement)
