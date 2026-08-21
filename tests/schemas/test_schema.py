from typing import Annotated, get_args, get_origin
import msgspec
from orionis.schemas.constraints import (
    GreaterThan,
    MinLength,
    StrongPassword,
)
from orionis.schemas.metadata import Description, Message, Title
from orionis.schemas.schema import Schema, SchemaMeta
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Schema fixtures
# ---------------------------------------------------------------------------

class _BasicSchema(Schema):
    name: str
    age: int

class _DefaultSchema(Schema):
    label: str = "default"
    count: int = 0

class _AnnotatedSchema(Schema):
    score: Annotated[int, GreaterThan(0)]

class _WithDocMetaSchema(Schema):
    name: Annotated[str, Title("Full name"), Description("The person's full name.")]

class _RuleSchema(Schema):
    password: Annotated[str, StrongPassword()]

class _MultiAnnotationSchema(Schema):
    token: Annotated[str, MinLength(4), Message("Token too short.")]

class _NestedChild(Schema):
    city: str

class _ParentWithNested(Schema):
    child: _NestedChild
    count: int

class _FieldlessSchema(Schema):
    pass

class _DoubleMessageSchema(Schema):
    code: Annotated[str, Message("First message."), Message("Second message.")]

class TestSchemaMeta(TestCase):

    def testSchemaSubclassUsesSchemaMeta(self) -> None:
        """
        Confirm that Schema subclasses have SchemaMeta as their metaclass.

        Validates that user-defined Schema subclasses are processed by
        the SchemaMeta metaclass pipeline.
        """
        self.assertIsInstance(_BasicSchema, SchemaMeta)

    def testOrionisMataAttached(self) -> None:
        """
        Confirm __orionis_meta__ is attached to Schema subclasses.

        Validates that the SchemaMeta pipeline populates __orionis_meta__
        on the finished class.
        """
        self.assertTrue(hasattr(_BasicSchema, "__orionis_meta__"))

    def testOrionisConstraintsAttached(self) -> None:
        """
        Confirm __orionis_constraints__ is attached to Schema subclasses.

        Validates that the SchemaMeta pipeline populates
        __orionis_constraints__ on the finished class.
        """
        self.assertTrue(hasattr(_BasicSchema, "__orionis_constraints__"))

    def testSimpleSchemaHasNoOrionisMetaEntries(self) -> None:
        """
        Confirm plain Schema fields produce an empty __orionis_meta__.

        Validates that fields without Annotated metadata do not create
        entries in the __orionis_meta__ dictionary.
        """
        self.assertEqual(_BasicSchema.__orionis_meta__, {})

    def testAnnotatedConstraintIsEnforced(self) -> None:
        """
        Confirm Annotated constraints are enforced during schema validation.

        Validates that a GreaterThan(0) constraint rejects non-positive
        integers at the msgspec conversion level, demonstrating that the
        SchemaMeta pipeline compiled the constraint correctly.
        """
        with self.assertRaises(msgspec.ValidationError):
            msgspec.convert({"score": -1}, type=_AnnotatedSchema)

    def testDocumentMetadataCompiledIntoMsgspecMeta(self) -> None:
        """
        Confirm documentation metadata is compiled into the field's msgspec.Meta.

        Validates that Title and Description annotations are compiled by the
        SchemaMeta pipeline so the resulting struct field carries the
        corresponding msgspec.Meta attributes.
        """
        fields = {f.name: f for f in msgspec.structs.fields(_WithDocMetaSchema)}
        self.assertIn("name", fields)
        field_type = fields["name"].type
        # The field type must be Annotated wrapping a msgspec.Meta
        origin = get_origin(field_type)
        self.assertIs(origin, Annotated)
        args = get_args(field_type)
        meta_objs = [a for a in args[1:] if isinstance(a, msgspec.Meta)]
        self.assertTrue(len(meta_objs) > 0)
        self.assertEqual(meta_objs[0].title, "Full name")

    def testSchemaIsMsgspecStruct(self) -> None:
        """
        Confirm Schema subclasses are also msgspec.Struct instances.

        Validates that the Schema base class inherits from msgspec.Struct
        and instances pass isinstance checks accordingly.
        """
        instance = _BasicSchema(name="Alice", age=30)
        self.assertIsInstance(instance, msgspec.Struct)

    def testSchemaWithDefaultsIsCreatable(self) -> None:
        """
        Instantiate a Schema with default field values without arguments.

        Validates that default values on Schema fields are respected by
        the msgspec.Struct machinery.
        """
        instance = _DefaultSchema()
        self.assertEqual(instance.label, "default")
        self.assertEqual(instance.count, 0)

    def testCustomRuleMetadataAppendedInOrionisMeta(self) -> None:
        """
        Confirm that custom Rule instances appear in __orionis_meta__.

        Validates that a StrongPassword() rule attached via Annotated is
        collected into the class-level __orionis_meta__ for the field.
        """
        meta = _RuleSchema.__orionis_meta__
        self.assertIn("password", meta)
        rule_types = [type(item) for item in meta["password"]]
        self.assertIn(StrongPassword, rule_types)

    def testMessageMetadataStoredInOrionisConstraints(self) -> None:
        """
        Confirm Message metadata is stored in __orionis_constraints__.

        Validates that a Message() annotation is extracted by the SchemaMeta
        pipeline and stored under __orionis_constraints__ with the 'type'
        key rather than in __orionis_meta__.
        """
        constraints = _MultiAnnotationSchema.__orionis_constraints__
        self.assertIn("token", constraints)
        self.assertIn("type", constraints["token"])
        self.assertEqual(constraints["token"]["type"], "Token too short.")

    def testNestedSchemaBuildsMetaForParent(self) -> None:
        """
        Confirm that nested Schema fields are processed by SchemaMeta.

        Validates that __orionis_meta__ and __orionis_constraints__ are
        present on a parent schema containing a nested schema field.
        """
        self.assertTrue(hasattr(_ParentWithNested, "__orionis_meta__"))
        self.assertTrue(hasattr(_ParentWithNested, "__orionis_constraints__"))

    def testSchemaWithoutAnnotationsIsBuilt(self) -> None:
        """
        Build a schema declaring no annotated field at all.

        Validates that the metaclass tolerates a missing annotation
        callback instead of assuming every class declares fields.
        """
        self.assertEqual(_FieldlessSchema.__orionis_meta__, {})
        self.assertEqual(_FieldlessSchema.__orionis_constraints__, {})
        self.assertEqual(msgspec.structs.fields(_FieldlessSchema), ())

    def testOnlyTheFirstMessageMetadataIsKept(self) -> None:
        """
        Keep the first Message annotation when several are declared.

        Validates the single-pass classification of field metadata.
        """
        constraints = _DoubleMessageSchema.__orionis_constraints__
        self.assertEqual(constraints["code"]["type"], "First message.")

