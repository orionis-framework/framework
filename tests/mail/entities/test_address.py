from orionis.mail.entities.address import Address, addresses, one_address
from orionis.mail.exceptions import MailCompositionException
from orionis.test import TestCase

class TestAddress(TestCase):

    def testPreservesLocalCaseAndNormalizesDomains(self) -> None:
        """
        Deduplicate mailboxes by their normalized addr-spec.

        Validates that the domain is lowercased while the potentially
        significant local part keeps its original case.
        """
        result = addresses(["Ana@EXAMPLE.com", "Ana@example.com", "ana@example.com"])
        self.assertEqual(
            tuple(item.address for item in result),
            ("Ana@example.com", "ana@example.com"),
        )

    def testInternationalMailboxAndDisplayName(self) -> None:
        """
        Preserve SMTPUTF8 local parts and Unicode display names.

        Validates that an internationalized domain is encoded with IDNA.
        """
        address = Address("jos\u00e9@example.com", "Jos\u00e9")
        self.assertEqual(address.asHeader().username, "jos\u00e9")
        self.assertEqual(address.asHeader().display_name, "Jos\u00e9")
        self.assertEqual(
            Address("ana@b\u00fccher.example").address,
            "ana@xn--bcher-kva.example",
        )

    def testHeaderKeepsTheOptionalDisplayName(self) -> None:
        """
        Build a header value that carries the mailbox and its name.

        Validates the structure the composer writes into address headers.
        """
        header = Address("ana@example.com", "Ana").asHeader()
        self.assertEqual(header.addr_spec, "ana@example.com")
        self.assertEqual(header.display_name, "Ana")
        self.assertEqual(Address("ana@example.com").asHeader().display_name, "")

    def testSingleMailboxAcceptsStringsAndAddresses(self) -> None:
        """
        Normalize one mailbox supplied as a string or as an Address.

        Validates that an existing Address is reused without copying.
        """
        existing = Address("ana@example.com", "Ana")
        self.assertIs(one_address(existing), existing)
        self.assertEqual(one_address("ana@EXAMPLE.com").address, "ana@example.com")
        self.assertEqual(one_address("ana@example.com", "Ana").name, "Ana")

    def testCollectionsAreNormalizedIntoTuples(self) -> None:
        """
        Accept a single mailbox or a list/tuple of mailboxes.

        Validates that every declaration produces a tuple of addresses.
        """
        self.assertEqual(len(addresses("ana@example.com")), 1)
        self.assertEqual(len(addresses(Address("ana@example.com"))), 1)
        self.assertEqual(len(addresses(("a@example.com", "b@example.com"))), 2)
        self.assertEqual(
            len(addresses([Address("a@example.com"), "b@example.com"])),
            2,
        )
        self.assertEqual(addresses(()), ())

    def testRejectsInvalidMailboxes(self) -> None:
        """
        Reject malformed mailboxes, lists encoded as strings, and injection.

        Validates that a display-name form and a header break never parse.
        """
        for value in (
            "",
            "local",
            "a@",
            "a@b,c@d",
            "Name <a@b>",
            "a@b\r\nBcc: x@y",
            "a@" + "a" * 64 + ".example",
        ):
            with self.assertRaises(MailCompositionException):
                Address(value)

    def testRejectsAmbiguousOrInvalidNames(self) -> None:
        """
        Reject a display name that duplicates or contradicts a declaration.

        Validates that names are only accepted beside a single string mailbox.
        """
        with self.assertRaises(MailCompositionException):
            addresses(["a@example.com"], "Name")
        with self.assertRaises(MailCompositionException):
            one_address(Address("a@example.com"), "Name")
        with self.assertRaises(MailCompositionException):
            Address("a@example.com", "Name\x00")

    def testRejectsUnsupportedRecipientContainers(self) -> None:
        """
        Reject containers that are not a list or a tuple of mailboxes.

        Validates that a set or a generator never reaches the parser.
        """
        for value in ({"a@example.com"}, 7, None):
            with self.assertRaises(MailCompositionException):
                addresses(value)
