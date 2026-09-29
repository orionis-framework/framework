from orionis.http.enums.status import WebSocketStatus
from orionis.test import TestCase

class TestWebSocketStatus(TestCase):
    """Unit tests for the WebSocketStatus enumeration."""

    def testNormalClosure(self) -> None:
        """Confirm that NORMAL_CLOSURE equals 1000.

        Validates the standard close code for a clean WebSocket shutdown.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(WebSocketStatus.NORMAL_CLOSURE, 1000)

    def testProtocolError(self) -> None:
        """Confirm that PROTOCOL_ERROR equals 1002.

        Validates the code indicating a protocol-level violation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(WebSocketStatus.PROTOCOL_ERROR, 1002)

    def testInternalError(self) -> None:
        """Confirm that INTERNAL_ERROR equals 1011.

        Validates the server-side unexpected-condition code.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(WebSocketStatus.INTERNAL_ERROR, 1011)

    def testCustomAuthCodes(self) -> None:
        """Confirm that custom auth-related codes have correct values.

        Validates UNAUTHORIZED (3000), FORBIDDEN (3003), and
        TIMEOUT (3008) which are application-defined extensions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(WebSocketStatus.UNAUTHORIZED, 3000)
        self.assertEqual(WebSocketStatus.FORBIDDEN, 3003)
        self.assertEqual(WebSocketStatus.TIMEOUT, 3008)

    def testIsIntEnum(self) -> None:
        """Verify that WebSocketStatus values are usable as plain integers.

        Confirms that members compare equal to their integer equivalents.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(int(WebSocketStatus.GOING_AWAY), int)
        self.assertEqual(int(WebSocketStatus.GOING_AWAY), 1001)
