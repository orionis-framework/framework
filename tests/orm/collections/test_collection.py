from typing import ClassVar
from orionis.orm.collections.collection import Collection, ModelCollection
from orionis.orm.model import Model
from orionis.orm.schema.types import Integer, String
from orionis.support.types.collection import Collection as FrameworkCollection
from orionis.test import TestCase

class _CollectionRecord(Model):
    """Provide a serializable model with a hidden column."""

    id = Integer().primary()
    name = String()
    hidden: ClassVar[list[str]] = ["name"]
    timestamps = False

class TestModelCollection(TestCase):
    """Verify ORM collections reuse the framework's collection implementation."""

    def testOrmAliasesUseTheFrameworkCollection(self) -> None:
        """Expose one collection implementation across framework and ORM APIs.

        Returns
        -------
        None
            Verify both ORM aliases retain the framework collection identity.
        """
        self.assertIs(Collection, FrameworkCollection)
        self.assertIs(ModelCollection, FrameworkCollection)

    def testCollectionSerializesModelsThroughTheirPublicSerializer(self) -> None:
        """Serialize ORM instances without exposing hidden model attributes.

        Returns
        -------
        None
            Verify collection serialization calls the model's serializer.
        """
        record = _CollectionRecord({"id": 7, "name": "hidden"})
        collection = ModelCollection([record])
        self.assertEqual(collection.serialize(), [{"id": 7}])
        self.assertIs(collection[0], record)
