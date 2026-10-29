import asyncio
from collections.abc import Collection, Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Annotated
from orionis.container.container import Container
from orionis.http.base import BaseController
from orionis.http.request import Request
from orionis.schemas import Schema
from orionis.schemas.constraints import ConfirmPassword, Email, MinLength
from orionis.schemas.exceptions import ValidationException
from orionis.schemas.fields import Field
from orionis.schemas.metadata import Title
from orionis.schemas.rule import Rule
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

# Schema annotations are evaluated at runtime by the metaclass.
# ruff: noqa: TC001


class _Contact(Schema):
    email: Field[str, Email(message="Invalid contact email.")]
    nickname: Field[str, MinLength(3, message="Nickname is too short.")] = "guest"


class _Account(Schema):
    contact: _Contact


class _ListAccount(Schema):
    contacts: list[_Contact]
    count: int = 1


class _DictAccount(Schema):
    contacts: dict[str, _Contact]
    count: int = 1


class _FrozenContact(Schema, frozen=True):
    email: Field[str, Email()]


class _PlainChild(Schema):
    label: str


class _TaggedEmailContact(Schema, tag="email"):
    email: Field[str, Email()]
    count: int = 1


class _TaggedPlainContact(Schema, tag="plain"):
    label: str


class _WaitingRule(Rule):
    __code__ = "waiting"
    __message__ = "Rejected after yielding."

    async def enforce(
        self, _field: str, _value: object, instance: object,
    ) -> bool:
        """
        Yield before checking a sibling on the converted child instance.

        Parameters
        ----------
        _field : str
            Unused name of the field under validation.
        _value : object
            Unused value of the field under validation.
        instance : object
            Converted child instance containing the sibling flag.

        Returns
        -------
        bool
            Whether the child instance's allowed flag permits validation.
        """
        await asyncio.sleep(0)
        return getattr(instance, "allowed", False)


class _AsyncChild(Schema):
    value: Field[str, _WaitingRule()]
    allowed: bool = False


class _SchemaContainer(Container):
    __slots__ = ()


class _SchemaRequest(Request):
    __slots__ = ("_data",)

    def __init__(self, data: dict[str, object]) -> None:
        """
        Retain the decoded body used by schema injection.

        Parameters
        ----------
        data : dict[str, object]
            Decoded request body supplied to schema injection.

        Returns
        -------
        None
            Store the supplied request body without converting it.
        """
        self._data = data

    async def data(self) -> dict[str, object]:
        """
        Return the body supplied by the test.

        Returns
        -------
        dict[str, object]
            Decoded request body retained by the request double.
        """
        return self._data


class _AccountController(BaseController):
    async def __call__(self, payload: _Account) -> dict:
        """
        Return the direct nested schema only after container validation.

        Parameters
        ----------
        payload : _Account
            Validated payload containing a directly nested schema.

        Returns
        -------
        dict
            Dictionary representation of the validated account payload.
        """
        return payload.toDict()


class _ListController(BaseController):
    async def __call__(self, payload: _ListAccount) -> dict:
        """
        Return the schema collection only after container validation.

        Parameters
        ----------
        payload : _ListAccount
            Validated payload containing a collection of schemas.

        Returns
        -------
        dict
            Dictionary representation of the validated schema collection.
        """
        return payload.toDict()


