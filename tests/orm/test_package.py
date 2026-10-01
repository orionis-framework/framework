import ast
from importlib import import_module
from pathlib import Path
from types import ModuleType
import orionis.orm as orm_module
from orionis.test import TestCase

def assert_package_exports(
    test_case: TestCase,
    module_name: str,
    expected_exports: dict[str, tuple[str, str]],
) -> None:
    """Verify public exports against their independently recorded definitions.

    Parameters
    ----------
    test_case : TestCase
        Test case owning the assertions.
    module_name : str
        Framework package whose public exports are inspected.
    expected_exports : dict of str to tuple of str and str
        Public names mapped to their defining module and symbol names.

    Returns
    -------
    None
        Verify exact names, uniqueness, origin identity, and export caching.
    """
    module = import_module(module_name)
    names = module.__all__
    test_case.assertEqual(set(names), set(expected_exports))
    test_case.assertEqual(len(names), len(set(names)))
    for name, (defining_module, symbol) in expected_exports.items():
        exported = getattr(module, name)
        test_case.assertIs(
            exported, getattr(import_module(defining_module), symbol), name,
        )
        test_case.assertNotIsInstance(exported, ModuleType, name)
        test_case.assertIs(getattr(module, name), exported, name)

class TestOrmPackageLookup(TestCase):
    """Verify the lazy ORM export lookup and interactive package surface."""

    def testUnknownExportRaisesAttributeError(self) -> None:
        """Reject undeclared names without fabricating exports.

        Returns
        -------
        None
            Verify ordinary lookup errors remain visible to callers.
        """
        missing_name = "missingOrmExport"
        with self.assertRaises(AttributeError):
            getattr(orm_module, missing_name)

    def testDirectoryListsEveryPublicExportInSortedOrder(self) -> None:
        """Expose declared lazy names in the package directory.

        Returns
        -------
        None
            Verify sorted and unique public interactive discovery.
        """
        names = orm_module.__dir__()
        self.assertEqual(names, sorted(set(names)))
        self.assertTrue(set(orm_module.__all__).issubset(names))

EXPECTED_EXPORTS = {
    "BelongsToManyRelation": ("orionis.orm.relations", "BelongsToManyRelation"),
    "BelongsToRelation": ("orionis.orm.relations", "BelongsToRelation"),
    "BigInteger": ("orionis.orm.schema.types", "BigInteger"),
    "Boolean": ("orionis.orm.schema.types", "Boolean"),
    "Collection": ("orionis.orm.collections.collection", "Collection"),
    "ColumnType": ("orionis.orm.schema.types", "ColumnType"),
    "ConnectionResolver": ("orionis.orm.resolver", "ConnectionResolver"),
    "Date": ("orionis.orm.schema.types", "Date"),
    "DateTime": ("orionis.orm.schema.types", "DateTime"),
    "Double": ("orionis.orm.schema.types", "Double"),
    "Enum": ("orionis.orm.schema.types", "Enum"),
    "Float": ("orionis.orm.schema.types", "Float"),
    "HasManyRelation": ("orionis.orm.relations", "HasManyRelation"),
    "HasOneRelation": ("orionis.orm.relations", "HasOneRelation"),
    "Integer": ("orionis.orm.schema.types", "Integer"),
    "Interval": ("orionis.orm.schema.types", "Interval"),
    "InvalidQueryException": ("orionis.orm.exceptions", "InvalidQueryException"),
    "LargeBinary": ("orionis.orm.schema.types", "LargeBinary"),
    "MassAssignmentException": ("orionis.orm.exceptions", "MassAssignmentException"),
    "MatchType": ("orionis.orm.schema.types", "MatchType"),
    "Model": ("orionis.orm.model", "Model"),
    "ModelCollection": ("orionis.orm.collections.collection", "ModelCollection"),
    "ModelNotFoundException": ("orionis.orm.exceptions", "ModelNotFoundException"),
    "ModelQueryBuilder": ("orionis.orm.query.builder", "ModelQueryBuilder"),
    "Numeric": ("orionis.orm.schema.types", "Numeric"),
    "NumericCommon": ("orionis.orm.schema.types", "NumericCommon"),
    "OrmConfigurationException": (
        "orionis.orm.exceptions",
        "OrmConfigurationException",
    ),
    "OrmException": ("orionis.orm.exceptions", "OrmException"),
    "Paginator": ("orionis.orm.collections.paginator", "Paginator"),
    "PickleType": ("orionis.orm.schema.types", "PickleType"),
    "Relation": ("orionis.orm.relations", "Relation"),
    "RelationNotFoundException": (
        "orionis.orm.exceptions",
        "RelationNotFoundException",
    ),
    "SchemaType": ("orionis.orm.schema.types", "SchemaType"),
    "SmallInteger": ("orionis.orm.schema.types", "SmallInteger"),
    "StrictArray": ("orionis.orm.schema.types", "StrictArray"),
    "StrictBigInt": ("orionis.orm.schema.types", "StrictBigInt"),
    "StrictBinary": ("orionis.orm.schema.types", "StrictBinary"),
    "StrictBlob": ("orionis.orm.schema.types", "StrictBlob"),
    "StrictChar": ("orionis.orm.schema.types", "StrictChar"),
    "StrictClob": ("orionis.orm.schema.types", "StrictClob"),
    "StrictDecimal": ("orionis.orm.schema.types", "StrictDecimal"),
    "StrictDoublePrecision": ("orionis.orm.schema.types", "StrictDoublePrecision"),
    "StrictInt": ("orionis.orm.schema.types", "StrictInt"),
    "StrictJson": ("orionis.orm.schema.types", "StrictJson"),
    "StrictNChar": ("orionis.orm.schema.types", "StrictNChar"),
    "StrictNVarChar": ("orionis.orm.schema.types", "StrictNVarChar"),
    "StrictReal": ("orionis.orm.schema.types", "StrictReal"),
    "StrictSmallInt": ("orionis.orm.schema.types", "StrictSmallInt"),
    "StrictTimestamp": ("orionis.orm.schema.types", "StrictTimestamp"),
    "StrictVarBinary": ("orionis.orm.schema.types", "StrictVarBinary"),
    "StrictVarChar": ("orionis.orm.schema.types", "StrictVarChar"),
    "String": ("orionis.orm.schema.types", "String"),
    "Text": ("orionis.orm.schema.types", "Text"),
    "Time": ("orionis.orm.schema.types", "Time"),
    "Unicode": ("orionis.orm.schema.types", "Unicode"),
    "UnicodeText": ("orionis.orm.schema.types", "UnicodeText"),
    "Uuid": ("orionis.orm.schema.types", "Uuid"),
}

