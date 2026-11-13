# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect normalized flash messages and native runtime session metadata."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import get_type_hints

from orionis.session.contracts.session import ISession
from orionis.session.entities.record import SessionRecord
from orionis.session.flash import apply_flash, normalize_errors
from orionis.test import TestCase


class _ValidationFailure(Exception):
    """Expose one validation message through the documented failure protocol."""

    def __init__(self, message: object) -> None:
        """Retain a field and its message without coercing the caller's value.

        Parameters
        ----------
        message : object
            Scalar message to normalize into a string.

        Returns
        -------
        None
            No return value.
        """
        super().__init__("Invalid quantity")
        self.failure = SimpleNamespace(field="quantity", message=message)


class TestSessionFlashRegressions(TestCase):
    """Keep supported validation inputs and public annotations consistent."""

    def testFailureMessagesAreStringsAndPreserveFalsyScalars(self) -> None:
        """Normalize scalar messages equally through a mapping or failure object.

        Returns
        -------
        None
            No return value.
        """
        for message in (0, False, 23, Decimal("1.25")):
            with self.subTest(message=message):
                expected = normalize_errors({"quantity": message})
                self.assertEqual(expected, {"quantity": [str(message)]})
                self.assertEqual(
                    normalize_errors(_ValidationFailure(message)),
                    expected,
                )
        self.assertEqual(normalize_errors(_ValidationFailure(None)), {"quantity": [""]})

    def testRecordAndFlashAnnotationsResolveAtRuntime(self) -> None:
        """Resolve persistent record and flash types without caller namespaces.

        Returns
        -------
        None
            No return value.
        """
        for target in (SessionRecord, SessionRecord.__init__):
            with self.subTest(target=target.__name__):
                self.assertIs(get_type_hints(target)["expires_at"], datetime)
        with self.subTest(target="apply_flash"):
            self.assertIs(get_type_hints(apply_flash)["session"], ISession)
