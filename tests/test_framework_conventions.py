import ast
from collections.abc import Callable
from pathlib import Path
import re
from typing import TYPE_CHECKING, get_args, get_origin
from unittest import TestSuite
from orionis.database.schema.definitions import SchemaDefinition
from orionis.foundation.contracts.application import IApplication
from orionis.queues.types import DispatchCallback
from orionis.test import TestCase
from orionis.test.core.engine import TestingEngine

if TYPE_CHECKING:
    from collections.abc import Iterator

_ROOT = Path(__file__).resolve().parents[1]
_METHOD = re.compile(r"_{0,2}[a-z][a-zA-Z0-9]*")
_FUNCTION = re.compile(r"_?[a-z][a-z0-9_]*")
_RESULT = re.compile(r"(?m)^(Returns|Yields)\n-+")
_PARAMETER = re.compile(r"(?m)^([*\w]+(?:,\s*[*\w]+)*)\s*:")
type _Function = ast.FunctionDef | ast.AsyncFunctionDef

def runtime_definitions() -> Iterator[tuple[Path, _Function, bool]]:
    """Inspect every runtime module without importing optional backend services.

    Yields
    ------
    tuple[Path, _Function, bool]
        Relative path, definition and whether its direct parent is a class.
    """
    for path in sorted((_ROOT / "orionis").rglob("*.py")):
        tree = ast.parse(path.read_bytes(), filename=str(path))
        for parent in ast.walk(tree):
            for node in ast.iter_child_nodes(parent):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield (
                        path.relative_to(_ROOT), node, isinstance(parent, ast.ClassDef),
                    )

def argument_names(function: _Function) -> set[str]:
    """Return signature argument names excluding implicit method receivers.

    Parameters
    ----------
    function : _Function
        Runtime function or method being checked.

    Returns
    -------
    set[str]
        Names that require parameter documentation.
    """
    arguments = [
        *function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs,
    ]
    if function.args.vararg is not None:
        arguments.append(function.args.vararg)
    if function.args.kwarg is not None:
        arguments.append(function.args.kwarg)
    return {item.arg for item in arguments if item.arg not in {"self", "cls"}}

class TestFrameworkConventions(TestCase):
    """Guard runtime conventions and native test-case inheritance."""

    def testTestsDirectoryContainsOnlyTestModules(self) -> None:
        """Keep auxiliary files outside the test source tree.

        Returns
        -------
        None
            Verify every source file is a test module, excluding generated caches.
        """
        unexpected = []
        for path in sorted((_ROOT / "tests").rglob("*")):
            if {"__pycache__", ".ruff_cache"}.intersection(path.parts):
                continue
            if path.is_file() and not path.match("test_*.py"):
                unexpected.append(path.relative_to(_ROOT).as_posix())
        self.assertEqual(unexpected, [])

    def testEveryDiscoveredTestUsesFrameworkBase(self, app: IApplication) -> None:
        """Require every discovered test to inherit the Orionis test case.

        Parameters
        ----------
        app : IApplication
            Booted application supplying the native discovery configuration.

        Returns
        -------
        None
            Verify discovery finds tests and none bypass the framework base.
        """
        self.assertIsInstance(app, IApplication)
        engine = TestingEngine(app)
        suite = (
            engine.setStartDir(str(_ROOT / "tests"))
            .setFilePattern("test_*.py")
            .setMethodPattern("test*")
            .discover()
        )
        pending: list[object] = [suite]
        invalid = []
        test_count = 0
        while pending:
            case = pending.pop()
            if isinstance(case, TestSuite):
                pending.extend(case)
            else:
                test_count += 1
                if not isinstance(case, TestCase):
                    invalid.append(str(case))
        self.assertGreater(test_count, 0)
        self.assertEqual(invalid, [])

    def testPublicStandaloneTypeAliasesEvaluateAtRuntime(self) -> None:
        """Resolve public aliases without relying on TYPE_CHECKING-only imports.

        Returns
        -------
        None
            Schema definitions and queue callbacks expose usable runtime types.
        """
        self.assertEqual(
            {member.__name__ for member in get_args(SchemaDefinition.__value__)},
            {
                "ColumnDefinition", "Comment", "ForeignKey", "Index",
                "PrimaryKey", "Unique",
            },
        )
        self.assertIs(get_origin(DispatchCallback.__value__), Callable)

    def testEveryRuntimeSignatureHasExplicitAnnotations(self) -> None:
        """Require annotated arguments and return values on runtime definitions.

        Returns
        -------
        None
            Implicit self and cls receivers are the only unannotated parameters.
        """
        invalid = []
        for path, function, _method in runtime_definitions():
            arguments = [
                *function.args.posonlyargs, *function.args.args,
                *function.args.kwonlyargs,
            ]
            arguments.extend(item for item in (
                function.args.vararg, function.args.kwarg,
            ) if item is not None)
            if function.returns is None or any(
                item.annotation is None and item.arg not in {"self", "cls"}
                for item in arguments
            ):
                invalid.append(f"{path}:{function.lineno}:{function.name}")
        self.assertEqual(invalid, [])

    def testEveryRuntimeDefinitionFollowsItsNamingConvention(self) -> None:
        """Require camelCase methods and snake_case standalone functions.

        Returns
        -------
        None
            Python hooks and property accessors retain their protocol names.
        """
        invalid = []
        for path, function, method in runtime_definitions():
            name = function.name
            if name.startswith("__") and name.endswith("__"):
                continue
            decorators = tuple(ast.unparse(item) for item in function.decorator_list)
            property_accessor = any(
                item == "property" or item.endswith((".setter", ".deleter"))
                for item in decorators
            )
            pattern = _METHOD if method else _FUNCTION
            if pattern.fullmatch(name) is None and not (
                property_accessor and _FUNCTION.fullmatch(name)
            ):
                invalid.append(f"{path}:{function.lineno}:{name}")
        self.assertEqual(invalid, [])

    def testEveryRuntimeDefinitionHasNumpyParameterAndResultSections(self) -> None:
        """Require NumPy documentation while excluding typing-only overloads.

        Returns
        -------
        None
            Runtime definitions document all explicit parameters and results.
        """
        invalid = []
        for path, function, _method in runtime_definitions():
            if any(
                ast.unparse(item).endswith("overload")
                for item in function.decorator_list
            ):
                continue
            doc = ast.get_docstring(function) or ""
            documented = {
                name.strip().lstrip("*")
                for match in _PARAMETER.finditer(doc)
                for name in match[1].split(",")
            }
            missing = argument_names(function) - documented
            if not _RESULT.search(doc) or missing:
                invalid.append(f"{path}:{function.lineno}:{function.name}:{sorted(missing)}")
        self.assertEqual(invalid, [])
