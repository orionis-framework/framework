from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from typing import NoReturn
from orionis.orm.relations.has_many import HasManyRelation
from orionis.orm.relations.relation import Relation
from orionis.support.types.collection import Collection
from orionis.test import TestCase
from tests.orm.relations import test_mixin as fixtures

def _raise_relation_error() -> NoReturn:
    """Reject construction of the relation template.

    Returns
    -------
    NoReturn
        Always raise the deliberate construction error.

    Raises
    ------
    ValueError
        Indicate that the relation factory failed.
    """
    error_msg = "Relation factory failed."
    raise ValueError(error_msg)

class _QueryRejectingHasMany(HasManyRelation[fixtures.Book]):
    """Reject any query attempted for a keyless eager batch."""

    __slots__ = ()

    async def get(self) -> Collection:
        """Reject execution of an unexpected related query.

        Returns
        -------
        Collection
            Never return a result because querying this fixture is forbidden.

        Raises
        ------
        AssertionError
            Indicate that a keyless batch reached query execution.
        """
        error_msg = "A keyless batch must not execute a related query."
        raise AssertionError(error_msg)

class TestRelationAwait(fixtures._RelationsTestCase):
    async def testAwaitShortcutEquivalentToGet(self) -> None:
        """Await a relationship directly without a terminal method.

        Validates the ``Relation.__await__`` ergonomic shortcut.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await fixtures.Author.create({"name": "Ana"})
        await fixtures.Book.create({"title": "One", "author_id": author.id})

        books = await author.books()
        self.assertEqual(len(books), 1)

class TestRelationConstraints(TestCase):
    """Check terminal guards and execution-context isolation."""

    def testConstraintSuppressionIsIsolatedBetweenThreads(self) -> None:
        """Keep parent constraints on relationships built by another thread.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parent = fixtures.Author({"id": 9, "name": "author"})
        with ThreadPoolExecutor(max_workers=1) as executor:

            def build_template() -> HasManyRelation[fixtures.Book]:
                """Resolve a query while the parent thread holds the scope context.

                Returns
                -------
                HasManyRelation
                    Relationship created in the current execution context.
                """
                constrained = executor.submit(parent.books).result(timeout=5)
                self.assertEqual(len(constrained.toPlan().wheres), 1)
                self.assertEqual(constrained.toPlan().wheres[0].value, 9)
                return parent.books()

            template = Relation.noConstraints(build_template)
        self.assertEqual(template.toPlan().wheres, [])
        self.assertEqual(len(parent.books().toPlan().wheres), 1)

    def testConstraintSuppressionRestoresAfterFailure(self) -> None:
        """Restore parent constraints when the relation factory raises.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parent = fixtures.Author({"id": 9, "name": "author"})
        with self.assertRaises(ValueError):
            Relation.noConstraints(_raise_relation_error)
        self.assertEqual(len(parent.books().toPlan().wheres), 1)

    async def testKeylessEagerBatchSkipsRelatedQuery(self) -> None:
        """Return an empty related set without querying a keyless batch.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        parent = fixtures.Author({"name": "author"})
        relation = Relation.noConstraints(
            lambda: _QueryRejectingHasMany(parent, fixtures.Book, "author_id", "id"),
        )
        relation.addEagerConstraints([parent])
        self.assertEqual(len(await relation.getEager()), 0)

    def testTemplateMethodsRequireConcreteImplementations(self) -> None:
        """Reject unimplemented constraint and result matching hooks.

        Returns
        -------
        None
            Verify each synchronous template hook raises NotImplementedError.
        """
        parent = fixtures.Author({"id": 9, "name": "author"})
        relation = Relation.noConstraints(lambda: Relation(parent, fixtures.Book))
        with self.assertRaises(NotImplementedError):
            relation.addConstraints()
        with self.assertRaises(NotImplementedError):
            relation.addEagerConstraints([parent])
        with self.assertRaises(NotImplementedError):
            relation.match([parent], Collection(), "books")

    async def testResultHookRequiresAConcreteImplementation(self) -> None:
        """Reject execution of the unimplemented result hook.

        Returns
        -------
        None
            Verify awaiting the base result hook raises NotImplementedError.
        """
        parent = fixtures.Author({"id": 9, "name": "author"})
        relation = Relation.noConstraints(lambda: Relation(parent, fixtures.Book))
        with self.assertRaises(NotImplementedError):
            await relation.getResults()
