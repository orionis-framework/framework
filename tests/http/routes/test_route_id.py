from orionis.http.routes.route_id import RouteID
from orionis.test import TestCase

class TestRouteID(TestCase):
    """Unit tests for the RouteID unique-identifier generator."""

    def testNextReturnsString(self) -> None:
        """Verify that RouteID.next returns a string value.

        Confirms the return type for any method/path combination.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = RouteID.next("GET", "/users")
        self.assertIsInstance(result, str)

    def testNextIsUnique(self) -> None:
        """Verify that successive calls to RouteID.next produce distinct values.

        Generates two identifiers for the same method and path and
        confirms they differ, ensuring monotonic counters or timestamps
        are applied correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        id1 = RouteID.next("GET", "/users")
        id2 = RouteID.next("GET", "/users")
        self.assertNotEqual(id1, id2)

    def testNextContainsMethod(self) -> None:
        """Verify that the generated ID encodes the HTTP method.

        Confirms that the method string appears verbatim in the
        returned identifier.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = RouteID.next("POST", "/orders")
        self.assertIn("POST", result)

    def testNextContainsPath(self) -> None:
        """Verify that the generated ID encodes the route path.

        Confirms that the path string appears verbatim in the
        returned identifier.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = RouteID.next("DELETE", "/items/42")
        self.assertIn("/items/42", result)

    def testNextWithRootPath(self) -> None:
        """Verify that RouteID.next handles the root path without errors.

        Confirms that '/' is a valid path input and produces a non-empty
        string identifier.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = RouteID.next("GET", "/")
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def testNextLargeBatch(self) -> None:
        """Verify that a batch of consecutive IDs are all unique.

        Generates fifty identifiers for the same route specification
        and confirms the resulting set has no duplicates.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ids = [RouteID.next("GET", "/ping") for _ in range(50)]
        self.assertEqual(len(ids), len(set(ids)))
