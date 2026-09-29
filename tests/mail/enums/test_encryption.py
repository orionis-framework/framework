from enum import StrEnum
from orionis.mail.enums.encryption import MailEncryption
from orionis.test import TestCase

class TestMailEncryption(TestCase):

    def testDeclaresTheThreeSupportedModes(self) -> None:
        """Expose exactly the transport security modes of the SMTP driver.

        Validates that no implicit or opportunistic mode exists.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(
            [member.value for member in MailEncryption],
            ["tls", "ssl", "none"],
        )

    def testMembersCompareEqualToConfiguredStrings(self) -> None:
        """Keep members interchangeable with normalized configuration values.

        Validates that a settings value and a member are the same thing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(MailEncryption, StrEnum))
        self.assertEqual(MailEncryption.TLS, "tls")
        self.assertEqual(MailEncryption.SSL, "ssl")
        self.assertEqual(MailEncryption.NONE, "none")

    def testLooksUpMembersByValue(self) -> None:
        """Resolve a member from a normalized configuration string.

        Validates that an unsupported mode is rejected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(MailEncryption("ssl"), MailEncryption.SSL)
        with self.assertRaises(ValueError):
            MailEncryption("starttls")
