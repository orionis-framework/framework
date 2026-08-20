from __future__ import annotations
from types import MappingProxyType
from typing import Any
from orionis.session.flash import (
    ERRORS_KEY,
    OLD_INPUT_KEY,
    PREVIOUS_URL_KEY,
    SENSITIVE_INPUT_FIELDS,
    apply_flash,
    filter_input,
    normalize_errors,
    queue_bag,
)
from orionis.session.session import Session
from orionis.test import TestCase

class _FakeFailure:
    """Minimal stand-in for a single validation failure."""

    def __init__(self, field: str | None, message: str | None) -> None:
        self.field = field
        self.message = message

class _FakeValidationException(Exception):
    """Duck-typed validation exception exposing errors and/or failure."""

    def __init__(
        self,
        errors: object | None = None,
        failure: _FakeFailure | None = None,
    ) -> None:
        super().__init__("invalid")
        if errors is not None:
            self.errors = errors
        if failure is not None:
            self.failure = failure

class TestFlashConstants(TestCase):
    """Unit tests for the reserved keys owned by the session layer."""

    def testReservedKeysAreDistinct(self) -> None:
        """
        Keep every reserved session key unique.

        Validates that the old-input, errors and previous-url bags can
        never overwrite one another inside the same payload.
        """
        keys = {OLD_INPUT_KEY, ERRORS_KEY, PREVIOUS_URL_KEY}
        self.assertEqual(len(keys), 3)

    def testSensitiveFieldsCoverCredentialInputs(self) -> None:
        """
        Blacklist every credential-like form field.

        Validates that passwords and CSRF tokens are declared as
        sensitive so they are never repopulated into a form.
        """
        for field in ("password", "password_confirmation", "csrf_token"):
            self.assertIn(field, SENSITIVE_INPUT_FIELDS)

class TestFilterInput(TestCase):
    """Unit tests for filter_input()."""

    def testDropsSensitiveFields(self) -> None:
        """
        Remove credential fields from the payload.

        Validates that a submitted password never reaches the flash bag.
        """
        result = filter_input({"email": "a@b.c", "password": "secret"})
        self.assertEqual(result, {"email": "a@b.c"})

    def testKeepsNonSensitiveFields(self) -> None:
        """
        Preserve every non-credential field verbatim.

        Validates that ordinary form values survive the filtering pass.
        """
        payload = {"email": "a@b.c", "remember": True}
        self.assertEqual(filter_input(payload), payload)

    def testReturnsIndependentCopy(self) -> None:
        """
        Never alias the caller's mapping.

        Validates that mutating the result leaves the original payload
        untouched, both on the fast and the filtered path.
        """
        payload = {"email": "a@b.c"}
        result = filter_input(payload)
        result["email"] = "changed"
        self.assertEqual(payload["email"], "a@b.c")

    def testDropsEverySensitiveField(self) -> None:
        """
        Remove all blacklisted fields at once.

        Validates that a payload made exclusively of credentials yields
        an empty mapping.
        """
        payload = dict.fromkeys(SENSITIVE_INPUT_FIELDS, "x")
        self.assertEqual(filter_input(payload), {})

    def testEmptyPayloadReturnsEmptyDict(self) -> None:
        """
        Handle an empty submission without failing.

        Validates that the disjoint fast path tolerates empty mappings.
        """
        self.assertEqual(filter_input({}), {})

    def testAcceptsAnyMappingOnTheFastPath(self) -> None:
        """
        Copy a read-only mapping into a plain dictionary.

        Validates that the credential-free fast path does not assume the
        payload is a mutable dict.
        """
        payload = MappingProxyType({"email": "a@b.c"})
        result = filter_input(payload)
        self.assertEqual(result, {"email": "a@b.c"})
        self.assertIsInstance(result, dict)

    def testAcceptsAnyMappingOnTheFilteredPath(self) -> None:
        """
        Filter a read-only mapping containing credentials.

        Validates that the slow path also accepts non-dict mappings.
        """
        payload = MappingProxyType({"email": "a@b.c", "password": "x"})
        self.assertEqual(filter_input(payload), {"email": "a@b.c"})

