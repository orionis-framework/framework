from orionis.http.enums.interfaces import Interface
from orionis.test import TestCase

class TestInterface(TestCase):
    """Unit tests for the Interface string enumeration."""

    def testAsgiValue(self) -> None:
        """Confirm that the ASGI member has the string value 'asgi'.

        Validates the exact lowercase string used to identify the
        ASGI transport interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Interface.ASGI, "asgi")

    def testRsgiValue(self) -> None:
        """Confirm that the RSGI member has the string value 'rsgi'.

        Validates the exact lowercase string used to identify the
        RSGI transport interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Interface.RSGI, "rsgi")

    def testIsStrEnum(self) -> None:
        """Verify that Interface members behave as plain strings.

        Confirms that each member passes an isinstance check against
        str and can be compared directly with string literals.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for member in Interface:
            self.assertIsInstance(str(member), str)

    def testMemberCount(self) -> None:
        """Verify that exactly two interface types are defined.

        Validates that no undocumented member has been added to the enum.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(list(Interface)), 2)

    def testStringComparison(self) -> None:
        """Confirm that Interface members compare equal to lowercase strings.

        Validates that string equality works without explicit casting,
        as expected from StrEnum.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Interface.ASGI, "asgi")
        self.assertNotEqual(Interface.ASGI, "ASGI")