class TestSchemaCollections(TestCase):
    async def testDirectNestedSchemaStillRunsItsRules(self) -> None:
        """
        Preserve validation of a directly declared child schema.

        Returns
        -------
        None
            Assert rule execution for a directly nested schema.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"contact": {"email": "invalid"}}, _Account)
        self.assertEqual(set(caught.exception.errors), {"contact.email"})

    async def testListRunsEveryChildRule(self) -> None:
        """
        Reject invalid children with distinct indexed paths.

        Returns
        -------
        None
            Assert indexed validation errors for each invalid list child.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": [{"email": "invalid"}, {"email": "also-invalid"}],
            }, _ListAccount)
        self.assertEqual(
            set(caught.exception.errors), {"contacts[0].email", "contacts[1].email"},
        )
        self.assertEqual(
            [f.rule for f in caught.exception.failures], ["email", "email"],
        )

    async def testDictRunsRulesWithActualKeys(self) -> None:
        """
        Retain dictionary keys instead of msgspec's anonymous placeholder.

        Returns
        -------
        None
            Assert validation paths containing the actual dictionary keys.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": {"primary": {"email": "invalid"}},
            }, _DictAccount)
        self.assertEqual(set(caught.exception.errors), {"contacts['primary'].email"})

    async def testValidCollectionsPreserveConversionAndInput(self) -> None:
        """
        Return typed children without mutating the caller's containers.

        Returns
        -------
        None
            Assert typed conversion without mutation of caller containers.
        """
        payload = {"contacts": [{"email": "ada@example.com"}]}
        result = await Validator.validate(payload, _ListAccount)
        self.assertIsInstance(result.contacts[0], _Contact)
        self.assertEqual(result.toDict()["contacts"], [
            {"email": "ada@example.com", "nickname": "guest"},
        ])
        self.assertEqual(payload, {"contacts": [{"email": "ada@example.com"}]})
        self.assertIsNot(result.contacts, payload["contacts"])

    async def testEmptyAndOptionalCollectionsAreAccepted(self) -> None:
        """
        Skip absent children without losing optional collection semantics.

        Returns
        -------
        None
            Assert acceptance of empty and absent optional collections.
        """
        class _Optional(Schema):
            contacts: list[_Contact | None] | None = None

        for payload in ({}, {"contacts": None}, {"contacts": []}, {"contacts": [None]}):
            self.assertIsInstance(
                await Validator.validate(payload, _Optional), _Optional,
            )

    async def testNestedAnnotatedCollectionsAreTraversed(self) -> None:
        """
        Follow annotations, optional children, maps and nested tuples.

        Returns
        -------
        None
            Assert traversal through annotated nested collection types.
        """
        class _Nested(Schema):
            contacts: Annotated[
                list[dict[str, tuple[
                    Annotated[_Contact, Title("Contact")] | None, ...,
                ]]],
                Title("Contacts"),
            ]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": [{"main": [None, {"email": "invalid"}]}],
            }, _Nested)
        self.assertEqual(
            set(caught.exception.errors), {"contacts[0]['main'][1].email"},
        )

    async def testEverySupportedCollectionRunsChildRules(self) -> None:
        """
        Cover concrete containers and msgspec-supported collection aliases.

        Returns
        -------
        None
            Assert child-rule execution for every supported collection form.
        """
        for annotation in (
            tuple[_FrozenContact, ...], set[_FrozenContact],
            frozenset[_FrozenContact], Sequence[_FrozenContact],
            Collection[_FrozenContact], AbstractSet[_FrozenContact],
        ):
            with self.subTest(annotation=annotation):
                class _CollectionSchema(Schema):
                    contacts: annotation  # pyright: ignore[reportInvalidTypeForm]

                with self.assertRaises(ValidationException) as caught:
                    await Validator.validate({
                        "contacts": [{"email": "invalid"}],
                    }, _CollectionSchema)
                self.assertEqual(set(caught.exception.errors), {"contacts[0].email"})

    async def testMappingAliasAndCollectionUnionRunChildRules(self) -> None:
        """
        Select collection traversal from the converted runtime value.

        Returns
        -------
        None
            Assert traversal of the selected runtime collection type.
        """
        class _UnionAccount(Schema):
            contacts: list[_Contact] | Mapping[str, _Contact]

        for contacts, path in (
            ([{"email": "invalid"}], "contacts[0].email"),
            ({"main": {"email": "invalid"}}, "contacts['main'].email"),
        ):
            with (
                self.subTest(path=path),
                self.assertRaises(ValidationException) as caught,
            ):
                await Validator.validate({"contacts": contacts}, _UnionAccount)
            self.assertEqual(set(caught.exception.errors), {path})

    async def testSiblingTypeErrorsStillRunCollectionRules(self) -> None:
        """
        Traverse converted collections on the partial-conversion path.

        Returns
        -------
        None
            Assert collection-rule execution after a sibling conversion error.
        """
        for schema, contacts, path in (
            (_ListAccount, [{"email": "invalid"}], "contacts[0].email"),
            (_DictAccount, {"main": {"email": "invalid"}}, "contacts['main'].email"),
        ):
            with (
                self.subTest(schema=schema),
                self.assertRaises(ValidationException) as caught,
            ):
                await Validator.validate({"contacts": contacts, "count": "bad"}, schema)
            self.assertEqual(set(caught.exception.errors), {path, "count"})

    async def testListTypeConstraintAndRuleFailuresAreCollectedTogether(self) -> None:
        """
        Verify that list items report type, constraint, and rule failures together.

        Returns
        -------
        None
            Assert indexed field paths and structured constraint details.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": [
                    {"email": 42},
                    {"email": "invalid"},
                    {"email": "ada@example.com", "nickname": "x"},
                ],
            }, _ListAccount)
        self.assertEqual(
            {(f.field, f.rule) for f in caught.exception.failures},
            {
                ("contacts[0].email", "type"),
                ("contacts[1].email", "email"),
                ("contacts[2].nickname", "min_length"),
            },
        )
        self.assertEqual(
            caught.exception.errors["contacts[2].nickname"],
            [{"rule": "min_length", "message": "Nickname is too short."}],
        )

    async def testDictFailuresKeepKeysAndCustomMessages(self) -> None:
        """
        Verify that dictionary errors preserve quoted keys and custom messages.

        Returns
        -------
        None
            Assert indexed key paths and the custom constraint code and message.
        """
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": {
                    "a.b']": {"email": "ada@example.com", "nickname": "x"},
                    "wrong_type": {"email": 42},
                    "invalid": {"email": "invalid"},
                },
            }, _DictAccount)
        self.assertEqual(set(caught.exception.errors), {
            "contacts[\"a.b']\"].nickname",
            "contacts['wrong_type'].email",
            "contacts['invalid'].email",
        })
        self.assertEqual(
            caught.exception.errors["contacts[\"a.b']\"].nickname"],
            [{"rule": "min_length", "message": "Nickname is too short."}],
        )

    async def testFixedTupleUsesEachElementsDeclaredType(self) -> None:
        """
        Verify that each tuple member uses its declared validation type.

        Returns
        -------
        None
            Assert member-specific error paths, rule codes, and custom messages.
        """
        class _TupleAccount(Schema):
            contacts: tuple[_PlainChild, _Contact]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": [
                    {"label": "plain"},
                    {"email": "invalid", "nickname": "x"},
                ],
            }, _TupleAccount)
        self.assertEqual(set(caught.exception.errors), {
            "contacts[1].nickname", "contacts[1].email",
        })
        self.assertEqual(
            caught.exception.errors["contacts[1].nickname"],
            [{"rule": "min_length", "message": "Nickname is too short."}],
        )

    async def testCollectionBoundsAreNotHiddenByChildFailures(self) -> None:
        """
        Verify that collection bounds remain visible alongside child failures.

        Returns
        -------
        None
            Assert the collection's structured length error and nested failures.
        """
        class _Bounded(Schema):
            contacts: Field[
                list[_Contact], MinLength(3, message="Three contacts required."),
            ]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": [{"email": 42}, {"email": "invalid"}],
            }, _Bounded)
        self.assertEqual(set(caught.exception.errors), {
            "contacts", "contacts[0].email", "contacts[1].email",
        })
        self.assertEqual(
            caught.exception.errors["contacts"],
            [{"rule": "min_length", "message": "Three contacts required."}],
        )

    async def testTupleLengthFailuresAreNotHiddenByChildRules(self) -> None:
        """
        Keep fixed-tuple length validation when a present child is invalid.

        Returns
        -------
        None
            Assert tuple-length errors alongside child-rule failures.
        """
        class _Tuple(Schema):
            contacts: tuple[_Contact, _PlainChild]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"contacts": [{"email": "invalid"}]}, _Tuple)
        self.assertEqual(
            set(caught.exception.errors), {"contacts", "contacts[0].email"},
        )

    async def testTaggedChildUnionsKeepTheSelectedSchema(self) -> None:
        """
        Respect discriminators while collecting partially converted children.

        Returns
        -------
        None
            Assert discriminator-based selection of partially converted children.
        """
        class _Tagged(Schema):
            contacts: list[_TaggedPlainContact | _TaggedEmailContact]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": [
                    {"type": "plain", "label": 42},
                    {"type": "email", "email": "invalid", "count": "bad"},
                ],
            }, _Tagged)
        self.assertEqual(set(caught.exception.errors), {
            "contacts[0].label", "contacts[1].email", "contacts[1].count",
        })

    async def testUnexpectedChildRuleErrorsPropagate(self) -> None:
        """
        Propagate unexpected child service errors without hiding them.

        Returns
        -------
        None
            Assert propagation of unexpected errors from child services.
        """
        class _FailingRule(Rule):
            async def enforce(
                self, _field: str, _value: object, _instance: object,
            ) -> bool:
                """
                Simulate an unavailable application service.

                Parameters
                ----------
                _field : str
                    Unused name of the field under validation.
                _value : object
                    Unused value of the field under validation.
                _instance : object
                    Unused schema instance containing the field.

                Raises
                ------
                RuntimeError
                    Always raised to simulate an unavailable child service.
                """
                message = "Child service unavailable."
                raise RuntimeError(message)

        class _FailingChild(Schema):
            value: Field[str, _FailingRule()]

        class _FailingCollection(Schema):
            contacts: list[_FailingChild]
            count: int

        for count in (1, "bad"):
            with self.assertRaisesRegex(RuntimeError, "Child service unavailable"):
                await Validator.validate({
                    "contacts": [{"value": "any"}], "count": count,
                }, _FailingCollection)

    async def testUnionChildrenUseTheirOwnConstraintMessages(self) -> None:
        """
        Verify that union errors use the selected child's constraint messages.

        Returns
        -------
        None
            Assert the selected member's code and message in lists and mappings.
        """
        class _First(Schema, tag="first"):
            label: Field[str, MinLength(3, message="First child label is too short.")]

        class _Second(Schema, tag="second"):
            label: Field[str, MinLength(3, message="Second child label is too short.")]

        class _TaggedCollection(Schema):
            contacts: list[_First | _Second]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": [{"type": "second", "label": "x"}],
            }, _TaggedCollection)
        self.assertEqual(
            caught.exception.errors["contacts[0].label"],
            [{"rule": "min_length", "message": "Second child label is too short."}],
        )

        class _CollectionUnion(Schema):
            contacts: list[_First] | dict[str, _Second]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": {"main": {"type": "second", "label": "x"}},
            }, _CollectionUnion)
        self.assertEqual(
            caught.exception.errors["contacts['main'].label"],
            [{"rule": "min_length", "message": "Second child label is too short."}],
        )

    async def testChildRulesReadChildSiblingsOnBothConversionPaths(self) -> None:
        """
        Keep sibling-field checks local to each child inside a collection.

        Returns
        -------
        None
            Assert sibling-field checks against each converted child instance.
        """
        class _Confirmation(Schema):
            original: str
            confirmation: Field[str, ConfirmPassword("original")]

        class _Confirmations(Schema):
            contacts: list[_Confirmation]
            count: int

        for count in (1, "bad"):
            with (
                self.subTest(count=count),
                self.assertRaises(ValidationException) as caught,
            ):
                await Validator.validate({
                    "contacts": [{"original": "first", "confirmation": "second"}],
                    "count": count,
                }, _Confirmations)
            self.assertIn("contacts[0].confirmation", caught.exception.errors)
            self.assertEqual("count" in caught.exception.errors, count == "bad")

    async def testAsyncChildRulesAreAwaitedOnBothConversionPaths(self) -> None:
        """
        Await child predicates rather than treating coroutine objects as true.

        Returns
        -------
        None
            Assert awaited child rules on both conversion paths.
        """
        class _AsyncCollection(Schema):
            contacts: list[_AsyncChild]
            count: int

        for count in (1, "bad"):
            with (
                self.subTest(count=count),
                self.assertRaises(ValidationException) as caught,
            ):
                await Validator.validate({
                    "contacts": [{"value": "any", "allowed": False}], "count": count,
                }, _AsyncCollection)
            self.assertIn("contacts[0].value", caught.exception.errors)

    async def testContainerAwaitsDirectAndCollectedControllerSchemas(self) -> None:
        """
        Exercise the controller contract through real request injection.

        Returns
        -------
        None
            Assert validated controller schemas through real request injection.
        """
        container = _SchemaContainer()
        try:
            for controller, payload, path in (
                (
                    _AccountController(), {"contact": {"email": "invalid"}},
                    "contact.email",
                ),
                (
                    _ListController(), {"contacts": [{"email": "invalid"}]},
                    "contacts[0].email",
                ),
            ):
                async with container.beginScope():
                    container.instance(Request, _SchemaRequest(payload))
                    with self.assertRaises(ValidationException) as caught:
                        await container.invoke(controller.__call__)
                    self.assertEqual(set(caught.exception.errors), {path})
        finally:
            Container._instances.pop(_SchemaContainer, None)
