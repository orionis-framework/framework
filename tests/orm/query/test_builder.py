from __future__ import annotations
from typing import TYPE_CHECKING
import tests.orm.query.test_base_builder as language_fixtures
import tests.orm.query.test_base_builder as plan_fixtures
import tests.orm.relations.test_mixin as relation_fixtures
import tests.orm.test_events as feature_fixtures
from orionis.database.compiler import SQLCompiler
from orionis.orm.contracts.builder import IModelQueryBuilder
from orionis.orm.exceptions import InvalidQueryException, ScopeNotFoundException
from orionis.orm.query.base_builder import QueryBuilderBase
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.orm.query.raw_builder import RawQueryBuilder
from orionis.support.facades.db import DB
from orionis.test import TestCase
from tests.orm.relations import test_mixin as fixtures

if TYPE_CHECKING:
    from sqlalchemy.sql.selectable import CompoundSelect, Select
    from orionis.orm.query.expressions import SelectPlan

class _RecordingCompiler(SQLCompiler):
    """Count SELECT plans passed through the real SQL compiler."""

    __slots__ = ("select_count",)

    def __init__(self) -> None:
        """Initialize ordinary compilation and the query counter.

        Returns
        -------
        None
            Prepare an independent compiler for the current test connection.
        """
        super().__init__()
        self.select_count = 0

    def compileSelect(self, plan: SelectPlan) -> Select[object] | CompoundSelect:
        """Count and compile the supplied SELECT plan.

        Parameters
        ----------
        plan : SelectPlan
            Query plan about to be executed by the connection.

        Returns
        -------
        Select or CompoundSelect
            Statement produced by the normal compiler implementation.
        """
        self.select_count += 1
        return super().compileSelect(plan)

class TestEagerLoading(relation_fixtures._RelationsTestCase):
    async def testWithLoadsHasManyForEveryModel(self) -> None:
        """Eager load a hasMany relationship across an entire result set.

        Validates ``withRelations()`` populates ``getRelation()`` for every row.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        ana = await relation_fixtures.Author.create({"name": "Ana"})
        bob = await relation_fixtures.Author.create({"name": "Bob"})
        await relation_fixtures.Book.create(
            {"title": "Ana's book", "author_id": ana.id},
        )

        authors = (
            await relation_fixtures.Author.query()
            .withRelations("books")
            .orderBy("name")
            .get()
        )
        self.assertTrue(authors[0].relationLoaded("books"))
        self.assertTrue(authors[1].relationLoaded("books"))
        loaded_titles = [b.title for b in authors[0].getRelation("books")]
        self.assertEqual(loaded_titles, ["Ana's book"])
        self.assertEqual(list(authors[1].getRelation("books")), [])
        self.assertEqual(ana.name, authors[0].name)
        self.assertEqual(bob.name, authors[1].name)

    async def testLoadAliasBehavesIdenticallyToWith(self) -> None:
        """Use the ``load()`` alias interchangeably with ``withRelations()``.

        Validates both spellings resolve to the same eager-loading path.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.Book.create({"title": "One", "author_id": author.id})

        authors = await relation_fixtures.Author.query().load("books").get()
        self.assertEqual([b.title for b in authors[0].getRelation("books")], ["One"])

    async def testEagerLoadingAlsoWorksOnFirst(self) -> None:
        """Eager load a relationship when only the first row is fetched.

        Validates ``withRelations()`` integrates with the ``first()`` terminal.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.AuthorProfile.create(
            {"bio": "Bio", "author_id": author.id},
        )

        fetched = (
            await relation_fixtures.Author.query().withRelations("profile").first()
        )
        self.assertTrue(fetched.relationLoaded("profile"))
        self.assertEqual(fetched.getRelation("profile").bio, "Bio")

    async def testEagerLoadingMultipleRelationsAtOnce(self) -> None:
        """Eager load several relationships in a single call.

        Validates that ``withRelations()`` accepts multiple relationship names.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.Book.create({"title": "One", "author_id": author.id})
        await relation_fixtures.AuthorProfile.create(
            {"bio": "Bio", "author_id": author.id},
        )

        fetched = (
            await relation_fixtures.Author.query()
            .withRelations("books", "profile")
            .get()
        )[0]
        self.assertTrue(fetched.relationLoaded("books"))
        self.assertTrue(fetched.relationLoaded("profile"))

    async def testClassLevelForwardingForWith(self) -> None:
        """Start eager loading directly from the model class.

        Validates ``Model.withRelations(...)`` forwards to ``Model.query()``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.Book.create({"title": "One", "author_id": author.id})

        fetched = (await relation_fixtures.Author.withRelations("books").get())[0]
        self.assertTrue(fetched.relationLoaded("books"))

    async def testEagerLoadedBelongsTo(self) -> None:
        """Eager load an inverse belongsTo relationship.

        Validates eager loading works for the "many/one side" too.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        await relation_fixtures.Book.create({"title": "One", "author_id": author.id})

        books = await relation_fixtures.Book.query().withRelations("author").get()
        self.assertTrue(books[0].relationLoaded("author"))
        self.assertEqual(books[0].getRelation("author").name, "Ana")

    async def testEagerLoadedBelongsToMany(self) -> None:
        """Eager load a belongsToMany relationship across a result set.

        Validates that the pivot-backed relationship supports eager
        loading like the single-table relationship kinds.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        book = await relation_fixtures.Book.create({"title": "One"})
        fiction = await relation_fixtures.Tag.create({"name": "fiction"})
        await book.tags().attach(fiction.id)

        books = await relation_fixtures.Book.query().withRelations("tags").get()
        self.assertTrue(books[0].relationLoaded("tags"))
        self.assertEqual([t.name for t in books[0].getRelation("tags")], ["fiction"])

    async def testRelationNotYetLoadedDefaultsToNone(self) -> None:
        """Report ``None``/``False`` for a relationship never resolved.

        Validates ``getRelation()``/``relationLoaded()`` defaults.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        author = await relation_fixtures.Author.create({"name": "Ana"})
        self.assertFalse(author.relationLoaded("books"))
        self.assertIsNone(author.getRelation("books"))

