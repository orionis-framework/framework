import typing
import msgspec
from orionis.schemas import fields
from orionis.schemas.constraints import MinLength
from orionis.schemas.schema import Schema
from orionis.test import TestCase

# Schema annotations are resolved at run time by the metaclass, so the imports
# above must stay outside a type-checking block.
# ruff: noqa: TC001

# Literal alias declared outside the class body so the metaclass resolves it.
_Role = fields.Choice["admin", "user"]

class _AliasedSchema(Schema):
    name: fields.Field[str, MinLength(2)]
    role: _Role
    nickname: fields.Nullable[str] = None

class TestFieldAliases(TestCase):

    def testFieldIsAnnotated(self) -> None:
        """
        Alias ``Field`` to the annotated type constructor.

        Validates the alias used to attach metadata to a field type.
        """
        self.assertIs(fields.Field, typing.Annotated)

    def testChoiceIsLiteral(self) -> None:
        """
        Alias ``Choice`` to the literal type constructor.

        Validates the alias used to restrict a field to fixed values.
        """
        self.assertIs(fields.Choice, typing.Literal)

    def testNullableIsOptional(self) -> None:
        """
        Alias ``Nullable`` to the optional type constructor.

        Validates the alias used to allow ``None`` on a field.
        """
        self.assertIs(fields.Nullable, typing.Optional)

    def testAnyOfIsUnion(self) -> None:
        """
        Alias ``AnyOf`` to the union type constructor.

        Validates the alias used to accept several field types.
        """
        self.assertIs(fields.AnyOf, typing.Union)

    def testConstantIsFinal(self) -> None:
        """
        Alias ``Constant`` to the final type qualifier.

        Validates the alias used to forbid reassignment.
        """
        self.assertIs(fields.Constant, typing.Final)

    def testAliasIsTypeAlias(self) -> None:
        """
        Alias ``Alias`` to the type-alias qualifier.

        Validates the alias used to name a composite annotation.
        """
        self.assertIs(fields.Alias, typing.TypeAlias)

    def testStaticIsClassVar(self) -> None:
        """
        Alias ``Static`` to the class-variable qualifier.

        Validates the alias used to exclude an attribute from the fields.
        """
        self.assertIs(fields.Static, typing.ClassVar)

class TestFieldAliasesInSchemas(TestCase):

    def testAliasedAnnotationsBuildAUsableSchema(self) -> None:
        """
        Declare a schema entirely through the field aliases.

        Validates that the aliases behave like their typing counterparts
        once the metaclass compiles the annotations.
        """
        instance = _AliasedSchema(name="Alice", role="admin")
        self.assertEqual(instance.name, "Alice")
        self.assertEqual(instance.role, "admin")
        self.assertIsNone(instance.nickname)

    def testAliasedConstraintIsCompiled(self) -> None:
        """
        Compile the metadata supplied through the ``Field`` alias.

        Validates that constraints declared with the alias reach the
        generated field metadata.
        """
        declared = {f.name: f.type for f in msgspec.structs.fields(_AliasedSchema)}
        metas = [
            arg
            for arg in typing.get_args(declared["name"])[1:]
            if isinstance(arg, msgspec.Meta)
        ]
        self.assertEqual(metas[0].min_length, 2)

    def testAliasedChoiceRestrictsTheAcceptedValues(self) -> None:
        """
        Reject a value outside the literal alias declared for a field.

        Validates that the ``Choice`` alias narrows the field domain.
        """
        with self.assertRaises(msgspec.ValidationError):
            msgspec.convert({"name": "Alice", "role": "root"}, type=_AliasedSchema)
