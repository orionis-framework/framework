from pathlib import Path
from orionis.mail.entities.result import MailResult
from orionis.mail.enums.status import MailStatus
from orionis.test import TestCase

class TestMailResult(TestCase):

    def testOwnsItsRecipientCollectionsAndRejections(self) -> None:
        """
        Detach every collection supplied by a transport.

        Validates that mutating the caller's data never changes the result.
        """
        rejected = {"a@example.com": [550, "No\r\nmail\x00"]}
        recipients = ["a@example.com", "c@example.com"]
        accepted = ["c@example.com"]
        result = MailResult(
            message_id="<id@example.com>",
            mailer="smtp",
            driver="smtp",
            status=MailStatus.PARTIAL,
            recipients=recipients,
            accepted_recipients=accepted,
            rejected_recipients=rejected,
        )
        rejected.clear()
        recipients.clear()
        accepted.clear()

        self.assertEqual(result.recipients, ("a@example.com", "c@example.com"))
        self.assertEqual(result.accepted_recipients, ("c@example.com",))
        self.assertEqual(
            result.rejected_recipients["a@example.com"],
            (550, "No  mail "),
        )
        with self.assertRaises(TypeError):
            result.rejected_recipients["new@example.com"] = (500, "no")

    def testStoredResultsCarryAPathAndNoSmtpAcceptance(self) -> None:
        """
        Keep acceptance collections empty for a stored message.

        Validates that file publication never claims SMTP acceptance.
        """
        result = MailResult(
            message_id="<id@example.com>",
            mailer="archive",
            driver="file",
            status=MailStatus.STORED,
            recipients=("ana@example.com",),
            file_path=Path("outgoing/message.eml"),
        )
        self.assertEqual(result.status, "stored")
        self.assertEqual(result.accepted_recipients, ())
        self.assertEqual(dict(result.rejected_recipients), {})
        self.assertEqual(result.file_path.name, "message.eml")

    def testAcceptedResultsHaveNoFilePath(self) -> None:
        """
        Report a fully accepted SMTP transaction without a file path.

        Validates the shape of a successful transport result.
        """
        result = MailResult(
            message_id="<id@example.com>",
            mailer="smtp",
            driver="smtp",
            status=MailStatus.ACCEPTED,
            recipients=("ana@example.com",),
            accepted_recipients=("ana@example.com",),
        )
        self.assertIsNone(result.file_path)
        self.assertEqual(result.status, MailStatus.ACCEPTED)
        self.assertEqual(result.accepted_recipients, result.recipients)