class TestScopes(feature_fixtures._ModelFeatureTestCase):
    """Local and global query scopes."""

    async def testLocalScopeIsCallableOnTheBuilder(self) -> None:
        """Apply a local scope declared on the model.

        Validates the ``scopeName`` convention.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        models = await feature_fixtures.Account.query().active().get()
        self.assertEqual([model.first_name for model in models], ["Ada"])

    async def testLocalScopeIsCallableOnTheModelClass(self) -> None:
        """Start a query from a local scope.

        Validates the class-level forwarding of scopes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        models = await feature_fixtures.Account.active().get()
        self.assertEqual([model.first_name for model in models], ["Ada"])

    async def testLocalScopeAcceptsArguments(self) -> None:
        """Forward arguments to a parameterized scope.

        Validates argument passing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        models = await feature_fixtures.Account.query().ofRole("guest").get()
        self.assertEqual([model.first_name for model in models], ["Ben"])

    def testUnknownScopeIsReported(self) -> None:
        """Report a scope the model does not declare.

        Validates the explicit lookup failure.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ScopeNotFoundException):
            feature_fixtures.Account.query().scope("ghost")

    def testUnknownAttributeStillRaisesAttributeError(self) -> None:
        """Keep ordinary attribute errors intact on the builder.

        Validates that the scope lookup does not swallow typos.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(AttributeError):
            feature_fixtures.Account.query().ghost  # noqa: B018

    async def testGlobalScopeAppliesToEveryQuery(self) -> None:
        """Constrain every query of the model.

        Validates global scope registration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        feature_fixtures.Account.addGlobalScope(
            "active",
            lambda query: query.where("active", True),
        )
        self.assertEqual(await feature_fixtures.Account.count(), 1)

    async def testGlobalScopeCanBeDisabledPerQuery(self) -> None:
        """Opt a single query out of a global scope.

        Validates ``withoutGlobalScope``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        feature_fixtures.Account.addGlobalScope(
            "active",
            lambda query: query.where("active", True),
        )
        self.assertEqual(
            await feature_fixtures.Account.withoutGlobalScope("active").count(),
            2,
        )
        self.assertEqual(
            await feature_fixtures.Account.withoutGlobalScopes().count(),
            2,
        )

    async def testGlobalScopeCanBeRemoved(self) -> None:
        """Unregister a global scope from the model.

        Validates ``removeGlobalScope``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        feature_fixtures.Account.addGlobalScope(
            "active",
            lambda query: query.where("active", True),
        )
        feature_fixtures.Account.removeGlobalScope("active")
        self.assertEqual(await feature_fixtures.Account.count(), 2)

    async def testToSqlIncludesScopesWithoutFreezingTheOriginalQuery(self) -> None:
        """Inspect model filters without affecting later scope selection.

        Returns
        -------
        None
            Verify SQL parity, detached scopes, and subsequent unscoped reads.
        """
        await self.seed()
        feature_fixtures.Account.addGlobalScope(
            "active", lambda query: query.where("active", True),
        )
        query = feature_fixtures.Account.query()
        original_plan = query.toPlan()
        original_wheres = original_plan.wheres.copy()

        sql = query.toSql(literal_binds=True)

        self.assertIn("accounts.active = 1", sql)
        self.assertIn("accounts.deleted_at IS NULL", sql)
        self.assertEqual(sql, query.toSql(literal_binds=True))
        self.assertIs(query.toPlan(), original_plan)
        self.assertEqual(query.toPlan().wheres, original_wheres)
        self.assertFalse(query._scopes_applied)
        rows = await self._manager.connection().select(sql)
        self.assertEqual([row["first_name"] for row in rows], ["Ada"])

        query.withoutGlobalScope("active").withTrashed()
        unscoped_sql = query.toSql(literal_binds=True)
        self.assertNotIn("accounts.active = 1", unscoped_sql)
        self.assertNotIn("accounts.deleted_at IS NULL", unscoped_sql)
        self.assertEqual(len(await query.get()), 2)

    def testToSqlRespectsSoftDeleteModesAndLocalScopes(self) -> None:
        """Render each soft delete mode and already-applied local scopes.

        Returns
        -------
        None
            Verify filter selection without modifying the original plans.
        """
        cases = (
            (feature_fixtures.Account.query(), "IS NULL"),
            (feature_fixtures.Account.onlyTrashed(), "IS NOT NULL"),
            (feature_fixtures.Account.withTrashed(), None),
        )
        for query, predicate in cases:
            with self.subTest(predicate=predicate):
                original_wheres = query.toPlan().wheres.copy()
                sql = query.toSql()
                if predicate is None:
                    self.assertNotIn("accounts.deleted_at IS", sql)
                else:
                    self.assertIn("accounts.deleted_at " + predicate, sql)
                self.assertEqual(query.toPlan().wheres, original_wheres)
                self.assertFalse(query._scopes_applied)
        self.assertIn(
            "accounts.active = 1",
            feature_fixtures.Account.active().toSql(literal_binds=True),
        )

