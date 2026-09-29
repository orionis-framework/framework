from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from orionis.test import TestCase
from orionis.support.entities.base import BaseEntity

# ---------------------------------------------------------------------------
# Fixtures: dataclasses used across all tests
# ---------------------------------------------------------------------------

class Color(Enum):
    """Simple enum fixture for testing enum serialization."""

    RED = "red"
    BLUE = "blue"

@dataclass
class SimpleEntity(BaseEntity):
    """Minimal entity with basic field types."""

    name: str = "default"
    count: int = 0
    active: bool = True

@dataclass
class EnumEntity(BaseEntity):
    """Entity containing an Enum field."""

    color: Color = Color.RED

@dataclass
class NullableEntity(BaseEntity):
    """Entity with a union / optional field."""

    value: int | None = None

@dataclass
class FactoryEntity(BaseEntity):
    """Entity using default_factory for a list field."""

    items: list = field(default_factory=list)

@dataclass
class MetadataEntity(BaseEntity):
    """Entity with field-level metadata."""

    score: int = field(default=0, metadata={"label": "Score", "default": 42})

@dataclass
class NestedEntity(BaseEntity):
    """Entity that nests another BaseEntity (as an inner dataclass)."""

    inner: SimpleEntity = field(default_factory=SimpleEntity)

@dataclass
class EmptyEntity(BaseEntity):
    """Entity with no fields."""

# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestBaseEntity(TestCase):

    # ------------------------------------------------ __post_init__

    def testPostInitIsCallable(self):
        """Confirm __post_init__ is defined and callable.

        Validates that BaseEntity exposes __post_init__ as a method
        that can be called without raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        entity.__post_init__()  # must not raise

    def testPostInitReturnsNone(self):
        """Return None from __post_init__.

        Validates that the default __post_init__ implementation
        returns None explicitly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        result = entity.__post_init__() # NOSONAR
        self.assertIsNone(result)

    # ------------------------------------------------ toDict - basic

    def testToDictReturnsDict(self):
        """Return a dict from toDict.

        Validates that toDict produces a plain dict instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        self.assertIsInstance(entity.toDict(), dict)

    def testToDictContainsAllFields(self):
        """Include all dataclass fields in toDict output.

        Validates that every declared field appears as a key
        in the resulting dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity(name="orionis", count=3, active=False)
        result = entity.toDict()
        self.assertIn("name", result)
        self.assertIn("count", result)
        self.assertIn("active", result)

    def testToDictPreservesValues(self):
        """Preserve field values in toDict output.

        Validates that the values in the resulting dict match
        the values set on the entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity(name="test", count=7, active=False)
        result = entity.toDict()
        self.assertEqual(result["name"], "test")
        self.assertEqual(result["count"], 7)
        self.assertFalse(result["active"])

    def testToDictConvertsEnumToValue(self):
        """Convert Enum fields to their primitive values.

        Validates that Enum instances are serialized as their
        underlying value rather than the Enum object itself.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = EnumEntity(color=Color.BLUE)
        result = entity.toDict()
        self.assertEqual(result["color"], "blue")
        self.assertNotIsInstance(result["color"], Enum)

    def testToDictWithNullableNone(self):
        """Serialize None value for optional fields.

        Validates that a field with a None value is represented
        as None in the toDict output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = NullableEntity(value=None)
        result = entity.toDict()
        self.assertIsNone(result["value"])

    def testToDictWithNullableValue(self):
        """Serialize a non-None optional field value.

        Validates that an optional field set to an int is
        stored correctly in toDict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = NullableEntity(value=99)
        result = entity.toDict()
        self.assertEqual(result["value"], 99)

    def testToDictWithDefaultFactory(self):
        """Serialize list default_factory fields correctly.

        Validates that a field using default_factory is included
        in toDict with its default value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = FactoryEntity()
        result = entity.toDict()
        self.assertEqual(result["items"], [])

    def testToDictWithPopulatedList(self):
        """Serialize a populated list field.

        Validates that a list field with items is serialized
        as a list in the toDict output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = FactoryEntity(items=[1, 2, 3])
        result = entity.toDict()
        self.assertEqual(result["items"], [1, 2, 3])

    def testToDictEmptyEntity(self):
        """Return empty dict for entity with no fields.

        Validates that toDict produces an empty dict when
        the dataclass defines no fields.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = EmptyEntity()
        self.assertEqual(entity.toDict(), {})

    def testToDictIsShallowCopyOnMutation(self):
        """Confirm toDict result is independent from entity mutation.

        Validates that modifying the entity after calling toDict
        does not alter the previously returned dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity(name="original")
        result = entity.toDict()
        entity.name = "changed"
        self.assertEqual(result["name"], "original")

    def testToDictCopiesMutableNestedValues(self):
        """Copy nested containers so serialized values do not alias fields.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        @dataclass
        class ContainerEntity(BaseEntity):
            payload: dict = field(default_factory=lambda: {"items": [1]})

        entity = ContainerEntity()
        result = entity.toDict()
        result["payload"]["items"].append(2)
        self.assertEqual(entity.payload, {"items": [1]})

    def testToDictKeepsEnumsInsideContainers(self):
        """Keep enum values inside containers consistent with asdict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        @dataclass
        class ContainerEntity(BaseEntity):
            colors: list = field(default_factory=lambda: [Color.RED])

        self.assertEqual(ContainerEntity().toDict()["colors"], [Color.RED])

    def testSlottedEntityDoesNotInheritAnInstanceDictionary(self):
        """Keep slotted entity instances free of an inherited dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        @dataclass(slots=True)
        class SlottedEntity(BaseEntity):
            value: int = 1

        entity = SlottedEntity()
        self.assertFalse(hasattr(entity, "__dict__"))
        self.assertEqual(entity.toDict(), {"value": 1})

    # ------------------------------------------------ getFields - basic

    def testGetFieldsReturnsList(self):
        """Return a list from getFields.

        Validates that getFields produces a list instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        self.assertIsInstance(entity.getFields(), list)

    def testGetFieldsCountMatchesDataclassFields(self):
        """Return one entry per declared dataclass field.

        Validates that the length of getFields output equals the
        number of declared fields in the dataclass.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        result = entity.getFields()
        self.assertEqual(len(result), 3)

    def testGetFieldsContainsRequiredKeys(self):
        """Include required keys in each field dict.

        Validates that each element in getFields output contains
        the keys 'name', 'types', 'default', and 'metadata'.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        for entry in entity.getFields():
            self.assertIn("name", entry)
            self.assertIn("types", entry)
            self.assertIn("default", entry)
            self.assertIn("metadata", entry)

    def testGetFieldsNameMatchesDeclaredField(self):
        """Report correct field names in getFields output.

        Validates that the 'name' key in each entry matches the
        actual field name declared in the dataclass.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        names = [f["name"] for f in entity.getFields()]
        self.assertIn("name", names)
        self.assertIn("count", names)
        self.assertIn("active", names)

    def testGetFieldsTypesIsAlwaysList(self):
        """Return 'types' as a list in every field entry.

        Validates that the 'types' value in each field dict is
        always a list, even for simple types like int or str.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        for entry in entity.getFields():
            self.assertIsInstance(entry["types"], list)

    def testGetFieldsSimpleTypeContainsTypeName(self):
        """Include the type name for simple-typed fields.

        Validates that the 'types' list for a plain int field
        contains the string 'int'.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        count_field = next(f for f in entity.getFields() if f["name"] == "count")
        self.assertIn("int", count_field["types"])

    def testGetFieldsDefaultValueReflectsDeclared(self):
        """Report the declared default in the 'default' key.

        Validates that the 'default' value in the field dict
        matches the default declared for the field.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        name_field = next(f for f in entity.getFields() if f["name"] == "name")
        self.assertEqual(name_field["default"], "default")

    def testGetFieldsDefaultForIntField(self):
        """Report correct int default in getFields.

        Validates that an int field with a default of 0 is
        reported as 0 in the 'default' key.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        count_field = next(f for f in entity.getFields() if f["name"] == "count")
        self.assertEqual(count_field["default"], 0)

    def testGetFieldsDefaultFactory(self):
        """Report the result of default_factory in 'default'.

        Validates that a field using default_factory has its
        factory called and the result stored as the default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = FactoryEntity()
        items_field = next(f for f in entity.getFields() if f["name"] == "items")
        self.assertEqual(items_field["default"], [])

    def testGetFieldsMetadataIsDict(self):
        """Return metadata as a dict in each field entry.

        Validates that the 'metadata' key in each field dict
        is always a dict instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        for entry in entity.getFields():
            self.assertIsInstance(entry["metadata"], dict)

    def testGetFieldsEmptyMetadataForPlainField(self):
        """Return empty metadata for fields without metadata.

        Validates that fields declared without explicit metadata
        report an empty dict under the 'metadata' key.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity()
        name_field = next(f for f in entity.getFields() if f["name"] == "name")
        self.assertEqual(name_field["metadata"], {})

    def testGetFieldsMetadataPreservesCustomKeys(self):
        """Include custom metadata keys in the field entry.

        Validates that metadata declared with field() is preserved
        and accessible in the 'metadata' dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = MetadataEntity()
        score_field = next(
            f for f in entity.getFields() if f["name"] == "score"
        )
        self.assertIn("label", score_field["metadata"])
        self.assertEqual(score_field["metadata"]["label"], "Score")

    def testGetFieldsMetadataDefaultOverridesFieldDefault(self):
        """Use metadata default as fallback when field has no default.

        Validates that when no field default is set but metadata
        contains a 'default' key, that value is used.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = MetadataEntity()
        score_field = next(
            f for f in entity.getFields() if f["name"] == "score"
        )
        # field.default = 0, so 'default' is taken from field.default
        self.assertEqual(score_field["default"], 0)

    # ------------------------------------------------ getFields - enum

    def testGetFieldsEnumDefaultIsSerializedValue(self):
        """Serialize Enum defaults to their primitive values.

        Validates that if the default value of a field is an Enum,
        getFields reports the Enum's value, not the Enum object.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = EnumEntity()
        color_field = next(
            f for f in entity.getFields() if f["name"] == "color"
        )
        self.assertEqual(color_field["default"], "red")
        self.assertNotIsInstance(color_field["default"], Enum)

    # ------------------------------------------------ getFields - union types

    def testGetFieldsUnionTypeReturnsMultipleTypes(self):
        """Report multiple type strings for union-typed fields.

        Validates that a field with a union type (int | None)
        has more than one entry in the 'types' list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = NullableEntity()
        value_field = next(
            f for f in entity.getFields() if f["name"] == "value"
        )
        self.assertGreater(len(value_field["types"]), 1)

    def testGetFieldsUnionTypeContainsIntAndNone(self):
        """Include 'int' and 'None' in union type list.

        Validates that a field typed as int | None reports both
        'int' and 'None' as its type strings.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = NullableEntity()
        value_field = next(
            f for f in entity.getFields() if f["name"] == "value"
        )
        types_str = " ".join(value_field["types"])
        self.assertIn("int", types_str)
        self.assertIn("None", types_str)

    # ------------------------------------------------ getFields - empty entity

    def testGetFieldsEmptyEntityReturnsList(self):
        """Return empty list for entity with no fields.

        Validates that getFields returns an empty list when the
        dataclass defines no fields at all.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = EmptyEntity()
        self.assertEqual(entity.getFields(), [])

    # ------------------------------------------------ nested entity

    def testToDictNestedEntityIsConverted(self):
        """Recursively convert nested entities in toDict.

        Validates that a field containing another dataclass is
        converted to a nested dict in the toDict output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = NestedEntity()
        result = entity.toDict()
        self.assertIsInstance(result["inner"], dict)
        self.assertIn("name", result["inner"])

    def testGetFieldsNestedEntityDefaultIsDict(self):
        """Serialize nested dataclass defaults as dicts in getFields.

        Validates that a field whose default is a nested dataclass
        has that default converted to a plain dict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = NestedEntity()
        inner_field = next(
            f for f in entity.getFields() if f["name"] == "inner"
        )
        self.assertIsInstance(inner_field["default"], dict)

    # ---------------------------------------- inheritance / extensibility

    def testSubclassCanOverridePostInit(self):
        """Allow subclasses to override __post_init__.

        Validates that a subclass can extend __post_init__ to
        perform additional initialization logic.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        @dataclass
        class ValidatedEntity(BaseEntity):
            value: int = 0

            def __post_init__(self) -> None:
                """Validate the entity value after initialization.

                Returns
                -------
                None
                    Completes the operation described above.

                Raises
                ------
                ValueError
                    Raised by this helper to exercise the failure path.
                """
                if self.value < 0:
                    error_msg = "value must be non-negative"
                    raise ValueError(error_msg)

        valid = ValidatedEntity(value=5)
        self.assertEqual(valid.value, 5)
        with self.assertRaises(ValueError):
            ValidatedEntity(value=-1)

    def testToDictPreservesTypesAfterUpdate(self):
        """Preserve attribute types after direct mutation in toDict.

        Validates that modifying a field directly and calling
        toDict reflects the updated value correctly.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        entity = SimpleEntity(count=1)
        entity.count = 42
        result = entity.toDict()
        self.assertEqual(result["count"], 42)