class TestOrmPackage(TestCase):
    """Verify the orionis.orm public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm", EXPECTED_EXPORTS)

class TestOrmTestLayout(TestCase):
    """Keep the ORM suite aligned with source modules and repository conventions."""

    def testEverySourceModuleHasAMirrorTestFile(self) -> None:
        """Require a matching test file for every ORM implementation module.

        Returns
        -------
        None
            Verify the source and test directory trees remain mirrored.
        """
        tests_root = Path(__file__).resolve().parent
        source_root = tests_root.parents[1] / "orionis/orm"
        for source in source_root.rglob("*.py"):
            relative = source.relative_to(source_root)
            if "docs" in relative.parts:
                continue
            filename = (
                "test_package.py"
                if source.name == "__init__.py"
                else f"test_{source.name}"
            )
            target = tests_root / relative.parent / filename
            self.assertTrue(target.is_file(), relative.as_posix())

    def testEveryTestMethodIsDeclaredDirectlyOnAClass(self) -> None:
        """Reject test functions hidden inside another method or function.

        Returns
        -------
        None
            Verify every declared test is discoverable as a class member.
        """
        for path in Path(__file__).resolve().parent.rglob("test_*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            parents = {
                child: node
                for node in ast.walk(tree)
                for child in ast.iter_child_nodes(node)
            }
            for node in ast.walk(tree):
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef),
                ) and node.name.startswith("test"):
                    self.assertIsInstance(
                        parents[node], ast.ClassDef, f"{path.name}: {node.name}",
                    )

    def testMethodsAndFunctionsFollowNamingAndNumpyConventions(self) -> None:
        """Require class camelCase, module snake_case, and NumPy result sections.

        Returns
        -------
        None
            Verify production and test function declarations satisfy conventions.
        """
        tests_root = Path(__file__).resolve().parent
        source_root = tests_root.parents[1] / "orionis/orm"
        for root in (source_root, tests_root):
            for path in root.rglob("*.py"):
                if "docs" in path.relative_to(root).parts:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                parents = {
                    child: node
                    for node in ast.walk(tree)
                    for child in ast.iter_child_nodes(node)
                }
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    label = f"{path.name}: {node.name}"
                    if not (node.name.startswith("__") and node.name.endswith("__")):
                        pattern = (
                            r"^_{0,2}[a-z][a-zA-Z0-9]*$"
                            if isinstance(parents[node], ast.ClassDef)
                            else r"^_{0,2}[a-z][a-z0-9_]*$"
                        )
                        self.assertRegex(node.name, pattern, label)
                    documentation = ast.get_docstring(node) or ""
                    self.assertTrue(
                        "Returns\n-------" in documentation
                        or "Yields\n------" in documentation,
                        label,
                    )