class TestNormalizeErrors(TestCase):
    """Unit tests for normalize_errors()."""

    def testStringValueBecomesSingleItemList(self) -> None:
        """
        Wrap a single message into a list.

        Validates that the ``{field: [message]}`` shape is always
        produced regardless of the caller's input style.
        """
        self.assertEqual(
            normalize_errors({"email": "required"}),
            {"email": ["required"]},
        )

    def testListValueIsStringified(self) -> None:
        """
        Coerce every item of a sequence to a string.

        Validates that non-string messages are rendered before storage.
        """
        self.assertEqual(
            normalize_errors({"age": ["too small", 42]}),
            {"age": ["too small", "42"]},
        )

    def testTupleValueIsSupported(self) -> None:
        """
        Accept a tuple of messages.

        Validates that immutable sequences are treated like lists.
        """
        self.assertEqual(
            normalize_errors({"a": ("x", "y")}),
            {"a": ["x", "y"]},
        )

    def testFrozensetValueIsSupported(self) -> None:
        """
        Accept a frozenset of messages.

        Validates that set-like containers are expanded instead of being
        stringified as a whole.
        """
        self.assertEqual(normalize_errors({"a": frozenset({"x"})}), {"a": ["x"]})

    def testScalarValueIsStringified(self) -> None:
        """
        Render a non-sequence value as a single message.

        Validates that arbitrary objects still produce a valid bag.
        """
        self.assertEqual(normalize_errors({"n": 10}), {"n": ["10"]})

    def testExceptionWithErrorsMappingIsPreferred(self) -> None:
        """
        Read the full error bag from a validation exception.

        Validates that every failing field is reported, not just the
        first one.
        """
        exc = _FakeValidationException(errors={"a": ["x"], "b": ["y", "z"]})
        self.assertEqual(normalize_errors(exc), {"a": ["x"], "b": ["y", "z"]})

    def testExceptionWithSingleFailureIsSupported(self) -> None:
        """
        Fall back to a single failure attribute.

        Validates compatibility with exceptions exposing only ``failure``.
        """
        exc = _FakeValidationException(failure=_FakeFailure("email", "invalid"))
        self.assertEqual(normalize_errors(exc), {"email": ["invalid"]})

    def testNonMappingErrorsAttributeFallsBackToFailure(self) -> None:
        """
        Ignore an ``errors`` attribute that is not a mapping.

        Validates that the failure attribute still drives the result
        when the richer bag is unusable.
        """
        exc = _FakeValidationException(
            errors=["not", "a", "mapping"],
            failure=_FakeFailure("email", "invalid"),
        )
        self.assertEqual(normalize_errors(exc), {"email": ["invalid"]})

    def testFailureWithoutFieldOrMessageYieldsEmptyStrings(self) -> None:
        """
        Tolerate a failure exposing empty attributes.

        Validates that ``None`` values are coerced to empty strings
        instead of leaking into the flash bag.
        """
        exc = _FakeValidationException(failure=_FakeFailure(None, None))
        self.assertEqual(normalize_errors(exc), {"": [""]})

    def testExceptionWithoutErrorBagRaisesTypeError(self) -> None:
        """
        Reject an exception carrying no error information.

        Validates that an unrelated exception cannot be flashed as if it
        were a validation failure.
        """
        with self.assertRaises(TypeError):
            normalize_errors(_FakeValidationException())

    def testUnsupportedPayloadRaisesTypeError(self) -> None:
        """
        Reject payloads that are neither mappings nor exceptions.

        Validates that misuse fails loudly instead of flashing garbage.
        """
        with self.assertRaises(TypeError):
            normalize_errors("boom")

    def testReadOnlyMappingIsSupported(self) -> None:
        """
        Accept any mapping implementation as the error bag.

        Validates that the normaliser never assumes a mutable dict.
        """
        self.assertEqual(
            normalize_errors(MappingProxyType({"email": "required"})),
            {"email": ["required"]},
        )

