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
        """Yield before checking a sibling on the converted child instance."""
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
        """Retain the decoded body used by schema injection."""
        self._data = data

    async def data(self) -> dict[str, object]:
        """Return the body supplied by the test."""
        return self._data


class _AccountController(BaseController):
    async def __call__(self, payload: _Account) -> dict:
        """Return the direct nested schema only after container validation."""
        return payload.toDict()


class _ListController(BaseController):
    async def __call__(self, payload: _ListAccount) -> dict:
        """Return the schema collection only after container validation."""
        return payload.toDict()


class TestSchemaCollections(TestCase):
    async def testDirectNestedSchemaStillRunsItsRules(self) -> None:
        """Preserve validation of a directly declared child schema."""
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"contact": {"email": "invalid"}}, _Account)
        self.assertEqual(set(caught.exception.errors), {"contact.email"})

    async def testListRunsEveryChildRule(self) -> None:
        """Reject invalid children with distinct indexed paths."""
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
        """Retain dictionary keys instead of msgspec's anonymous placeholder."""
        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": {"primary": {"email": "invalid"}},
            }, _DictAccount)
        self.assertEqual(set(caught.exception.errors), {"contacts['primary'].email"})

    async def testValidCollectionsPreserveConversionAndInput(self) -> None:
        """Return typed children without mutating the caller's containers."""
        payload = {"contacts": [{"email": "ada@example.com"}]}
        result = await Validator.validate(payload, _ListAccount)
        self.assertIsInstance(result.contacts[0], _Contact)
        self.assertEqual(result.toDict()["contacts"], [
            {"email": "ada@example.com", "nickname": "guest"},
        ])
        self.assertEqual(payload, {"contacts": [{"email": "ada@example.com"}]})
        self.assertIsNot(result.contacts, payload["contacts"])

    async def testEmptyAndOptionalCollectionsAreAccepted(self) -> None:
        """Skip absent children without losing optional collection semantics."""
        class _Optional(Schema):
            contacts: list[_Contact | None] | None = None

        for payload in ({}, {"contacts": None}, {"contacts": []}, {"contacts": [None]}):
            self.assertIsInstance(
                await Validator.validate(payload, _Optional), _Optional,
            )

    async def testNestedAnnotatedCollectionsAreTraversed(self) -> None:
        """Follow annotations, optional children, maps and nested tuples."""
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
        """Cover concrete containers and msgspec-supported collection aliases."""
        for annotation in (
            tuple[_FrozenContact, ...], set[_FrozenContact],
            frozenset[_FrozenContact], Sequence[_FrozenContact],
            Collection[_FrozenContact], AbstractSet[_FrozenContact],
        ):
            with self.subTest(annotation=annotation):
                class _CollectionSchema(Schema):
                    contacts: annotation

                with self.assertRaises(ValidationException) as caught:
                    await Validator.validate({
                        "contacts": [{"email": "invalid"}],
                    }, _CollectionSchema)
                self.assertEqual(set(caught.exception.errors), {"contacts[0].email"})

    async def testMappingAliasAndCollectionUnionRunChildRules(self) -> None:
        """Select collection traversal from the converted runtime value."""
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
        """Traverse converted collections on the partial-conversion path."""
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
        """Validate unaffected items even when another child cannot convert."""
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
            caught.exception.errors["contacts[2].nickname"], ["Nickname is too short."],
        )

    async def testDictFailuresKeepKeysAndCustomMessages(self) -> None:
        """Preserve quoted keys, including punctuation, in both failure phases."""
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
            ["Nickname is too short."],
        )

    async def testFixedTupleUsesEachElementsDeclaredType(self) -> None:
        """Resolve errors and custom messages through the correct tuple member."""
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
            caught.exception.errors["contacts[1].nickname"], ["Nickname is too short."],
        )

    async def testCollectionBoundsAreNotHiddenByChildFailures(self) -> None:
        """Preserve the original collection constraint alongside child errors."""
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
            caught.exception.errors["contacts"], ["Three contacts required."],
        )

    async def testTupleLengthFailuresAreNotHiddenByChildRules(self) -> None:
        """Keep fixed-tuple length validation when a present child is invalid."""
        class _Tuple(Schema):
            contacts: tuple[_Contact, _PlainChild]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({"contacts": [{"email": "invalid"}]}, _Tuple)
        self.assertEqual(
            set(caught.exception.errors), {"contacts", "contacts[0].email"},
        )

    async def testTaggedChildUnionsKeepTheSelectedSchema(self) -> None:
        """Respect discriminators while collecting partially converted children."""
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
        """Never disguise an unexpected service error as a validation result."""
        class _FailingRule(Rule):
            async def enforce(
                self, _field: str, _value: object, _instance: object,
            ) -> bool:
                """Simulate an unavailable application service."""
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
        """Resolve messages from the selected child, not the first union member."""
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
            ["Second child label is too short."],
        )

        class _CollectionUnion(Schema):
            contacts: list[_First] | dict[str, _Second]

        with self.assertRaises(ValidationException) as caught:
            await Validator.validate({
                "contacts": {"main": {"type": "second", "label": "x"}},
            }, _CollectionUnion)
        self.assertEqual(
            caught.exception.errors["contacts['main'].label"],
            ["Second child label is too short."],
        )

    async def testChildRulesReadChildSiblingsOnBothConversionPaths(self) -> None:
        """Keep sibling-field checks local to each child inside a collection."""
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
        """Await child predicates rather than treating coroutine objects as true."""
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
        """Exercise the controller contract through real request injection."""
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
