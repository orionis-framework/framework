from types import ModuleType
import orionis.mail as mail_package
from orionis.mail import (
    Address,
    Attachment,
    Content,
    Envelope,
    Mailable,
    MailResult,
    MailStatus,
    Message,
    PendingMail,
)
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.contracts.transport import IMailTransport
from orionis.test import TestCase
from tests.mail.fixtures.doubles import RecordingDelivery

class TestMailPackage(TestCase):

    def testDeclaresTheConsumerFacingSurface(self) -> None:
        """
        Export the values and base classes consumers compose mail with.

        Validates that no second Mail facade is published here.
        """
        self.assertEqual(
            mail_package.__all__,
            [
                "Address",
                "Attachment",
                "Content",
                "Envelope",
                "MailResult",
                "MailStatus",
                "Mailable",
                "Message",
                "PendingMail",
            ],
        )
        self.assertFalse(hasattr(mail_package, "Mail"))

    def testNoExportShadowsASubmodule(self) -> None:
        """
        Bind every exported name to a class instead of a module.

        Validates that submodules stay reachable by attribute access.
        """
        for name in mail_package.__all__:
            self.assertNotIsInstance(getattr(mail_package, name), ModuleType)

    def testPerOperationObjectsAndContractsUseSlots(self) -> None:
        """
        Keep operation objects and interfaces free of attribute dictionaries.

        Validates the memory contract of the composition API.
        """
        objects = (
            Address("a@example.com"),
            Attachment.fromStorage("a.pdf"),
            Content(text=""),
            Envelope(),
            MailResult(
                message_id="id",
                mailer="file",
                driver="file",
                status=MailStatus.STORED,
                recipients=(),
            ),
            Message(),
            PendingMail(RecordingDelivery()),
        )
        for value in objects:
            self.assertFalse(hasattr(value, "__dict__"))
        for contract in (Mailable, IMailManager, IMailTransport):
            self.assertEqual(contract.__slots__, ())
