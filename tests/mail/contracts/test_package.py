from orionis.mail import contracts as contracts_package
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.contracts.transport import IMailTransport
from orionis.test import TestCase

class TestMailContractsPackage(TestCase):

    def testDeclaresBothContractsAsPublicExports(self) -> None:
        """
        Expose the manager and transport contracts from the package root.

        Validates the interfaces available to consumers and driver authors.
        """
        self.assertEqual(
            contracts_package.__all__,
            ["IMailManager", "IMailTransport"],
        )

    def testReExportsBindEachContract(self) -> None:
        """
        Bind every exported name to its real interface.

        Validates that the re-exports are not shadowing aliases.
        """
        self.assertIs(contracts_package.IMailManager, IMailManager)
        self.assertIs(contracts_package.IMailTransport, IMailTransport)