class TestModelBuilderContract(TestCase):
    def testBuilderImplementsContract(self) -> None:
        """Implement the IModelQueryBuilder contract.

        Validates the builder class hierarchy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(plan_fixtures._Item.query(), IModelQueryBuilder)

class TestModelSharesTheEngine(language_fixtures._QueryLanguageTestCase):
    """The model builder and the model-less builder are one engine."""

    async def testModelSupportsNestedGroups(self) -> None:
        """Group conditions from a model query.

        Validates that grouping is not exclusive to ``DB.table()``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        models = await (
            language_fixtures._User.where("active", True)
            .where(
                lambda query: query.where("role", "admin").orWhere("role", "manager"),
            )
            .get()
        )
        self.assertEqual(sorted(model.name for model in models), ["Ada", "Ben"])

    async def testModelSupportsJoins(self) -> None:
        """Join a related table from a model query.

        Validates that joins reached the model builder too.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        await DB.table("posts").insert(
            [{"user_id": 1, "title": "first", "views": 3}],
        )
        models = await language_fixtures._User.join(
            "posts",
            "posts.user_id",
            "=",
            "users.id",
        ).get()
        self.assertEqual([model.name for model in models], ["Ada"])

    async def testModelSupportsSubqueryConditions(self) -> None:
        """Filter a model query with a correlated subquery.

        Validates the shared ``EXISTS`` machinery.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seedUsers()
        await DB.table("posts").insert(
            [{"user_id": 2, "title": "first", "views": 3}],
        )
        models = await language_fixtures._User.whereExists(
            lambda query: (
                query.table("posts")
                .select("id")
                .whereColumn("posts.user_id", "=", "users.id")
            ),
        ).get()
        self.assertEqual([model.name for model in models], ["Ben"])

    def testBothBuildersProduceTheSameSql(self) -> None:
        """Compile the same query identically from both entry points.

        Validates that models are a thin layer over the shared engine,
        with no duplicated query logic underneath.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        model_plan = (
            language_fixtures._User.query()
            .select("name")
            .where("active", True)
            .where(
                lambda query: query.where("role", "admin").orWhere("role", "manager"),
            )
            .orderBy("name")
            .toPlan()
        )
        raw_plan = (
            RawQueryBuilder()
            .table("users")
            .select("name")
            .where("active", True)
            .where(
                lambda query: query.where("role", "admin").orWhere("role", "manager"),
            )
            .orderBy("name")
            .toPlan()
        )
        self.assertEqual(
            str(SQLCompiler().compileSelect(model_plan)),
            str(SQLCompiler().compileSelect(raw_plan)),
        )

    def testModelBuilderDerivesFromTheSharedEngine(self) -> None:
        """Share the very same base class between both builders.

        Validates the structural guarantee behind the previous test.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(ModelQueryBuilder, QueryBuilderBase))
        self.assertTrue(issubclass(RawQueryBuilder, QueryBuilderBase))

    def testToSqlIsSharedByModelsAndDbTable(self) -> None:
        """Expose matching SQL through both public builder entry points.

        Returns
        -------
        None
            Verify class forwarding, parameter privacy, and repeatable rendering.
        """
        model_query = (
            language_fixtures._User.where("name", "O'Reilly")
            .select("name").orderBy("id").limit(3)
        )
        raw_query = (
            DB.table("users").where("name", "O'Reilly")
            .select("name").orderBy("id").limit(3)
        )
        for literal_binds in (False, True):
            with self.subTest(literal_binds=literal_binds):
                sql = model_query.toSql(literal_binds=literal_binds)
                self.assertIsInstance(sql, str)
                self.assertEqual(sql, raw_query.toSql(literal_binds=literal_binds))
                self.assertEqual(sql, model_query.toSql(literal_binds=literal_binds))
                if literal_binds:
                    self.assertIn("'O''Reilly'", sql)
                else:
                    self.assertNotIn("Reilly", sql)
        self.assertEqual(
            language_fixtures._User.toSql(),
            language_fixtures._User.query().toSql(),
        )
        self.assertEqual(model_query.toPlan().limit_value, 3)

    def testToSqlUsesTheNamedConnectionAndItsPrefix(self) -> None:
        """Use the selected connection rather than the default SQLite dialect.

        Returns
        -------
        None
            Verify named connection routing without creating its database engine.
        """
        self._manager.addConnection(
            "debug", {"driver": "mysql", "database": "debug", "prefix": "app_"},
        )
        queries = (
            DB.table("users", connection="debug").where("name", "marker"),
            language_fixtures._User.query().adoptConnection("debug")
            .where("name", "marker"),
        )
        for query in queries:
            sql = query.toSql()
            self.assertIn("FROM app_users", sql)
            self.assertIn("app_users.name = %s", sql)
            self.assertNotIn("marker", sql)
        self.assertIsNone(self._manager.connection("debug")._engine)

    def testToSqlRejectsAMissingTarget(self) -> None:
        """Reject a builder without a selected table before compiling SQL.

        Returns
        -------
        None
            Verify the same target guard used by ordinary raw retrieval.
        """
        with self.assertRaises(InvalidQueryException):
            RawQueryBuilder().toSql()

    async def testToSqlPreservesQueryLanguageResults(self) -> None:
        """Execute rendered literals and compare them with builder results.

        Returns
        -------
        None
            Verify groups, IN, joins, raw bindings, subqueries, unions, and paging.
        """
        await self.seedUsers()
        await DB.table("posts").insert([
            {"user_id": 1, "title": "first", "views": 3},
            {"user_id": 2, "title": "second", "views": 7},
        ])
        queries = (
            DB.table("users").select("name")
            .where("active", True)
            .where(lambda query: query.where("role", "admin").orWhere(
                "role", "manager",
            ))
            .whereIn("country", ["CO", "MX"]).orderBy("name").limit(2),
            DB.table("users", alias="u").select("u.name", "p.title")
            .join("posts", "p.user_id", "=", "u.id", alias="p")
            .whereRaw("p.views > :floor", {"floor": 3})
            .whereExists(lambda query: query.table("posts").select("id")
                         .whereColumn("posts.user_id", "=", "u.id"))
            .orderBy("u.id"),
            DB.table("posts").select("user_id")
            .selectRaw("count(*)", alias="total").groupBy("user_id")
            .havingRaw("count(*) >= :minimum", {"minimum": 1})
            .orderBy("user_id"),
            DB.table("users").select("name")
            .whereRaw("role = :role", {"role": "admin"})
            .unionAll(DB.table("users").select("name").whereRaw(
                "role = :role", {"role": "manager"},
            ))
            .orderBy("name").limit(2).offset(1),
        )
        for index, query in enumerate(queries):
            with self.subTest(query=index):
                original_plan = query.toPlan()
                sql = query.toSql(literal_binds=True)
                self.assertNotIn("POSTCOMPILE", query.toSql())
                self.assertIs(query.toPlan(), original_plan)
                rendered_rows = await self._manager.connection().select(sql)
                self.assertEqual(rendered_rows, list(await query.get()))

