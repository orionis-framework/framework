from __future__ import annotations
import ast
import re
from pathlib import Path
from typing import ClassVar
import tests.orm.query.test_base_builder as plan_fixtures
from orionis.orm import Boolean, DateTime, Integer, Model, String
from orionis.orm.exceptions import OrmConfigurationException
from orionis.orm.metaclass import pluralize, snake_case
from orionis.orm.schema.table import TableDefinition
from orionis.test import TestCase

class _User(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    active = Boolean()

    casts: ClassVar[dict[str, str]] = {"active": "bool"}
    hidden: ClassVar[list[str]] = ["active"]

class _Category(Model):
    id = Integer().primary()

class _Box(Model):
    id = Integer().primary()

class _Account(Model):
    table = "ledger_accounts"
    id = Integer().primary()

class _CustomKey(Model):
    uuid = String().primary()
    incrementing = False

class _BaseAudit(Model):
    __abstract__ = True
    id = Integer().primary().autoIncrement()
    created_by = String().nullable()

    casts: ClassVar[dict[str, str]] = {"id": "int"}

class _Invoice(_BaseAudit):
    total = Integer()

    casts: ClassVar[dict[str, str]] = {"total": "int"}

class TestNamingHelpers(TestCase):
    def testSnakeCaseSplitsCamelWords(self) -> None:
        """Convert CamelCase names into snake_case.

        Validates the class-name normalization helper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(snake_case("UserProfile"), "user_profile")
        self.assertEqual(snake_case("User"), "user")

    def testPluralizeAppliesEnglishHeuristics(self) -> None:
        """Pluralize words with the conventional English rules.

        Validates the y/ies, sibilant/es, and default/s branches.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(pluralize("user"), "users")
        self.assertEqual(pluralize("category"), "categories")
        self.assertEqual(pluralize("box"), "boxes")
        self.assertEqual(pluralize("day"), "days")

class TestModelMetaclass(TestCase):
    def testTableNameDerivedFromClassName(self) -> None:
        """Derive the table name from the pluralized class name.

        Validates the naming convention.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(_User.__meta__.table_name, "users")
        self.assertEqual(_Category.__meta__.table_name, "categories")
        self.assertEqual(_Box.__meta__.table_name, "boxes")

    def testExplicitTableNameIsRespected(self) -> None:
        """Respect an explicitly declared table name.

        Validates the declaration override.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(_Account.__meta__.table_name, "ledger_accounts")

    def testColumnsAreDiscoveredAndDetached(self) -> None:
        """Discover the declared columns and detach them from the class.

        Validates column discovery and namespace cleanup.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        meta = _User.__meta__
        self.assertEqual(set(meta.columns), {"id", "name", "active"})
        self.assertEqual(meta.columns["id"].name, "id")
        # Class access falls through to the metaclass, not the column.
        self.assertNotIn("name", _User.__dict__)

    def testPrimaryKeyFromColumnFlag(self) -> None:
        """Resolve the primary key from the primary column flag.

        Validates primary key discovery.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(_User.__meta__.primary_key, "id")
        self.assertEqual(_CustomKey.__meta__.primary_key, "uuid")
        self.assertFalse(_CustomKey.__meta__.incrementing)

    def testCastsAndHiddenArePrecomputed(self) -> None:
        """Precompute cast handlers and hidden attribute sets.

        Validates the metadata precomputation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        meta = _User.__meta__
        self.assertIn("active", meta.cast_lookup)
        self.assertEqual(meta.hidden, frozenset({"active"}))

    def testAbstractModelsDeferColumnsToChildren(self) -> None:
        """Inherit columns and casts from abstract parents.

        Validates the abstract model support.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(_BaseAudit.__meta__)
        meta = _Invoice.__meta__
        self.assertEqual(
            set(meta.columns),
            {"id", "created_by", "total"},
        )
        self.assertEqual(meta.primary_key, "id")
        self.assertEqual(set(meta.casts), {"id", "total"})

    def testTimestampColumnsOnlyWhenDeclared(self) -> None:
        """Track timestamp columns only when they are declared.

        Validates the timestamp column detection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(_User.__meta__.created_column)
        self.assertIsNone(_User.__meta__.updated_column)

    def testFillableRulesPrecedence(self) -> None:
        """Resolve mass assignment rules with whitelist precedence.

        Validates isFillable across fillable, guarded, and wildcard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        open_meta = _User.__meta__
        self.assertTrue(open_meta.isFillable("name"))

        class _WhiteListed(Model):
            id = Integer().primary()
            name = String()
            fillable: ClassVar[list[str]] = ["name"]

        meta = _WhiteListed.__meta__
        self.assertTrue(meta.isFillable("name"))
        self.assertFalse(meta.isFillable("id"))

        class _BlackListed(Model):
            id = Integer().primary()
            name = String()
            guarded: ClassVar[list[str]] = ["id"]

        meta = _BlackListed.__meta__
        self.assertTrue(meta.isFillable("name"))
        self.assertFalse(meta.isFillable("id"))

        class _Locked(Model):
            id = Integer().primary()
            name = String()
            guarded: ClassVar[list[str]] = ["*"]

        meta = _Locked.__meta__
        self.assertFalse(meta.isFillable("name"))

    def testTimestampsDisabledClearsTimestampColumns(self) -> None:
        """Ignore timestamp columns when timestamps are disabled.

        Validates the timestamps switch.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _Frozen(Model):
            id = Integer().primary()
            created_at = String().nullable()
            updated_at = String().nullable()
            timestamps = False

        meta = _Frozen.__meta__
        self.assertIsNone(meta.created_column)
        self.assertIsNone(meta.updated_column)

    def testCustomTimestampColumnNames(self) -> None:
        """Honor overridden CREATED_AT and UPDATED_AT names.

        Validates the timestamp column overrides.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _Renamed(Model):
            id = Integer().primary()
            createdOn = String().nullable()  # noqa: N815
            CREATED_AT: ClassVar[str] = "createdOn"

        meta = _Renamed.__meta__
        self.assertEqual(meta.created_column, "createdOn")
        self.assertIsNone(meta.updated_column)

    def testApplyCastsSkipsNoneValues(self) -> None:
        """Skip cast application for None values.

        Validates the hydration cast pass.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        meta = _User.__meta__
        row = {"id": 1, "name": "a", "active": None}
        self.assertIsNone(meta.applyCasts(row)["active"])
        row_cast = meta.applyCasts({"id": 1, "active": 1})
        self.assertIs(row_cast["active"], True)

    def testBaseModelHasNoMetadata(self) -> None:
        """Keep the abstract base model without metadata.

        Validates the abstract base detection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsNone(Model.__meta__)

    def testUnknownAttributeRaisesAttributeError(self) -> None:
        """Raise AttributeError for names outside the forwarded builder set.

        Validates the metaclass __getattr__ fallback.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(AttributeError):
            _User.totallyUnknownAttribute  # noqa: B018

    def testForwardedMethodOnAbstractModelRaisesAttributeError(self) -> None:
        """Raise AttributeError for forwarded methods on an abstract model.

        Validates that a builder method name never crashes when the
        owning class has no metadata to build a query from.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(AttributeError):
            Model.where("name", "x")

    def testPrimaryKeyDefaultsToIdWithoutAnyPrimaryFlag(self) -> None:
        """Default the primary key name to "id" without a primary flag.

        Validates the final fallback of primary key resolution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _NoFlaggedPrimary(Model):
            id = Integer()
            name = String()

        self.assertEqual(_NoFlaggedPrimary.__meta__.primary_key, "id")

    def testConcreteParentColumnsAreInherited(self) -> None:
        """Inherit columns from a concrete, non-abstract parent model.

        Validates that __meta__.columns (not just __pending_columns__)
        feeds the discovery of a subclass built from a real model.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _ConcreteParent(Model):
            id = Integer().primary().autoIncrement()
            name = String()

        class _ConcreteChild(_ConcreteParent):
            extra = String().nullable()

        self.assertEqual(
            set(_ConcreteChild.__meta__.columns),
            {"id", "name", "extra"},
        )

class TestModelQueryForwarding(TestCase):
    def testForwardedClassEntryPointsStartBuilders(self) -> None:
        """Start builders from forwarded class-level entry points.

        Validates the metaclass forwarding whitelist.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        builder = plan_fixtures._Item.where("name", "a")
        self.assertEqual(len(builder._plan.wheres), 1)
        chained = plan_fixtures._Item.orderBy("name").limit(1)
        self.assertEqual(chained._plan.limit_value, 1)

    def testUnknownClassAttributeRaises(self) -> None:
        """Raise AttributeError for non-forwarded class attributes.

        Validates the metaclass forwarding guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(AttributeError):
            _ = plan_fixtures._Item.notAQueryMethod

class TestSharedModelSchema(TestCase):
    """Exercise attribute state and serialization without database access."""

    def testSharedSchemaRetainsItsTableAndConstraints(self) -> None:
        """Adopt the same versioned table used by schema migrations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        definition = TableDefinition(
            name="shared_records",
            schema="example",
            columns={"key": Integer().primary(), "name": String()},
            primary_key="key",
            comment="Shared schema version one",
        )

        class _Shared(Model):
            table_definition = definition

        class _Descendant(_Shared):
            pass

        self.assertIs(_Shared.__meta__.table, definition)
        self.assertIs(_Descendant.__meta__.table, definition)
        self.assertEqual(_Shared.__meta__.primary_key, "key")
        self.assertEqual(_Shared({"name": "valid"}).name, "valid")

    def testSharedSchemaRejectsConflictingDeclarations(self) -> None:
        """Reject duplicate columns, table names and primary keys.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        definition = TableDefinition(
            name="records",
            columns={"id": Integer().primary()},
        )
        for overrides in (
            {"id": Integer()},
            {"table": "other"},
            {"primary_key": "other"},
            {"table_definition": "invalid"},
        ):
            with (
                self.subTest(overrides=overrides),
                self.assertRaises(
                    OrmConfigurationException,
                ),
            ):
                type("Invalid", (Model,), {"table_definition": definition, **overrides})

    def testSoftDeleteInheritanceDoesNotModifyParentSchema(self) -> None:
        """Keep a child nullable delete column isolated from its parent.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """

        class _Parent(Model):
            id = Integer().primary()
            deleted_at = DateTime()

        class _SoftChild(_Parent):
            soft_deletes = True

        self.assertFalse(_Parent.__meta__.columns["deleted_at"].is_nullable)
        self.assertTrue(_SoftChild.__meta__.columns["deleted_at"].is_nullable)

    def testSharedSoftDeleteSchemaRequiresNullableColumn(self) -> None:
        """Reject invalid shared schemas without modifying historical definitions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        definition = TableDefinition(
            name="records",
            columns={"id": Integer().primary(), "deleted_at": DateTime()},
        )
        with self.assertRaises(OrmConfigurationException):
            type(
                "Invalid",
                (Model,),
                {
                    "table_definition": definition,
                    "soft_deletes": True,
                },
            )
        self.assertFalse(definition.columns["deleted_at"].is_nullable)

_ROOT = Path(__file__).resolve().parents[2]

_METHOD_NAME = re.compile(r"_{0,2}[a-z][a-zA-Z0-9]*\Z")

_FUNCTION_NAME = re.compile(r"_?[a-z][a-z0-9_]*\Z")

class TestDatabaseNamingConventions(TestCase):
    """Check public and internal Python names across the database and ORM."""

    def testMethodsAndModuleFunctionsFollowConventions(self) -> None:
        """Keep methods camelCase and module functions snake_case.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        failures = []
        for package in ("database", "orm"):
            root = _ROOT / "orionis" / package
            self.assertTrue(root.is_dir())
            for path in (*root.rglob("*.py"), *root.rglob("*.pyi")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.ClassDef, ast.Module)):
                        continue
                    pattern = (
                        _METHOD_NAME
                        if isinstance(node, ast.ClassDef)
                        else (_FUNCTION_NAME)
                    )
                    for member in node.body:
                        if not isinstance(
                            member,
                            (ast.FunctionDef, ast.AsyncFunctionDef),
                        ):
                            continue
                        name = member.name
                        if name.startswith("__") and name.endswith("__"):
                            continue
                        if pattern.fullmatch(name) is None:
                            failures.append(
                                f"{path.relative_to(_ROOT)}:{member.lineno} {name}",
                            )
        self.assertEqual(failures, [])
