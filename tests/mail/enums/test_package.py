from orionis.mail import enums as enums_package
from orionis.mail.enums.encryption import MailEncryption
from orionis.mail.enums.status import MailStatus
from orionis.test import TestCase

class TestMailEnumsPackage(TestCase):

    def testDeclaresBothEnumerationsAsPublicExports(self) -> None:
        """
        Expose the encryption and status enumerations from the package.

        Validates the public surface consumers may import.
        """
        self.assertEqual(
            enums_package.__all__,
            ["MailEncryption", "MailStatus"],
        )

    def testReExportsBindEachEnumeration(self) -> None:
        """
        Bind every exported name to its real enumeration.

        Validates that the re-exports are not shadowing aliases.
        """
        self.assertIs(enums_package.MailEncryption, MailEncryption)
        self.assertIs(enums_package.MailStatus, MailStatus)
