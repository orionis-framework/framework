from dataclasses import FrozenInstanceError, asdict
from config.mail import BootstrapMail
from orionis.foundation.config.mail.entities.file import File
from orionis.foundation.config.mail.entities.mail import Mail
from orionis.foundation.config.mail.entities.mailers import Mailers
from orionis.foundation.config.mail.entities.smtp import Smtp
from orionis.test import TestCase


class TestMailConfiguration(TestCase):
    def testNamedMailerSurvivesSerialization(self) -> None:
        """Preserve named mailers through the central configuration entity."""
        original = {
            "archive": {"driver": "file", "path": "storage/mail/archive"},
        }
        config = Mail(default="archive", mailers=original)
        self.assertEqual(asdict(config)["mailers"], original)
        self.assertIsNot(config.mailers, original)

    def testBootstrapKeepsFrozenDataclassContract(self) -> None:
        """Keep the existing bootstrap and conventional entities usable."""
        config = BootstrapMail(
            default="file",
            mailers=Mailers(
                smtp=Smtp(host="", username="", password=""),
                file=File(path="storage/mail"),
            ),
        )
        self.assertEqual(config.toDict()["mailers"]["file"]["path"], "storage/mail")
        with self.assertRaises(FrozenInstanceError):
            config.default = "smtp"
