from orionis.auth.concerns.functions import model_primary_key
from orionis.test import TestCase

class _Meta:
    """Model metadata double publishing a primary key name."""

    __slots__ = ("primary_key",)

    def __init__(self, primary_key: object) -> None:
        """Store the primary key value advertised by the metadata.

        Parameters
        ----------
        primary_key : object
            Value to expose as the metadata's primary key.

        Returns
        -------
        None
            Initializes the metadata double.
        """
        self.primary_key = primary_key

class _Documented:
    """Object exposing ORM style metadata."""

    __slots__ = ()

    __meta__ = _Meta("uuid")

class _Blank:
    """Object whose metadata declares an unusable primary key."""

    __slots__ = ()

    __meta__ = _Meta("")

class TestModelPrimaryKey(TestCase):
    """Validate the duck typed primary key lookup."""

    def testReadsTheNameDeclaredByTheMetadata(self) -> None:
        """Query an object exposing ORM metadata.

        Validates that the helper honours the primary key the ORM
        metaclass publishes instead of assuming a convention.

        Returns
        -------
        None
            Asserts that the metadata's declared primary key is returned.
        """
        self.assertEqual(model_primary_key(_Documented()), "uuid")

    def testFallsBackToIdWithoutMetadata(self) -> None:
        """Query a plain object carrying no metadata at all.

        Validates that objects outside the ORM still work as identities.

        Returns
        -------
        None
            Asserts that an object without metadata uses the ``id`` key.
        """
        self.assertEqual(model_primary_key(object()), "id")

    def testFallsBackToIdForAnUnusableDeclaration(self) -> None:
        """Query an object whose metadata declares an empty name.

        Validates the defensive branch that prevents building a query
        against a nameless column.

        Returns
        -------
        None
            Asserts that an unusable declaration falls back to ``id``.
        """
        self.assertEqual(model_primary_key(_Blank()), "id")
