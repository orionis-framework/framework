from __future__ import annotations
import ast
import re
from pathlib import Path
from unittest import TestCase

_ROOT = Path(__file__).resolve().parents[2]
_METHOD_NAME = re.compile(r"_{0,2}[a-z][a-zA-Z0-9]*\Z")
_FUNCTION_NAME = re.compile(r"_?[a-z][a-z0-9_]*\Z")


class TestDatabaseNamingConventions(TestCase):
    """Check public and internal Python names across the database and ORM."""

    def testMethodsAndModuleFunctionsFollowConventions(self) -> None:
        """Keep methods camelCase and module functions snake_case."""
        failures = []
        for package in ("database", "orm"):
            root = _ROOT / "orionis" / package
            self.assertTrue(root.is_dir())
            for path in (*root.rglob("*.py"), *root.rglob("*.pyi")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.ClassDef, ast.Module)):
                        continue
                    pattern = _METHOD_NAME if isinstance(node, ast.ClassDef) else (
                        _FUNCTION_NAME
                    )
                    for member in node.body:
                        if not isinstance(
                            member, (ast.FunctionDef, ast.AsyncFunctionDef),
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
