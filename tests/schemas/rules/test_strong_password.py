from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.rules.strong_password import StrongPassword
from orionis.test import TestCase

class TestStrongPasswordEnforce(TestCase):

    def testValidPasswordPasses(self) -> None:
        """
        Accept a password meeting every requirement.

        Validates that length, case variety and digits together satisfy
        the rule.
        """
        self.assertTrue(StrongPassword().enforce("password", "Secure1!", object()))

    def testTooShortPasswordFails(self) -> None:
        """
        Reject a password shorter than the minimum length.

        Validates that character variety alone is not enough.
        """
        self.assertFalse(StrongPassword().enforce("password", "Ab1!", object()))

    def testMissingUppercaseFails(self) -> None:
        """
        Reject a password without an uppercase letter.

        Validates the uppercase requirement in isolation.
        """
        self.assertFalse(StrongPassword().enforce("password", "abcdef12", object()))

    def testMissingLowercaseFails(self) -> None:
        """
        Reject a password without a lowercase letter.

        Validates the lowercase requirement in isolation.
        """
        self.assertFalse(StrongPassword().enforce("password", "ABCDEF12", object()))

    def testMissingDigitFails(self) -> None:
        """
        Reject a password without a digit.

        Validates the digit requirement in isolation.
        """
        self.assertFalse(StrongPassword().enforce("password", "Abcdefgh", object()))

    def testNonStringValuesArePassedThrough(self) -> None:
        """
        Accept values that are not strings.

        Validates that type reporting is delegated to the type layer.
        """
        rule = StrongPassword()
        self.assertTrue(rule.enforce("password", 12345, object()))
        self.assertTrue(rule.enforce("password", None, object()))

    def testMinimumLengthBoundaryIsInclusive(self) -> None:
        """
        Accept a password of exactly the minimum length.

        Validates that the boundary is inclusive on the accepted side.
        """
        self.assertTrue(StrongPassword().enforce("password", "Aa000000", object()))

    def testBelowMinimumLengthIsRejected(self) -> None:
        """
        Reject a password one character below the minimum length.

        Validates that the boundary is exclusive on the rejected side.
        """
        self.assertFalse(StrongPassword().enforce("password", "Aa00000", object()))

class TestStrongPasswordValidate(TestCase):

    def testValidateReturnsNoneForStrongPassword(self) -> None:
        """
        Return None when the password satisfies the rule.

        Validates the success path of the inherited validate method.
        """
        self.assertIsNone(StrongPassword().validate("pwd", "Secure1!", object()))

    def testValidateReturnsFailureForWeakPassword(self) -> None:
        """
        Return a ValidationFailure for a rejected password.

        Validates the rule code carried by the reported failure.
        """
        result = StrongPassword().validate("pwd", "weakpass", object())
        self.assertIsInstance(result, ValidationFailure)
        self.assertEqual(result.rule, "strong_password")

    def testRuleCodeIsStrongPassword(self) -> None:
        """
        Expose ``strong_password`` as the rule code.

        Validates the identifier surfaced through ValidationFailure.rule.
        """
        self.assertEqual(StrongPassword.__code__, "strong_password")