class TestSchemaInstantiation(TestCase):

    def testDirectInstantiationWithKeywordArguments(self) -> None:
        """
        Instantiate a Schema directly with keyword arguments.

        Validates that Schema subclasses can be constructed via keyword
        arguments without the Validator utility.
        """
        instance = _BasicSchema(name="Carol", age=28)
        self.assertEqual(instance.name, "Carol")
        self.assertEqual(instance.age, 28)

    def testSchemaFieldsAreAccessible(self) -> None:
        """
        Access Schema field values via attribute notation.

        Validates that declared fields are readable as standard Python
        attributes after construction.
        """
        instance = _DefaultSchema(label="custom", count=5)
        self.assertEqual(instance.label, "custom")
        self.assertEqual(instance.count, 5)

class TestSchemaInvalidCustomRule(TestCase):

    def testUnsupportedMetadataObjectRaisesTypeError(self) -> None:
        """
        Raise TypeError when an unsupported metadata object is used in Annotated.

        Validates that attaching an object that is neither a Rule nor a
        ValidationMetadata instance to a field raises TypeError during
        class creation.
        """

        class _BadMeta:
            pass

        with self.assertRaises(TypeError):

            class _BadSchema(Schema):
                field: Annotated[str, _BadMeta()]

class TestSchemaToDict(TestCase):

    def testToDictReturnsEveryField(self) -> None:
        """
        Convert a schema instance into a plain dictionary.

        Validates that every declared field reaches the returned mapping.
        """
        result = _BasicSchema(name="Alice", age=30).toDict()
        self.assertEqual(result, {"name": "Alice", "age": 30})

    def testToDictReflectsDefaultValues(self) -> None:
        """
        Include default field values in the converted dictionary.

        Validates that unset fields are exported with their fallback.
        """
        self.assertEqual(_DefaultSchema().toDict(), {"label": "default", "count": 0})

    def testToDictKeepsNestedSchemasAsInstances(self) -> None:
        """
        Keep nested schema values as instances in the dictionary.

        Validates that the conversion is shallow by design.
        """
        instance = _ParentWithNested(child=_NestedChild(city="Lima"), count=1)
        self.assertIsInstance(instance.toDict()["child"], _NestedChild)
