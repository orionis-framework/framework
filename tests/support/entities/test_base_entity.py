"""
Exercise shared behavior for dataclass entities.

Cover generated and shared constructors, dictionary serialization, and field
inspection.
"""

# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import NamedTuple
from orionis.support.entities.base import BaseEntity
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Fixtures: dataclasses used across all tests
# ---------------------------------------------------------------------------


class Color(Enum):
    """
    Provide string-valued colors for serialization tests.

    Attributes
    ----------
    RED : Color
        Member that serializes as ``"red"``.
    BLUE : Color
        Member that serializes as ``"blue"``.
    """

    RED = "red"
    BLUE = "blue"


@dataclass
class SimpleEntity(BaseEntity):
    """
    Provide scalar fields for entity tests.

    Parameters
    ----------
    name : str, optional
        Name to serialize. Defaults to ``"default"``.
    count : int, optional
        Count to serialize. Defaults to ``0``.
    active : bool, optional
        Flag that defaults to ``True``.
    """

    name: str = "default"
    count: int = 0
    active: bool = True


@dataclass
class EnumEntity(BaseEntity):
    """
    Provide an entity for enum serialization tests.

    Parameters
    ----------
    color : Color, optional
        Enum member to serialize. Defaults to ``Color.RED``.
    """

    color: Color = Color.RED


@dataclass
class NullableEntity(BaseEntity):
    """
    Provide an entity for nullable-field tests.

    Parameters
    ----------
    value : int or None, optional
        Integer to serialize. Defaults to ``None``.
    """

    value: int | None = None


@dataclass
class FactoryEntity(BaseEntity):
    """
    Provide a list field backed by a default factory.

    Parameters
    ----------
    items : list, optional
        Values to serialize. Omit to use a new empty list.
    """

    items: list = field(default_factory=list)


@dataclass
class MetadataEntity(BaseEntity):
    """
    Provide a score field with a metadata label and conflicting default.

    Parameters
    ----------
    score : int, optional
        Score value. Defaults to ``0`` even though metadata specifies ``42``.
    """

    score: int = field(default=0, metadata={"label": "Score", "default": 42})


@dataclass
class NestedEntity(BaseEntity):
    """
    Provide a fixture for nested entity serialization.

    Parameters
    ----------
    inner : SimpleEntity, optional
        Entity to serialize. Omit to create a new ``SimpleEntity``.
    """

    inner: SimpleEntity = field(default_factory=SimpleEntity)


