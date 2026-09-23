from orionis.mail.exceptions import (
    MailAttachmentException,
    MailCompositionException,
    MailConfigurationException,
    MailException,
    MailTransportException,
)
from orionis.test import TestCase

class TestMailExceptions(TestCase):

    def testEveryFailureSharesOneBaseClass(self) -> None:
        """
        Derive every mail failure from a single catchable base.

        Validates that one handler can cover the whole module.
        """
        for exception in (
            MailConfigurationException,
            MailCompositionException,
            MailTransportException,
        ):
            self.assertTrue(issubclass(exception, MailException))
        self.assertTrue(issubclass(MailException, Exception))

    def testAttachmentFailuresAreCompositionFailures(self) -> None:
        """
        Treat an unreadable attachment as a composition failure.

        Validates that both can be caught with one clause before transport.
        """
        self.assertTrue(issubclass(MailAttachmentException, MailCompositionException))

    def testCarriesTheSuppliedMessageAndCause(self) -> None:
        """
        Preserve the reported message and its original cause.

        Validates the diagnostics produced by the pipeline.
        """
        cause = ValueError("origin")
        error_msg = "transport failed"
        try:
            raise MailTransportException(error_msg) from cause
        except MailException as exception:
            self.assertEqual(str(exception), "transport failed")
            self.assertIs(exception.__cause__, cause)

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots in every exception of the hierarchy.

        Validates that raising one allocates no attribute dictionary.
        """
        for exception in (
            MailException,
            MailConfigurationException,
            MailCompositionException,
            MailAttachmentException,
            MailTransportException,
        ):
            self.assertEqual(exception.__slots__, ())
