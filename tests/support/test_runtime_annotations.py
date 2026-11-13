# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect public concurrency annotations used by dependency reflection."""

from typing import get_type_hints
from orionis.support.concurrency import (
    BoundedExecutor,
    close_abandoned_awaitable,
    complete_on_cancel,
    threaded,
    wait_for_completion,
)
from orionis.test import TestCase


class TestConcurrencyAnnotations(TestCase):
    """Resolve annotations through the same runtime API as consumers."""

    def testResolvePublicAnnotations(self) -> None:
        """Resolve callable and awaitable types without caller namespace patches."""
        for callback in (
            BoundedExecutor.run,
            close_abandoned_awaitable,
            complete_on_cancel,
            threaded,
            wait_for_completion,
        ):
            with self.subTest(callback=callback.__qualname__):
                self.assertIn("return", get_type_hints(callback))
