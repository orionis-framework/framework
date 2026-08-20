from types import SimpleNamespace
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.rule import Rule
from orionis.schemas.rules.confirm_password import ConfirmPassword
from orionis.schemas.rules.strong_password import StrongPassword
from orionis.test import TestCase

# Sample values shared by the ConfirmPassword tests.
_CREDENTIAL = "Secure1!"
_OTHER = "Other1!"

# ---------------------------------------------------------------------------
# Minimal concrete Rule subclass for testing the abstract base
# ---------------------------------------------------------------------------

class _AlwaysValidRule(Rule):
    """Concrete Rule that always passes."""

    __code__ = "always_valid"
    __message__ = "Should not appear."

    def enforce(
        self,
        _field: str,
        _value: object,
        _instance: object,
    ) -> bool:
        return True

class _AlwaysInvalidRule(Rule):
    """Concrete Rule that always fails."""

    __code__ = "always_invalid"
    __message__ = "Value is always invalid."

    def enforce(
        self,
        _field: str,
        _value: object,
        _instance: object,
    ) -> bool:
        return False

class TestRule(TestCase):

    def testEnforceNotImplementedOnBase(self) -> None:
        """
        Raise NotImplementedError when enforce is called on the base Rule.

        Validates that the base class enforce method raises
        NotImplementedError as documented.
        """
        class _Stub(Rule):
            def enforce(
                self,
                field: str,
                value: object,
                instance: object,
            ) -> bool:
                return super().enforce(field, value, instance)  # type: ignore[misc]

        stub = _Stub()
        with self.assertRaises(NotImplementedError):
            stub.enforce("f", "v", object())

    def testValidateReturnsNoneOnSuccess(self) -> None:
        """
        Return None from validate when enforce returns True.

        Validates that a passing rule produces no ValidationFailure.
        """
        rule = _AlwaysValidRule()
        result = rule.validate("field", "any_value", object())
        self.assertIsNone(result)

    def testValidateReturnsFailureOnFail(self) -> None:
        """
        Return ValidationFailure from validate when enforce returns False.

        Validates that a failing rule wraps the error as a ValidationFailure
        with the correct field and rule code.
        """
        rule = _AlwaysInvalidRule()
        result = rule.validate("age", 0, object())
        self.assertIsInstance(result, ValidationFailure)
        self.assertEqual(result.field, "age")
        self.assertEqual(result.rule, "always_invalid")

    def testValidateUsesDefaultMessageFromClass(self) -> None:
        """
        Use the class-level __message__ when no custom message is supplied.

        Validates that the failure message falls back to __message__ when
        the Rule is instantiated without a custom message.
        """
        rule = _AlwaysInvalidRule()
        result = rule.validate("f", "v", object())
        self.assertIsNotNone(result)
        self.assertEqual(result.message, "Value is always invalid.")  # type: ignore[union-attr]

    def testValidateUsesCustomMessageWhenProvided(self) -> None:
        """
        Use the custom message when one is provided at construction time.

        Validates that the custom message overrides the class-level
        __message__ in the ValidationFailure.
        """
        custom = "Custom error."
        rule = _AlwaysInvalidRule(message=custom)
        result = rule.validate("f", "v", object())
        self.assertIsNotNone(result)
        self.assertEqual(result.message, custom)  # type: ignore[union-attr]

    def testResolvedCodeUsesClassAttribute(self) -> None:
        """
        Confirm the resolved rule code matches the class __code__ attribute.

        Validates that _resolved_code is populated from the class-level
        __code__ string.
        """
        rule = _AlwaysInvalidRule()
        result = rule.validate("x", 1, object())
        self.assertIsNotNone(result)
        self.assertEqual(result.rule, "always_invalid")  # type: ignore[union-attr]

    def testRuleWithNoMessageDefaultsToNone(self) -> None:
        """
        Leave message as None when __message__ is not defined on the class.

        Validates that Rules without a __message__ attribute produce
        failures with a None message value.
        """
        class _NoMsg(Rule):
            __code__ = "no_msg"

            def enforce(
                self,
                _field: str,
                _value: object,
                _instance: object,
            ) -> bool:
                return False

        rule = _NoMsg()
        result = rule.validate("f", "v", object())
        self.assertIsNotNone(result)
        self.assertIsNone(result.message)  # type: ignore[union-attr]

