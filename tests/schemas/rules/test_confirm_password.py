from types import SimpleNamespace
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.rules.confirm_password import ConfirmPassword
from orionis.test import TestCase

# Sample values shared by the tests; neutral names avoid credential lint rules.
_CREDENTIAL = "Secure1!"
_OTHER = "Other1!"

class TestConfirmPasswordEnforce(TestCase):

    async def testMatchingConfirmationPasses(self) -> None:
        """Accept a confirmation equal to the compared field.

        Validates the success path against the default sibling field.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = SimpleNamespace(password=_CREDENTIAL)
        rule = ConfirmPassword()
        self.assertTrue(
            await rule.enforce("password_confirmation", _CREDENTIAL, instance),
        )

    async def testMismatchedConfirmationFails(self) -> None:
        """Reject a confirmation differing from the compared field.

        Validates that any difference, including case, is rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = SimpleNamespace(password=_CREDENTIAL)
        rule = ConfirmPassword()
        self.assertFalse(await rule.enforce("password_confirmation", _OTHER, instance))
        self.assertFalse(
            await rule.enforce("password_confirmation", "secure1!", instance),
        )

    async def testCustomSiblingFieldIsCompared(self) -> None:
        """Compare against the sibling field supplied at construction time.

        Validates that the default field name can be overridden.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = ConfirmPassword("new_password")
        instance = SimpleNamespace(new_password=_CREDENTIAL, password=_OTHER)
        self.assertTrue(await rule.enforce("confirmation", _CREDENTIAL, instance))
        self.assertFalse(await rule.enforce("confirmation", _OTHER, instance))

    async def testMissingSiblingPasses(self) -> None:
        """Accept the value when the compared field is absent.

        Validates that a failed sibling conversion is not reported twice.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = ConfirmPassword()
        self.assertTrue(
            await rule.enforce("password_confirmation", _CREDENTIAL, SimpleNamespace()),
        )

    async def testPresentNoneSiblingIsStillCompared(self) -> None:
        """Compare a sibling field that is present and holds None.

        Validates that an absent field is distinguished from a None value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = SimpleNamespace(password=None)
        rule = ConfirmPassword()
        self.assertTrue(await rule.enforce("password_confirmation", None, instance))
        self.assertFalse(
            await rule.enforce("password_confirmation", _CREDENTIAL, instance),
        )

    def testEmptyFieldNameRaises(self) -> None:
        """Raise ValueError when no sibling field name is supplied.

        Validates that the rule refuses a configuration with no target.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            ConfirmPassword("")

class TestConfirmPasswordValidate(TestCase):

    async def testValidateReturnsNoneForMatchingValue(self) -> None:
        """Return None when both values match.

        Validates the success path of the inherited validate method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = SimpleNamespace(password=_CREDENTIAL)
        rule = ConfirmPassword()
        self.assertIsNone(
            await rule.validate("password_confirmation", _CREDENTIAL, instance),
        )

    async def testValidateReturnsFailureWithCustomMessage(self) -> None:
        """Return a ValidationFailure carrying the overridden message.

        Validates the rule code and the custom message resolution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = SimpleNamespace(password=_CREDENTIAL)
        rule = ConfirmPassword(message="Passwords do not match.")
        result = await rule.validate("password_confirmation", _OTHER, instance)
        self.assertIsInstance(result, ValidationFailure)
        self.assertEqual(result.rule, "confirm_password")
        self.assertEqual(result.message, "Passwords do not match.")

    def testRuleCodeIsConfirmPassword(self) -> None:
        """Expose ``confirm_password`` as the rule code.

        Validates the identifier surfaced through ValidationFailure.rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ConfirmPassword.__code__, "confirm_password")
