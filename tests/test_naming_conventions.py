# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import ast
import os
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from typing import NoReturn, TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from collections.abc import Iterator

_METHOD_NAME = re.compile(r"_{0,2}[a-z][a-zA-Z0-9]*")
_FUNCTION_NAME = re.compile(r"_{0,2}[a-z][a-z0-9_]*")


def _raise_scan_error(error: OSError) -> NoReturn:
    """Propagate a filesystem error from the source walker.

    Parameters
    ----------
    error : OSError
        Original error reported while scanning an allowed directory.

    Raises
    ------
    OSError
        Always propagate the original scan error.
    """
    raise error


def _naming_violations(
    node: ast.AST,
    *,
    in_class: bool = False,
    external_bases: dict[str, type] | None = None,
    protocol_methods: frozenset[str] = frozenset(),
) -> Iterator[str]:
    """Find definitions that violate the naming rule for their lexical scope.

    Parameters
    ----------
    node : ast.AST
        Syntax node whose definitions and descendants are inspected.
    in_class : bool, optional
        Whether the current lexical scope belongs to a class.
    external_bases : dict[str, type] or None, optional
        External bases resolved from explicit imports in this module.
    protocol_methods : frozenset[str], optional
        Methods inherited from a resolved external base in the current class.

    Yields
    ------
    str
        Line number, definition name and expected naming convention.
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # Python and dataclass hooks must retain their special protocol names.
        special_method = node.name.startswith("__") and node.name.endswith("__")
        pattern = _METHOD_NAME if in_class else _FUNCTION_NAME
        protocol_method = in_class and node.name in protocol_methods
        if (
            not (in_class and special_method)
            and not protocol_method
            and not pattern.fullmatch(node.name)
        ):
            convention = "camelCase" if in_class else "snake_case"
            yield f"{node.lineno}: {node.name} must use {convention}"
        in_class = False
        protocol_methods = frozenset()
    elif isinstance(node, ast.ClassDef):
        in_class = True
        protocol_methods = frozenset(
            name
            for base in node.bases
            if isinstance(base, ast.Name) and base.id in (external_bases or {})
            for name in dir(external_bases[base.id])
            if callable(getattr(external_bases[base.id], name, None))
        )
    elif isinstance(node, ast.Module):
        external_bases = {
            alias.asname or alias.name: HTMLParser
            for statement in node.body
            if isinstance(statement, ast.ImportFrom)
            and statement.module == "html.parser"
            for alias in statement.names
            if alias.name == "HTMLParser"
        }

    for child in ast.iter_child_nodes(node):
        yield from _naming_violations(
            child,
            in_class=in_class,
            external_bases=external_bases,
            protocol_methods=protocol_methods,
        )


class TestNamingConventions(unittest.TestCase):
    """Keep framework and test definitions consistent with their scope."""

    def testExternalHooksKeepTheirProtocolNames(self) -> None:
        """Permit inherited HTMLParser hooks without exempting custom snake names."""
        source = ast.parse(
            "from html.parser import HTMLParser as Parser\n"
            "class Reader(Parser):\n"
            "    def handle_data(self, data): pass\n"
            "    def custom_method(self): pass\n"
            "class Unrelated:\n"
            "    def handle_data(self, data): pass\n",
        )
        violations = list(_naming_violations(source))
        self.assertEqual(len(violations), 2)
        self.assertIn("custom_method", violations[0])
        self.assertIn("handle_data", violations[1])

    def testUnreadableSourceDirectoryFailsValidation(self) -> None:
        """Propagate scan failures instead of omitting allowed source files.

        Returns
        -------
        None
            No return value.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blocked = root / "orionis" / "unreadable"
            blocked.mkdir(parents=True)
            (root / "tests").mkdir()
            scan = os.scandir
            failure = PermissionError("The source directory cannot be read.")

            def scan_allowed(
                path: str | os.PathLike[str],
            ) -> Iterator[os.DirEntry[str]]:
                """Raise the original error for one allowed source directory.

                Parameters
                ----------
                path : str | os.PathLike[str]
                    Directory requested by the source walker.

                Returns
                -------
                Iterator[os.DirEntry[str]]
                    Directory entries when access succeeds.

                Raises
                ------
                PermissionError
                    If the requested directory is blocked by the fixture.
                """
                if Path(path) == blocked:
                    raise failure
                return scan(path)

            with (
                patch.object(
                    sys.modules[__name__],
                    "__file__",
                    str(root / "tests" / "naming.py"),
                ),
                patch.object(os, "scandir", scan_allowed),
                self.assertRaises(PermissionError) as raised,
            ):
                self.testDefinitionsFollowTheirScopeConvention()
            self.assertIs(raised.exception, failure)

    def testExcludedDatabaseTreeIsNeverScanned(self) -> None:
        """Prune the local database tree before scanning or parsing its contents."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            excluded = root / "tests" / "real_database"
            excluded.mkdir(parents=True)
            # Invalid source makes accidental parsing fail independently of traversal.
            (excluded / "test_private.py").write_text(
                "invalid python !",
                encoding="utf-8",
            )
            source = root / "orionis" / "allowed.py"
            source.parent.mkdir()
            source.write_text("value = 1\n", encoding="utf-8")
            scandir = os.scandir

            def scan_allowed(
                path: str | os.PathLike[str],
            ) -> Iterator[os.DirEntry[str]]:
                """Reject scans beneath the excluded temporary directory.

                Parameters
                ----------
                path : str | os.PathLike[str]
                    Directory requested by the source walker.

                Returns
                -------
                Iterator[os.DirEntry[str]]
                    Original directory entries for an allowed directory.
                """
                self.assertFalse(Path(path).is_relative_to(excluded))
                return scandir(path)

            with (
                patch.object(
                    sys.modules[__name__],
                    "__file__",
                    str(root / "tests" / "naming.py"),
                ),
                patch.object(os, "scandir", scan_allowed),
            ):
                self.testDefinitionsFollowTheirScopeConvention()

    def testSimilarlyNamedPublicDirectoriesRemainChecked(self) -> None:
        """Keep unrelated directories in scope despite a matching path segment."""
        for relative in (
            "orionis/real_database/allowed.py",
            "tests/real_database_unit/allowed.py",
            "tests/public/real_database/allowed.py",
        ):
            with (
                self.subTest(path=relative),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                (root / "orionis").mkdir()
                (root / "tests").mkdir()
                source = root / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                # Deliberately violate naming to prove this public fixture is checked.
                source.write_text(
                    "class Example:\n    def invalid_name(self): pass\n",
                    encoding="utf-8",
                )
                with (
                    patch.object(
                        sys.modules[__name__],
                        "__file__",
                        str(root / "tests" / "naming.py"),
                    ),
                    self.assertRaisesRegex(AssertionError, re.escape(relative)),
                ):
                    self.testDefinitionsFollowTheirScopeConvention()

    def testDefinitionsFollowTheirScopeConvention(self) -> None:
        """Check source and typing files, including nested and async definitions.

        Returns
        -------
        None
            Report all incorrectly named definitions in one assertion.
        """
        root = Path(__file__).resolve().parents[1]
        violations = []
        for folder in (root / "orionis", root / "tests"):
            for directory, subdirectories, filenames in folder.walk(
                on_error=_raise_scan_error,
            ):
                # Prune the complete local database tree before visiting it.
                if directory == root / "tests" and "real_database" in subdirectories:
                    subdirectories.remove("real_database")
                subdirectories.sort()
                for filename in sorted(filenames):
                    path = directory / filename
                    if path.suffix not in {".py", ".pyi"}:
                        continue
                    relative = path.relative_to(root)
                    tree = ast.parse(
                        path.read_text(encoding="utf-8-sig"),
                        filename=str(path),
                    )
                    violations.extend(
                        f"{relative.as_posix()}:{violation}"
                        for violation in _naming_violations(tree)
                    )

        self.assertEqual(violations, [], "\n".join(violations))
