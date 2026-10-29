from datetime import datetime
from inspect import iscoroutinefunction
from orionis.schemas import Schema
from orionis.schemas import constraints as constraints_module
from orionis.schemas import rules as rules_module
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.fields import Field
from orionis.schemas.rules.accepted import Accepted
from orionis.schemas.rules.after import After
from orionis.schemas.rules.between import Between
from orionis.schemas.rules.confirm_password import ConfirmPassword
from orionis.schemas.rules.greater_than_or_equal_field import GreaterThanOrEqualField
from orionis.schemas.rules.ip_address import IpAddress
from orionis.schemas.rules.uuid_string import Uuid
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

# Schema fields resolve their annotations at run time, so the metadata imports
# above must stay outside a type-checking block.
# ruff: noqa: TC001, TC003

# Identifier reused by the schema exercised through the validator.
_UUID_V4 = "9f8c1e2a-4b3d-4c5e-8a9b-0c1d2e3f4a5b"

class _Registration(Schema):
    terms: Field[str, Accepted()]
    ident: Field[str, Uuid(4)]
    host: Field[str, IpAddress()]
    quantity: Field[int, Between(1, 10)]
    minimum: int
    maximum: Field[int, GreaterThanOrEqualField("minimum")]
    password: str
    password_confirmation: Field[str, ConfirmPassword()]

class _Booking(Schema):
    start: datetime
    end: Field[datetime, After("start", message="End must follow start.")]

def _payload(**overrides: object) -> dict:
    """
    Build a valid registration payload with optional overrides.

    Parameters
    ----------
    **overrides : object
        Field values replacing the valid defaults.

    Returns
    -------
    dict
        Payload ready to be handed to the validator.
    """
    payload = {
        "terms": "yes",
        "ident": _UUID_V4,
        "host": "192.168.0.1",
        "quantity": 5,
        "minimum": 1,
        "maximum": 3,
        "password": "Secure1!",
        "password_confirmation": "Secure1!",
    }
    payload.update(overrides)
    return payload

class TestRulesThroughValidator(TestCase):

    async def testValidPayloadIsDecoded(self) -> None:
        """Return a typed instance when every custom rule passes.

        Validates that the rules do not reject a well-formed payload.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = await Validator.validate(_payload(), _Registration)
        self.assertEqual(instance.ident, _UUID_V4)
        self.assertEqual(instance.quantity, 5)

    async def testFailingRuleRaisesWithItsCode(self) -> None:
        """
        Verify that a failing rule exposes its code in validation errors.

        Returns
        -------
        None
            Assert the failure's field, rule code, and structured error details.
        """
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate(_payload(terms="no"), _Registration)
        self.assertEqual(ctx.exception.failure.rule, "accepted")
        self.assertEqual(ctx.exception.failure.field, "terms")
        self.assertEqual(ctx.exception.errors["terms"], [{
            "rule": "accepted", "message": ctx.exception.failure.message,
        }])

    async def testEveryRuleIsEvaluatedOnItsField(self) -> None:
        """
        Verify the expected rule code for each failing field.

        Returns
        -------
        None
            Assert each rule's field, code, and message in the reported errors.
        """
        cases = (
            ({"ident": "not-a-uuid"}, "ident", "uuid"),
            ({"host": "::1"}, "host", "ip"),
            ({"quantity": 99}, "quantity", "between"),
            ({"maximum": 0}, "maximum", "gte"),
            (
                {"password_confirmation": "Other1!"},
                "password_confirmation",
                "confirm_password",
            ),
        )
        for overrides, field, code in cases:
            with self.assertRaises(ValidationException) as ctx:
                await Validator.validate(_payload(**overrides), _Registration)
            self.assertEqual(ctx.exception.failure.field, field)
            self.assertEqual(ctx.exception.failure.rule, code)
            self.assertEqual(ctx.exception.errors[field], [{
                "rule": code, "message": ctx.exception.failure.message,
            }])

    async def testCrossFieldRuleReadsTheDecodedInstance(self) -> None:
        """Compare a field against a sibling resolved on the instance.

        Validates that the schema instance reaches the rule at run time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"start": "2024-01-01T00:00:00", "end": "2024-06-01T00:00:00"}
        self.assertIsNotNone(await Validator.validate(payload, _Booking))

    async def testCustomMessageOverridesTheDefault(self) -> None:
        """Report the message supplied when the rule was declared.

        Validates that per-instance messages reach the failure entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"start": "2024-06-01T00:00:00", "end": "2024-01-01T00:00:00"}
        with self.assertRaises(ValidationException) as ctx:
            await Validator.validate(payload, _Booking)
        self.assertEqual(ctx.exception.failure.message, "End must follow start.")

class TestRuleExports(TestCase):

    def testEveryBundledRuleHasOnlyAsyncEnforcement(self) -> None:
        """
        Require the same single asynchronous contract for every public rule.

        Returns
        -------
        None
            Assert a single asynchronous enforcement contract for every rule.
        """
        for name in rules_module.__all__:
            with self.subTest(rule=name):
                rule = getattr(rules_module, name)
                self.assertTrue(iscoroutinefunction(rule.enforce))
                self.assertFalse(hasattr(rule, "enforceAsync"))

    def testPackageExportsMatchItsPublicApi(self) -> None:
        """Resolve every name declared in the rules package ``__all__``.

        Validates that the package exposes exactly what it advertises.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in rules_module.__all__:
            self.assertTrue(hasattr(rules_module, name), name)

    def testConstraintsReexportEveryRule(self) -> None:
        """Re-export every rule from the constraints module.

        Validates that both entry points expose the same objects.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in rules_module.__all__:
            self.assertIn(name, constraints_module.__all__)
            self.assertIs(
                getattr(constraints_module, name),
                getattr(rules_module, name),
            )
