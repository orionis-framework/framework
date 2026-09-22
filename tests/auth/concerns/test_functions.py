from orionis.auth.concerns.functions import model_primary_key
from orionis.test import TestCase


class _Meta:
    """Model metadata double publishing a primary key name."""

    __slots__ = ("primary_key",)

    def __init__(self, primary_key: object) -> None:
        """Store the value the metadata advertises as primary key."""
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
        """
        self.assertEqual(model_primary_key(_Documented()), "uuid")

    def testFallsBackToIdWithoutMetadata(self) -> None:
        """Query a plain object carrying no metadata at all.

        Validates that objects outside the ORM still work as identities.
        """
        self.assertEqual(model_primary_key(object()), "id")

    def testFallsBackToIdForAnUnusableDeclaration(self) -> None:
        """Query an object whose metadata declares an empty name.

        Validates the defensive branch that prevents building a query
        against a nameless column.
        """
        self.assertEqual(model_primary_key(_Blank()), "id")
