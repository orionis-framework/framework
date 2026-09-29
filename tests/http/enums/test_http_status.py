from orionis.http.enums.status import HTTPStatus
from orionis.test import TestCase

class TestHTTPStatus(TestCase):
    """Unit tests for the HTTPStatus enumeration."""

    def testInformationalCodes(self) -> None:
        """Confirm that 1xx informational codes have correct integer values.

        Validates the numeric value of CONTINUE, SWITCHING_PROTOCOLS,
        PROCESSING, and EARLY_HINTS members.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(HTTPStatus.CONTINUE, 100)
        self.assertEqual(HTTPStatus.SWITCHING_PROTOCOLS, 101)
        self.assertEqual(HTTPStatus.PROCESSING, 102)
        self.assertEqual(HTTPStatus.EARLY_HINTS, 103)

    def testSuccessCodes(self) -> None:
        """Confirm that 2xx success codes have correct integer values.

        Validates a representative subset of 2xx members including
        OK, CREATED, NO_CONTENT, and PARTIAL_CONTENT.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(HTTPStatus.OK, 200)
        self.assertEqual(HTTPStatus.CREATED, 201)
        self.assertEqual(HTTPStatus.ACCEPTED, 202)
        self.assertEqual(HTTPStatus.NO_CONTENT, 204)
        self.assertEqual(HTTPStatus.PARTIAL_CONTENT, 206)

    def testRedirectionCodes(self) -> None:
        """Confirm that 3xx redirection codes have correct integer values.

        Validates MOVED_PERMANENTLY, FOUND, SEE_OTHER,
        TEMPORARY_REDIRECT, and PERMANENT_REDIRECT.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(HTTPStatus.MOVED_PERMANENTLY, 301)
        self.assertEqual(HTTPStatus.FOUND, 302)
        self.assertEqual(HTTPStatus.SEE_OTHER, 303)
        self.assertEqual(HTTPStatus.NOT_MODIFIED, 304)
        self.assertEqual(HTTPStatus.TEMPORARY_REDIRECT, 307)
        self.assertEqual(HTTPStatus.PERMANENT_REDIRECT, 308)

    def testClientErrorCodes(self) -> None:
        """Confirm that 4xx client-error codes have correct integer values.

        Validates BAD_REQUEST, UNAUTHORIZED, FORBIDDEN, NOT_FOUND,
        METHOD_NOT_ALLOWED, UNPROCESSABLE_CONTENT, and TOO_MANY_REQUESTS.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(HTTPStatus.BAD_REQUEST, 400)
        self.assertEqual(HTTPStatus.UNAUTHORIZED, 401)
        self.assertEqual(HTTPStatus.FORBIDDEN, 403)
        self.assertEqual(HTTPStatus.NOT_FOUND, 404)
        self.assertEqual(HTTPStatus.METHOD_NOT_ALLOWED, 405)
        self.assertEqual(HTTPStatus.UNPROCESSABLE_CONTENT, 422)
        self.assertEqual(HTTPStatus.TOO_MANY_REQUESTS, 429)

    def testServerErrorCodes(self) -> None:
        """Confirm that 5xx server-error codes have correct integer values.

        Validates INTERNAL_SERVER_ERROR, NOT_IMPLEMENTED, BAD_GATEWAY,
        SERVICE_UNAVAILABLE, and GATEWAY_TIMEOUT.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(HTTPStatus.INTERNAL_SERVER_ERROR, 500)
        self.assertEqual(HTTPStatus.NOT_IMPLEMENTED, 501)
        self.assertEqual(HTTPStatus.BAD_GATEWAY, 502)
        self.assertEqual(HTTPStatus.SERVICE_UNAVAILABLE, 503)
        self.assertEqual(HTTPStatus.GATEWAY_TIMEOUT, 504)

    def testIsIntEnum(self) -> None:
        """Verify that HTTPStatus values are usable as plain integers.

        Confirms that IntEnum members can be compared directly to int
        literals and used in integer arithmetic.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(HTTPStatus.OK + 1, 201)
        self.assertIsInstance(int(HTTPStatus.NOT_FOUND), int)

    def testMemberIterable(self) -> None:
        """Verify that all HTTPStatus members are accessible by iteration.

        Confirms that the enum has more than ten members and that every
        member value is a positive integer.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        members = list(HTTPStatus)
        self.assertGreater(len(members), 10)
        for member in members:
            self.assertIsInstance(int(member), int)
            self.assertGreater(int(member), 0)

    def testTeapotCode(self) -> None:
        """Confirm that IM_A_TEAPOT equals 418.

        Validates RFC 2324 compliance for the special status code.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(HTTPStatus.IM_A_TEAPOT, 418)
