import ast
import re
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator

type _Function = ast.FunctionDef | ast.AsyncFunctionDef

_ROOT = Path(__file__).resolve().parents[2]
_METHOD_NAME = re.compile(r"_{0,2}[a-z][a-zA-Z0-9]*")
_FUNCTION_NAME = re.compile(r"_?[a-z][a-z0-9_]*")
_TEST_NAME = re.compile(r"test[A-Z][a-zA-Z0-9]*")

@cache
def source_trees() -> tuple[tuple[Path, ast.Module], ...]:
    """
    Read the HTTP source and test syntax trees for convention checks.

    Returns
    -------
    tuple[tuple[Path, ast.Module], ...]
        Repository-relative paths and their parsed module syntax trees.
    """
    return tuple(
        (path.relative_to(_ROOT), ast.parse(path.read_text(encoding="utf-8")))
        for directory in (_ROOT / "orionis" / "http", _ROOT / "tests" / "http")
        for path in sorted(directory.rglob("*.py"))
    )

def function_definitions() -> Iterator[tuple[Path, _Function, bool]]:
    """
    Enumerate functions and distinguish class methods from standalone helpers.

    Yields
    ------
    tuple[Path, _Function, bool]
        Definition path, syntax node, and whether its parent is a class.
    """
    for path, tree in source_trees():
        parents = {
            child: node for node in ast.walk(tree)
            for child in ast.iter_child_nodes(node)
        }
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield path, node, isinstance(parents[node], ast.ClassDef)

def function_arguments(function: _Function) -> Iterator[ast.arg]:
    """
    Enumerate positional, keyword-only, and variadic function arguments.

    Parameters
    ----------
    function : _Function
        Definition whose argument annotations are inspected.

    Yields
    ------
    ast.arg
        One declared argument, including variadic arguments when present.
    """
    yield from function.args.posonlyargs
    yield from function.args.args
    yield from function.args.kwonlyargs
    if function.args.vararg is not None:
        yield function.args.vararg
    if function.args.kwarg is not None:
        yield function.args.kwarg

class TestHTTPConventions(TestCase):
    """Enforce HTTP naming, documentation, annotations, and test dependencies."""

    def testFunctionAndMethodNamesFollowTheirConventions(self) -> None:
        """
        Require camelCase methods and snake_case standalone functions.

        Validates custom names while retaining the protocol hooks that Python
        invokes through its language-defined dunder names.
        """
        invalid = []
        for path, function, is_method in function_definitions():
            name = function.name
            if is_method and name.startswith("__") and name.endswith("__"):
                continue
            pattern = _METHOD_NAME if is_method else _FUNCTION_NAME
            if is_method and name.startswith("test"):
                pattern = _TEST_NAME
            if pattern.fullmatch(name) is None:
                invalid.append(f"{path}:{function.lineno}:{name}")
        self.assertEqual(invalid, [])

    def testEveryTestHelperHasAnnotatedArgumentsAndReturnType(self) -> None:
        """
        Require explicit annotations on test methods and their helper functions.

        Validates signatures independently of repository-wide lint exemptions.
        """
        invalid = []
        for path, function, _is_method in function_definitions():
            if path.parts[0] != "tests":
                continue
            missing = [
                argument.arg for argument in function_arguments(function)
                if argument.arg not in {"self", "cls"}
                and argument.annotation is None
            ]
            if function.returns is None or missing:
                invalid.append(f"{path}:{function.lineno}:{function.name}")
        self.assertEqual(invalid, [])

    def testEveryTestHelperHasADocstringWithoutExamplesSection(self) -> None:
        """
        Require documentation for every test function and helper.

        Validates that documentation does not introduce an Examples section.
        """
        invalid = []
        for path, function, _is_method in function_definitions():
            if path.parts[0] != "tests":
                continue
            docstring = ast.get_docstring(function)
            if not docstring or re.search(r"(?m)^Examples\n-+", docstring):
                invalid.append(f"{path}:{function.lineno}:{function.name}")
        self.assertEqual(invalid, [])

    def testTestsDoNotImportUnittestDirectly(self) -> None:
        """
        Keep all test imports independent of the unittest package.

        Validates the framework TestCase contract and explicit test doubles.
        """
        invalid = []
        for path, tree in source_trees():
            if path.parts[0] != "tests":
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    modules = [node.module or ""]
                else:
                    continue
                if any(module.split(".")[0] == "unittest" for module in modules):
                    invalid.append(f"{path}:{node.lineno}")
        self.assertEqual(invalid, [])

    def testAsyncTestsExerciseAnAsyncOperation(self) -> None:
        """
        Require asynchronous test methods to await asynchronous behavior.

        Validates that synchronous functionality uses ordinary test methods.
        """
        invalid = []
        for path, function, is_method in function_definitions():
            if (
                path.parts[0] == "tests" and is_method
                and function.name.startswith("test")
                and isinstance(function, ast.AsyncFunctionDef)
                and not any(
                    isinstance(node, (ast.Await, ast.AsyncFor, ast.AsyncWith))
                    or (isinstance(node, ast.comprehension) and node.is_async)
                    for node in ast.walk(function)
                )
            ):
                invalid.append(f"{path}:{function.lineno}:{function.name}")
        self.assertEqual(invalid, [])