class TestEagerLoadCloning(TestCase):
    """Check terminal guards and execution-context isolation."""

    def testClonedEagerLoadsAreIndependentAndUnique(self) -> None:
        """Preserve load order and isolate later registrations on clones.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        query = fixtures.Author.query().withRelations("books", "books")
        clone = query.clone().withRelations("profile", "books")
        self.assertEqual(list(query._eager_loads), ["books"])
        self.assertEqual(list(clone._eager_loads), ["books", "profile"])

class TestModelTerminalIsolation(fixtures._RelationsTestCase):
    """Exercise repeated terminals and relation writes against SQLite."""

    async def testFirstDoesNotLimitLaterGet(self) -> None:
        """Keep the original result limit when retrieving only one model.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await fixtures.Book.create({"title": "first"})
        await fixtures.Book.create({"title": "second"})
        query = fixtures.Book.query().orderBy("id")
        self.assertEqual((await query.first()).title, "first")
        self.assertIsNone(query.toPlan().limit_value)
        self.assertEqual(len(await query.get()), 2)

    async def testDuplicateEagerLoadsIssueOneRelatedQuery(self) -> None:
        """Load a repeated relationship name once for the entire batch.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await fixtures.Author.create({"name": "author"})
        connection = self._manager.connection()
        compiler = _RecordingCompiler()
        connection._compiler = compiler
        result = await fixtures.Author.withRelations("books", "books").get()
        self.assertEqual(len(result), 1)
        self.assertEqual(compiler.select_count, 2)
