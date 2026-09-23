from types import ModuleType
from orionis.mail import entities as entities_package
from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.content import Content
from orionis.mail.entities.envelope import Envelope
from orionis.mail.entities.options import MailOptions
from orionis.mail.entities.prepared import PreparedMail
from orionis.mail.entities.result import MailResult
from orionis.mail.entities.smtp_settings import SmtpSettings
from orionis.test import TestCase

class TestMailEntitiesPackage(TestCase):

    def testDeclaresEveryEntityAsAPublicExport(self) -> None:
        """
        Expose the eight mail entities from the package root.

        Validates the public surface consumers may import.
        """
        self.assertEqual(
            entities_package.__all__,
            [
                "Address",
                "Attachment",
                "Content",
                "Envelope",
                "MailOptions",
                "MailResult",
                "PreparedMail",
                "SmtpSettings",
            ],
        )

    def testReExportsBindEachEntityClass(self) -> None:
        """
        Bind every exported name to its real entity class.

        Validates that no export shadows a sibling submodule.
        """
        exported = {
            "Address": Address,
            "Attachment": Attachment,
            "Content": Content,
            "Envelope": Envelope,
            "MailOptions": MailOptions,
            "MailResult": MailResult,
            "PreparedMail": PreparedMail,
            "SmtpSettings": SmtpSettings,
        }
        for name, entity in exported.items():
            self.assertIs(getattr(entities_package, name), entity)
            self.assertNotIsInstance(getattr(entities_package, name), ModuleType)

    def testEveryEntityUsesSlots(self) -> None:
        """
        Keep entity instances free of attribute dictionaries.

        Validates the memory contract shared by framework entities.
        """
        instances = (
            Address("ana@example.com"),
            Attachment.fromStorage("guide.pdf"),
            Content(text=""),
            Envelope(),
            MailOptions(),
            PreparedMail(
                message_id="<id@example.com>",
                sender="a@example.com",
                recipients=(),
                mime=b"",
                smtp_utf8=False,
            ),
            SmtpSettings.fromConfig({"host": "smtp.example.com"}),
        )
        for instance in instances:
            self.assertFalse(hasattr(instance, "__dict__"))