class TestQueueBag(TestCase):
    """Unit tests for queue_bag()."""

    def testCreatesBagWhenAbsent(self) -> None:
        """
        Create the reserved bag on first use.

        Validates that the stored bag is a copy of the supplied values.
        """
        pending: dict[str, Any] = {}
        values = {"email": "a@b.c"}
        queue_bag(pending, OLD_INPUT_KEY, values)
        self.assertEqual(pending[OLD_INPUT_KEY], values)
        self.assertIsNot(pending[OLD_INPUT_KEY], values)

    def testMergesIntoExistingBag(self) -> None:
        """
        Merge new entries into an already queued bag.

        Validates that successive calls accumulate instead of replacing.
        """
        pending: dict[str, Any] = {OLD_INPUT_KEY: {"a": 1}}
        queue_bag(pending, OLD_INPUT_KEY, {"b": 2})
        self.assertEqual(pending[OLD_INPUT_KEY], {"a": 1, "b": 2})

    def testReplacesNonDictValue(self) -> None:
        """
        Overwrite a previously stored non-mapping value.

        Validates that a corrupted slot is rebuilt as a proper bag.
        """
        pending: dict[str, Any] = {ERRORS_KEY: "oops"}
        queue_bag(pending, ERRORS_KEY, {"a": ["x"]})
        self.assertEqual(pending[ERRORS_KEY], {"a": ["x"]})

class TestApplyFlash(TestCase):
    """Unit tests for apply_flash()."""

    def testRoutesOldInputThroughFlashInput(self) -> None:
        """
        Send the reserved input bag through flashInput().

        Validates that sensitive fields are stripped even when the data
        arrives as a raw pending payload.
        """
        session = Session()
        apply_flash(
            session,
            {OLD_INPUT_KEY: {"email": "a@b.c", "password": "secret"}},
        )
        self.assertEqual(session.getOldInput("email"), "a@b.c")
        self.assertIsNone(session.getOldInput("password"))

    def testRoutesErrorsThroughFlashErrors(self) -> None:
        """
        Send the reserved errors bag through flashErrors().

        Validates that messages are normalised into lists.
        """
        session = Session()
        apply_flash(session, {ERRORS_KEY: {"email": "required"}})
        self.assertEqual(session.getErrors(), {"email": ["required"]})

    def testRoutesPlainKeysThroughFlash(self) -> None:
        """
        Flash ordinary keys unchanged.

        Validates that status messages keep their original value.
        """
        session = Session()
        apply_flash(session, {"success": "Saved"})
        self.assertEqual(session.getFlash("success"), "Saved")

    def testReservedBagsMergeWithExistingFlash(self) -> None:
        """
        Merge reserved bags instead of replacing them.

        Validates that a payload applied after a direct flashInput()
        call keeps both sets of fields.
        """
        session = Session()
        session.flashInput({"email": "a@b.c"})
        apply_flash(session, {OLD_INPUT_KEY: {"name": "Ada"}})
        self.assertEqual(session.getOldInput("email"), "a@b.c")
        self.assertEqual(session.getOldInput("name"), "Ada")

    def testEmptyPayloadLeavesSessionUntouched(self) -> None:
        """
        Ignore an empty pending payload.

        Validates that no write occurs and the session stays lazy.
        """
        session = Session()
        apply_flash(session, {})
        self.assertFalse(session.started)

    def testRoutesExceptionErrorsThroughFlashErrors(self) -> None:
        """
        Normalise a validation exception queued as the errors bag.

        Validates that responses may queue the raised exception itself
        instead of a pre-built mapping.
        """
        session = Session()
        apply_flash(
            session,
            {ERRORS_KEY: _FakeValidationException({"email": ["invalid"]})},
        )
        self.assertEqual(session.getErrors(), {"email": ["invalid"]})

    def testPreviousUrlKeyIsFlashedVerbatim(self) -> None:
        """
        Treat the previous-url key as an ordinary flash entry.

        Validates that only the input and error bags receive special
        routing.
        """
        session = Session()
        apply_flash(session, {PREVIOUS_URL_KEY: "http://orionis.test/login"})
        self.assertEqual(
            session.getFlash(PREVIOUS_URL_KEY),
            "http://orionis.test/login",
        )