@dataclass(init=False)
class EmptyEntity(BaseEntity):
    """
    Use the shared constructor without declaring any fields.

    Accept public extras so dynamic attributes can be tested separately
    from dataclass fields.
    """


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestBaseEntity(TestCase):
    """
    Verify the behavior of ``BaseEntity`` subclasses.

    Exercise default factories, nested values, dynamic attributes, and
    post-init hooks with small fixtures.
    """

    # ------------------------------------------------ toDict - basic

    def testToDictReturnsDict(self) -> None:
        """
        Verify the return type of ``toDict()``.

        Returns
        -------
        None
            Assert that a default entity serializes to a dictionary.
        """
        entity = SimpleEntity()
        self.assertIsInstance(entity.toDict(), dict)

    def testToDictContainsAllFields(self) -> None:
        """
        Verify that serialization includes every declared field.

        Returns
        -------
        None
            Check for the ``name``, ``count``, and ``active`` keys.
        """
        entity = SimpleEntity(name="orionis", count=3, active=False)
        result = entity.toDict()
        self.assertIn("name", result)
        self.assertIn("count", result)
        self.assertIn("active", result)

    def testToDictPreservesValues(self) -> None:
        """
        Verify that serialization preserves the assigned field values.

        Returns
        -------
        None
            Check the custom name, count, and false flag against the input.
        """
        entity = SimpleEntity(name="test", count=7, active=False)
        result = entity.toDict()
        self.assertEqual(result["name"], "test")
        self.assertEqual(result["count"], 7)
        self.assertFalse(result["active"])

    def testToDictConvertsEnumToValue(self) -> None:
        """
        Verify that serialization replaces an enum member with its value.

        Returns
        -------
        None
            Check for the string ``"blue"`` rather than ``Color.BLUE``.
        """
        entity = EnumEntity(color=Color.BLUE)
        result = entity.toDict()
        self.assertEqual(result["color"], "blue")
        self.assertNotIsInstance(result["color"], Enum)

    def testToDictWithNullableNone(self) -> None:
        """
        Verify serialization of a nullable field set to ``None``.

        Returns
        -------
        None
            Assert that the serialized ``value`` is ``None``.
        """
        entity = NullableEntity(value=None)
        result = entity.toDict()
        self.assertIsNone(result["value"])

    def testToDictWithNullableValue(self) -> None:
        """
        Verify serialization of a populated optional field.

        Returns
        -------
        None
            Assert that the serialized ``value`` matches the supplied integer.
        """
        entity = NullableEntity(value=99)
        result = entity.toDict()
        self.assertEqual(result["value"], 99)

    def testToDictWithDefaultFactory(self) -> None:
        """
        Verify serialization of a factory-provided default.

        Returns
        -------
        None
            Check that the default ``items`` list serializes to an empty list.
        """
        entity = FactoryEntity()
        result = entity.toDict()
        self.assertEqual(result["items"], [])

    def testToDictWithPopulatedList(self) -> None:
        """
        Verify that serialization preserves the contents of a populated list.

        Returns
        -------
        None
            Assert that the serialized ``items`` match the supplied list.
        """
        entity = FactoryEntity(items=[1, 2, 3])
        result = entity.toDict()
        self.assertEqual(result["items"], [1, 2, 3])

    def testToDictEmptyEntity(self) -> None:
        """
        Verify serialization of an entity with no fields.

        Returns
        -------
        None
            Assert that the result is an empty dictionary.
        """
        entity = EmptyEntity()
        self.assertEqual(entity.toDict(), {})

    def testToDictDoesNotFollowLaterFieldAssignment(self) -> None:
        """
        Verify that serialization captures the current field values.

        Returns
        -------
        None
            Check that changing the name leaves the earlier result unchanged.
        """
        entity = SimpleEntity(name="original")
        result = entity.toDict()
        entity.name = "changed"
        self.assertEqual(result["name"], "original")

    def testToDictCopiesMutableNestedValues(self) -> None:
        """
        Verify that serialization copies mutable nested values.

        Returns
        -------
        None
            Append to the serialized list and check the original payload.
        """

        @dataclass
        class ContainerEntity(BaseEntity):
            """
            Provide a fixture for testing nested list mutations.

            Parameters
            ----------
            payload : dict, optional
                Dictionary to serialize. Omit to start with ``{"items": [1]}``.
            """

            payload: dict = field(default_factory=lambda: {"items": [1]})

        entity = ContainerEntity()
        result = entity.toDict()
        result["payload"]["items"].append(2)
        self.assertEqual(entity.payload, {"items": [1]})

    def testSerializeEnumsInsideContainers(self) -> None:
        """
        Verify enum conversion in serialized fields and defaults.

        Returns
        -------
        None
            Check that enum keys and values become strings while tuple nesting
            and named tuple types are preserved.
        """

        @dataclass
        class Swatch:
            """
            Wrap a color in a plain dataclass.

            Parameters
            ----------
            color : Color
                Enum member to serialize from within a tuple.
            """

            color: Color

        class Palette(NamedTuple):
            """
            Wrap a primary color in a named tuple.

            Parameters
            ----------
            primary : Color
                Enum member stored in the tuple.
            """

            primary: Color

        @dataclass
        class ContainerEntity(BaseEntity):
            """
            Provide nested containers for recursive enum serialization tests.

            Parameters
            ----------
            colors : dict, optional
                Enum-keyed mapping containing palettes and tuples of swatches.
            """

            colors: dict[Color, list[Palette | tuple[Swatch]]] = field(
                default_factory=lambda: {
                    Color.RED: [Palette(Color.BLUE), (Swatch(Color.RED),)],
                },
            )

        entity = ContainerEntity()
        for colors in (entity.toDict()["colors"], entity.getFields()[0]["default"]):
            self.assertEqual(colors, {"red": [("blue",), ({"color": "red"},)]})
            self.assertIsInstance(colors["red"][0], Palette)

    def testSlottedEntityDoesNotInheritAnInstanceDictionary(self) -> None:
        """
        Verify that slotted entities lack an instance dictionary.

        Returns
        -------
        None
            Check declared-field serialization and expect ``TypeError`` for
            an extra keyword.
        """

        @dataclass(init=False, slots=True)
        class SlottedEntity(BaseEntity):
            """
            Provide a slotted fixture that uses the shared constructor.

            Parameters
            ----------
            value : int, optional
                Value stored in the declared slot. Defaults to ``1``.
            """

            value: int = 1

        entity = SlottedEntity()
        self.assertFalse(hasattr(entity, "__dict__"))
        self.assertEqual(entity.toDict(), {"value": 1})
        with self.assertRaisesRegex(TypeError, "cannot store dynamic attributes"):
            SlottedEntity(extra=True)

    def testDynamicAttributesAreSerializedAndDescribedPerInstance(self) -> None:
        """
        Verify serialization and optional field descriptions for public extras.

        Returns
        -------
        None
            Check for copied nested values, omitted private extras, and
            per-instance type descriptions when requested.
        """
        entity = EmptyEntity(labels=[Color.RED])
        vars(entity)["_private"] = "excluded"

        result = EmptyEntity(inner=entity).toDict()
        self.assertEqual(result, {"inner": {"labels": ["red"]}})
        result["inner"]["labels"].append("blue")
        self.assertEqual(vars(entity)["labels"], [Color.RED])

        self.assertEqual(entity.getFields(), [])
        self.assertEqual(
            entity.getFields(include_dynamic=True),
            [
                {
                    "name": "labels",
                    "types": ["list"],
                    "default": None,
                    "metadata": {"dynamic": True},
                },
            ],
        )
        self.assertEqual(
            EmptyEntity(labels=1).getFields(include_dynamic=True)[0]["types"],
            ["int"],
        )
        self.assertEqual(EmptyEntity().getFields(include_dynamic=True), [])

    def testSharedConstructorInitializesFieldsBeforePostInit(self) -> None:
        """
        Verify that the shared constructor sets fields before post-init.

        Returns
        -------
        None
            Check that the hook sees initialized fields and extras and that
            each instance receives a separate factory default.
        """

        @dataclass(frozen=True, init=False)
        class SharedEntity(BaseEntity):
            """
            Exercise post-init on a frozen entity with fields and extras.

            Parameters
            ----------
            name : str
                Name used in the private label.
            enabled : bool, optional
                Flag that defaults to ``True``.
            items : list of int, optional
                Values to store. Omit to use a new empty list.
            tag : str
                Extra keyword used in the private label.
            """

            name: str
            enabled: bool = True
            items: list[int] = field(default_factory=list)
            fixed: str = field(init=False, default="fixed")
            _label: str = field(init=False)

            def __post_init__(self) -> None:
                """
                Build the private label from the name, fixed value, and tag.

                Returns
                -------
                None
                    Assign the label on the frozen instance.
                """
                label = f"{self.name}:{self.fixed}:{vars(self)['tag']}"
                object.__setattr__(self, "_label", label)

        entity = SharedEntity(name="orionis", enabled=False, tag="blue")
        other = SharedEntity(name="other", tag="red")
        entity.items.append(1)
        self.assertEqual(other.items, [])
        self.assertEqual(
            entity.toDict(),
            {
                "name": "orionis",
                "enabled": False,
                "items": [1],
                "fixed": "fixed",
                "_label": "orionis:fixed:blue",
                "tag": "blue",
            },
        )

    def testSharedConstructorRejectsInvalidInputsBeforeCallingFactories(self) -> None:
        """
        Verify that invalid constructor inputs prevent factory calls.

        Returns
        -------
        None
            Check that missing required fields, ``init=False`` overrides, and
            invalid or reserved extras raise ``TypeError``. Also check that
            ``BaseEntity`` cannot be constructed directly.
        """
        calls: list[str] = []

        def make_items() -> list[int]:
            """
            Record a default factory call and return an empty list.

            Returns
            -------
            list of int
                A new list for the ``items`` field.
            """
            calls.append("items")
            return []

        @dataclass(init=False)
        class SharedEntity(BaseEntity):
            """
            Combine a tracked factory with required and non-init fields.

            Parameters
            ----------
            items : list of int, optional
                Values that bypass the tracked factory when supplied.
            required : int
                Value the caller must supply to construct the entity.
            """

            items: list[int] = field(default_factory=make_items)
            required: int
            fixed: int = field(init=False, default=1)

        cases = (
            ({}, "Missing required argument: 'required'"),
            ({"required": 1, "fixed": 2}, "has init=False"),
            ({"required": 1, "invalid-name": 2}, "Invalid attribute name"),
            ({"required": 1, "for": 2}, "Invalid attribute name"),
            ({"required": 1, "_private": 2}, "Reserved attribute name"),
            ({"required": 1, "toDict": 2}, "Reserved attribute name"),
        )
        for kwargs, message in cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaisesRegex(TypeError, message),
            ):
                SharedEntity(**kwargs)

        self.assertEqual(calls, [])
        with self.assertRaisesRegex(TypeError, "must be decorated with dataclass"):
            BaseEntity()

    # ------------------------------------------------ getFields - basic

    def testGetFieldsReturnsList(self) -> None:
        """
        Verify the return type of ``getFields()``.

        Returns
        -------
        None
            Assert that the field descriptions for a basic entity form a list.
        """
        entity = SimpleEntity()
        self.assertIsInstance(entity.getFields(), list)

    def testGetFieldsCountMatchesDataclassFields(self) -> None:
        """
        Verify that ``getFields()`` returns one entry per declared field.

        Returns
        -------
        None
            Compare the result length with the fixture's three fields.
        """
        entity = SimpleEntity()
        result = entity.getFields()
        self.assertEqual(len(result), 3)

    def testGetFieldsContainsRequiredKeys(self) -> None:
        """
        Verify the structure of each field description.

        Returns
        -------
        None
            Check for ``name``, ``types``, ``default``, and ``metadata`` keys.
        """
        entity = SimpleEntity()
        for entry in entity.getFields():
            self.assertIn("name", entry)
            self.assertIn("types", entry)
            self.assertIn("default", entry)
            self.assertIn("metadata", entry)

    def testGetFieldsNameMatchesDeclaredField(self) -> None:
        """
        Verify that field descriptions include every declared name.

        Returns
        -------
        None
            Check that the names include ``name``, ``count``, and ``active``.
        """
        entity = SimpleEntity()
        names = [f["name"] for f in entity.getFields()]
        self.assertIn("name", names)
        self.assertIn("count", names)
        self.assertIn("active", names)

    def testGetFieldsTypesIsAlwaysList(self) -> None:
        """
        Verify that type descriptions use lists.

        Returns
        -------
        None
            Check the ``types`` entry for each scalar field.
        """
        entity = SimpleEntity()
        for entry in entity.getFields():
            self.assertIsInstance(entry["types"], list)

    def testGetFieldsSimpleTypeContainsTypeName(self) -> None:
        """
        Verify the reported type name for an integer field.

        Returns
        -------
        None
            Check that the ``count`` field includes ``int`` in its type list.
        """
        entity = SimpleEntity()
        count_field = next(f for f in entity.getFields() if f["name"] == "count")
        self.assertIn("int", count_field["types"])

    def testGetFieldsDefaultValueReflectsDeclared(self) -> None:
        """
        Verify that a string field reports its declared default.

        Returns
        -------
        None
            Assert that the default for ``name`` is ``"default"``.
        """
        entity = SimpleEntity()
        name_field = next(f for f in entity.getFields() if f["name"] == "name")
        self.assertEqual(name_field["default"], "default")

    def testGetFieldsDefaultForIntField(self) -> None:
        """
        Verify the reported default for an integer field.

        Returns
        -------
        None
            Assert that the default for ``count`` is ``0``.
        """
        entity = SimpleEntity()
        count_field = next(f for f in entity.getFields() if f["name"] == "count")
        self.assertEqual(count_field["default"], 0)

    def testGetFieldsDefaultFactory(self) -> None:
        """
        Verify that a list field reports its factory result as the default.

        Returns
        -------
        None
            Check that ``items`` reports an empty list rather than ``None``.
        """
        entity = FactoryEntity()
        items_field = next(f for f in entity.getFields() if f["name"] == "items")
        self.assertEqual(items_field["default"], [])

    def testGetFieldsMetadataIsDict(self) -> None:
        """
        Verify the type of the metadata in each field description.

        Returns
        -------
        None
            Assert that every ``metadata`` entry is a dictionary.
        """
        entity = SimpleEntity()
        for entry in entity.getFields():
            self.assertIsInstance(entry["metadata"], dict)

    def testGetFieldsEmptyMetadataForPlainField(self) -> None:
        """
        Verify the metadata default for a plain field.

        Returns
        -------
        None
            Assert that the ``name`` field has an empty metadata dictionary.
        """
        entity = SimpleEntity()
        name_field = next(f for f in entity.getFields() if f["name"] == "name")
        self.assertEqual(name_field["metadata"], {})

    def testGetFieldsMetadataPreservesCustomKeys(self) -> None:
        """
        Verify that field descriptions preserve custom metadata.

        Returns
        -------
        None
            Check that the ``score`` field retains its ``"Score"`` label.
        """
        entity = MetadataEntity()
        score_field = next(f for f in entity.getFields() if f["name"] == "score")
        self.assertIn("label", score_field["metadata"])
        self.assertEqual(score_field["metadata"]["label"], "Score")

    def testGetFieldsDeclaredDefaultTakesPrecedenceOverMetadata(self) -> None:
        """
        Verify that the declared default takes precedence over metadata.

        Returns
        -------
        None
            Check that ``score`` reports ``0`` instead of the metadata's ``42``.
        """
        entity = MetadataEntity()
        score_field = next(f for f in entity.getFields() if f["name"] == "score")
        # field.default = 0, so 'default' is taken from field.default
        self.assertEqual(score_field["default"], 0)

    # ------------------------------------------------ getFields - enum

    def testGetFieldsEnumDefaultIsSerializedValue(self) -> None:
        """
        Verify serialization of an enum field's default.

        Returns
        -------
        None
            Check for the string ``"red"`` rather than ``Color.RED``.
        """
        entity = EnumEntity()
        color_field = next(f for f in entity.getFields() if f["name"] == "color")
        self.assertEqual(color_field["default"], "red")
        self.assertNotIsInstance(color_field["default"], Enum)

    # ------------------------------------------------ getFields - union types

    def testGetFieldsUnionTypeReturnsMultipleTypes(self) -> None:
        """
        Verify that a union annotation produces multiple type entries.

        Returns
        -------
        None
            Check the number of types reported for ``int | None``.
        """
        entity = NullableEntity()
        value_field = next(f for f in entity.getFields() if f["name"] == "value")
        self.assertGreater(len(value_field["types"]), 1)

    def testGetFieldsUnionTypeContainsIntAndNone(self) -> None:
        """
        Verify that a nullable field describes both union members.

        Returns
        -------
        None
            Check that the combined type strings contain ``int`` and ``None``.
        """
        entity = NullableEntity()
        value_field = next(f for f in entity.getFields() if f["name"] == "value")
        types_str = " ".join(value_field["types"])
        self.assertIn("int", types_str)
        self.assertIn("None", types_str)

    # ------------------------------------------------ getFields - empty entity

    def testGetFieldsEmptyEntityReturnsList(self) -> None:
        """
        Verify field descriptions for an entity with no fields.

        Returns
        -------
        None
            Assert that ``getFields()`` returns an empty list.
        """
        entity = EmptyEntity()
        self.assertEqual(entity.getFields(), [])

    # ------------------------------------------------ nested entity

    def testToDictNestedEntityIsConverted(self) -> None:
        """
        Verify that serialization descends into a nested entity.

        Returns
        -------
        None
            Check that ``inner`` is a dictionary containing ``name``.
        """
        entity = NestedEntity()
        result = entity.toDict()
        self.assertIsInstance(result["inner"], dict)
        self.assertIn("name", result["inner"])

    def testGetFieldsNestedEntityDefaultIsDict(self) -> None:
        """
        Verify that field descriptions serialize nested defaults.

        Returns
        -------
        None
            Check that ``inner`` reports a dictionary as its default.
        """
        entity = NestedEntity()
        inner_field = next(f for f in entity.getFields() if f["name"] == "inner")
        self.assertIsInstance(inner_field["default"], dict)

    # ---------------------------------------- inheritance / extensibility

    def testSubclassCanOverridePostInit(self) -> None:
        """
        Verify that a subclass can validate values in its post-init hook.

        Returns
        -------
        None
            Check that construction accepts a positive value and rejects a
            negative one with ``ValueError``.
        """

        @dataclass
        class ValidatedEntity(BaseEntity):
            """
            Provide a fixture that rejects a negative value during post-init.

            Parameters
            ----------
            value : int, optional
                Value to validate. Defaults to ``0``.
            """

            value: int = 0

            def __post_init__(self) -> None:
                """
                Reject a negative value after initialization.

                Returns
                -------
                None
                    Leave non-negative values unchanged.

                Raises
                ------
                ValueError
                    If the initialized value is negative.
                """
                if self.value < 0:
                    error_msg = "value must be non-negative"
                    raise ValueError(error_msg)

        valid = ValidatedEntity(value=5)
        self.assertEqual(valid.value, 5)
        with self.assertRaises(ValueError):
            ValidatedEntity(value=-1)

    def testToDictPreservesTypesAfterUpdate(self) -> None:
        """
        Verify that serialization reflects an integer field update.

        Returns
        -------
        None
            Check that the serialized count matches the value assigned later.
        """
        entity = SimpleEntity(count=1)
        entity.count = 42
        result = entity.toDict()
        self.assertEqual(result["count"], 42)