class TestStrongPassword(TestCase):

    def testValidPasswordPassesEnforce(self) -> None:
        """
        Return True for a password meeting all requirements.

        Validates that a password with >= 8 characters, at least one
        uppercase, one lowercase, and one digit passes enforce.
        """
        rule = StrongPassword()
        self.assertTrue(rule.enforce("password", "Secure1!", object()))

    def testTooShortPasswordFails(self) -> None:
        """
        Return False for a password shorter than the minimum length.

        Validates that a password with fewer than 8 characters fails
        enforce regardless of character variety.
        """
        rule = StrongPassword()
        self.assertFalse(rule.enforce("password", "Ab1!", object()))

    def testNoUppercaseFails(self) -> None:
        """
        Return False for a password without an uppercase letter.

        Validates that a password missing an uppercase character fails
        enforce even when it meets the length and digit requirements.
        """
        rule = StrongPassword()
        self.assertFalse(rule.enforce("password", "abcdef12", object()))

    def testNoLowercaseFails(self) -> None:
        """
        Return False for a password without a lowercase letter.

        Validates that a password missing a lowercase character fails
        enforce even when it meets the length and digit requirements.
        """
        rule = StrongPassword()
        self.assertFalse(rule.enforce("password", "ABCDEF12", object()))

    def testNoDigitFails(self) -> None:
        """
        Return False for a password without a digit.

        Validates that a password missing any digit fails enforce even
        when it meets the length and character case requirements.
        """
        rule = StrongPassword()
        self.assertFalse(rule.enforce("password", "Abcdefgh", object()))

    def testNonStringValuePassesEnforce(self) -> None:
        """
        Return True when the value is not a string.

        Validates that enforce skips validation for non-string values
        and treats them as passing (type checking is delegated elsewhere).
        """
        rule = StrongPassword()
        self.assertTrue(rule.enforce("password", 12345, object()))
        self.assertTrue(rule.enforce("password", None, object()))

    def testExactlyEightCharsPassesWhenRequirementsMet(self) -> None:
        """
        Return True for a password of exactly 8 characters meeting all rules.

        Validates that the minimum length boundary (8 characters) is
        treated as inclusive.
        """
        rule = StrongPassword()
        self.assertTrue(rule.enforce("password", "Aa000000", object()))

    def testSevenCharsFails(self) -> None:
        """
        Return False for a password of exactly 7 characters.

        Validates that the minimum length boundary is exclusive for
        lengths below 8.
        """
        rule = StrongPassword()
        self.assertFalse(rule.enforce("password", "Aa00000", object()))

    def testValidateReturnsNoneForValidPassword(self) -> None:
        """
        Return None from validate for a strong password.

        Validates the full validate path returns no failure for a
        password that satisfies all StrongPassword requirements.
        """
        rule = StrongPassword()
        result = rule.validate("pwd", "Secure1!", object())
        self.assertIsNone(result)

    def testValidateReturnsFailureForWeakPassword(self) -> None:
        """
        Return ValidationFailure from validate for a weak password.

        Validates that validate produces a failure with the expected
        rule code when the password fails enforce.
        """
        rule = StrongPassword()
        result = rule.validate("pwd", "weakpass", object())
        self.assertIsInstance(result, ValidationFailure)
        self.assertEqual(result.rule, "strong_password")

    def testCodeAttributeIsStrongPassword(self) -> None:
        """
        Confirm the __code__ class attribute is 'strong_password'.

        Validates that the rule code matches the expected string used
        in ValidationFailure.rule.
        """
        self.assertEqual(StrongPassword.__code__, "strong_password")

class TestConfirmPassword(TestCase):

    def testMatchingConfirmationPasses(self) -> None:
        """
        Return True when the confirmation equals the password field.

        Validates the success path against the default sibling field.
        """
        rule = ConfirmPassword()
        instance = SimpleNamespace(password=_CREDENTIAL)
        self.assertTrue(rule.enforce("password_confirmation", _CREDENTIAL, instance))

    def testMismatchedConfirmationFails(self) -> None:
        """
        Return False when the confirmation differs from the password.

        Validates that any difference, including case, rejects the value.
        """
        rule = ConfirmPassword()
        instance = SimpleNamespace(password=_CREDENTIAL)
        self.assertFalse(rule.enforce("password_confirmation", _OTHER, instance))
        self.assertFalse(rule.enforce("password_confirmation", "secure1!", instance))

    def testCustomSiblingFieldIsCompared(self) -> None:
        """
        Compare against the sibling field supplied at construction time.

        Validates that the default field name can be overridden.
        """
        rule = ConfirmPassword("new_password")
        instance = SimpleNamespace(new_password=_CREDENTIAL, password=_OTHER)
        self.assertTrue(rule.enforce("confirmation", _CREDENTIAL, instance))
        self.assertFalse(rule.enforce("confirmation", _OTHER, instance))

    def testMissingSiblingPasses(self) -> None:
        """
        Return True when the compared field is absent from the instance.

        Validates that type reporting is delegated to the type layer.
        """
        rule = ConfirmPassword()
        empty = SimpleNamespace()
        self.assertTrue(rule.enforce("password_confirmation", _CREDENTIAL, empty))

    def testPresentNoneSiblingIsStillCompared(self) -> None:
        """
        Compare a sibling field that is present and holds None.

        Validates that an absent field is distinguished from a None value.
        """
        rule = ConfirmPassword()
        instance = SimpleNamespace(password=None)
        self.assertTrue(rule.enforce("password_confirmation", None, instance))
        self.assertFalse(rule.enforce("password_confirmation", _CREDENTIAL, instance))

    def testEmptyFieldNameRaises(self) -> None:
        """
        Raise ValueError when no sibling field name is supplied.

        Validates that the rule refuses a configuration with no target.
        """
        with self.assertRaises(ValueError):
            ConfirmPassword("")

    def testValidateReturnsNoneForMatchingValue(self) -> None:
        """
        Return None from validate when both values match.

        Validates the full validate path for the success case.
        """
        rule = ConfirmPassword()
        instance = SimpleNamespace(password=_CREDENTIAL)
        self.assertIsNone(rule.validate("password_confirmation", _CREDENTIAL, instance))

    def testValidateReturnsFailureWithCustomMessage(self) -> None:
        """
        Return a ValidationFailure carrying the overridden message.

        Validates the rule code and the custom message resolution.
        """
        rule = ConfirmPassword(message="Passwords do not match.")
        instance = SimpleNamespace(password=_CREDENTIAL)
        result = rule.validate("password_confirmation", _OTHER, instance)
        self.assertIsInstance(result, ValidationFailure)
        self.assertEqual(result.rule, "confirm_password")
        self.assertEqual(result.message, "Passwords do not match.")

    def testCodeAttributeIsConfirmPassword(self) -> None:
        """
        Confirm the __code__ class attribute is 'confirm_password'.

        Validates that the rule code matches the expected string used
        in ValidationFailure.rule.
        """
        self.assertEqual(ConfirmPassword.__code__, "confirm_password")
