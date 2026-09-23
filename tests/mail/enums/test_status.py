from enum import StrEnum
from orionis.mail.enums.status import MailStatus
from orionis.test import TestCase

class TestMailStatus(TestCase):

    def testDeclaresTheThreeConfirmableOutcomes(self) -> None:
        """
        Expose exactly the outcomes a transport can confirm.

        Validates that no member implies mailbox delivery.
        """
        self.assertEqual(
            [member.value for member in MailStatus],
            ["accepted", "partial", "stored"],
        )

    def testMembersCompareEqualToPlainStrings(self) -> None:
        """
        Keep members interchangeable with the serialized status strings.

        Validates that consumers may compare a result against a literal.
        """
        self.assertTrue(issubclass(MailStatus, StrEnum))
        self.assertEqual(MailStatus.ACCEPTED, "accepted")
        self.assertEqual(MailStatus.PARTIAL, "partial")
        self.assertEqual(MailStatus.STORED, "stored")
        self.assertEqual(f"{MailStatus.STORED}", "stored")

    def testLooksUpMembersByValue(self) -> None:
        """
        Resolve a member from a configured or persisted string.

        Validates that an unknown status is rejected.
        """
        self.assertIs(MailStatus("partial"), MailStatus.PARTIAL)
        with self.assertRaises(ValueError):
            MailStatus("delivered")
