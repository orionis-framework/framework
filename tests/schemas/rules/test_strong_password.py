from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.rules.strong_password import StrongPassword
from orionis.test import TestCase

class TestStrongPasswordEnforce(TestCase):

    async def testValidPasswordPasses(self) -> None:
        """Accept a password meeting every requirement.

        Validates that length, case variety and digits together satisfy
        the rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            await StrongPassword().enforce("password", "Secure1!", object()),
        )

    async def testTooShortPasswordFails(self) -> None:
        """Reject a password shorter than the minimum length.

        Validates that character variety alone is not enough.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(await StrongPassword().enforce("password", "Ab1!", object()))

    async def testMissingUppercaseFails(self) -> None:
        """Reject a password without an uppercase letter.

        Validates the uppercase requirement in isolation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(
            await StrongPassword().enforce("password", "abcdef12", object()),
        )

    async def testMissingLowercaseFails(self) -> None:
        """Reject a password without a lowercase letter.

        Validates the lowercase requirement in isolation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(
            await StrongPassword().enforce("password", "ABCDEF12", object()),
        )

    async def testMissingDigitFails(self) -> None:
        """Reject a password without a digit.

        Validates the digit requirement in isolation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(
            await StrongPassword().enforce("password", "Abcdefgh", object()),
        )

    async def testNonStringValuesArePassedThrough(self) -> None:
        """Accept values that are not strings.

        Validates that type reporting is delegated to the type layer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = StrongPassword()
        self.assertTrue(await rule.enforce("password", 12345, object()))
        self.assertTrue(await rule.enforce("password", None, object()))

    async def testMinimumLengthBoundaryIsInclusive(self) -> None:
        """Accept a password of exactly the minimum length.

        Validates that the boundary is inclusive on the accepted side.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(
            await StrongPassword().enforce("password", "Aa000000", object()),
        )

    async def testBelowMinimumLengthIsRejected(self) -> None:
        """Reject a password one character below the minimum length.

        Validates that the boundary is exclusive on the rejected side.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(
            await StrongPassword().enforce("password", "Aa00000", object()),
        )

class TestStrongPasswordValidate(TestCase):

    async def testValidateReturnsNoneForStrongPassword(self) -> None:
        """Return None when the password satisfies the rule.

        Validates the success path of the inherited validate method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(await StrongPassword().validate("pwd", "Secure1!", object()))

    async def testValidateReturnsFailureForWeakPassword(self) -> None:
        """Return a ValidationFailure for a rejected password.

        Validates the rule code carried by the reported failure.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await StrongPassword().validate("pwd", "weakpass", object())
        self.assertIsInstance(result, ValidationFailure)
        self.assertEqual(result.rule, "strong_password")

    def testRuleCodeIsStrongPassword(self) -> None:
        """Expose ``strong_password`` as the rule code.

        Validates the identifier surfaced through ValidationFailure.rule.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(StrongPassword.__code__, "strong_password")
