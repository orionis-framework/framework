import ast
import re
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

_METHOD_NAME = re.compile(r"_{0,2}[a-z][a-zA-Z0-9]*")
_FUNCTION_NAME = re.compile(r"_{0,2}[a-z][a-z0-9_]*")

def _naming_violations(
    node: ast.AST, *, in_class: bool = False,
) -> Iterator[str]:
    """Find definitions that violate the naming rule for their lexical scope.

    Parameters
    ----------
    node : ast.AST
        Syntax node whose definitions and descendants are inspected.
    in_class : bool, optional
        Whether the current lexical scope belongs to a class.

    Yields
    ------
    str
        Line number, definition name and expected naming convention.
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # Python and dataclass hooks must retain their special protocol names.
        special_method = node.name.startswith("__") and node.name.endswith("__")
        pattern = _METHOD_NAME if in_class else _FUNCTION_NAME
        if not (in_class and special_method) and not pattern.fullmatch(node.name):
            convention = "camelCase" if in_class else "snake_case"
            yield f"{node.lineno}: {node.name} must use {convention}"
        in_class = False
    elif isinstance(node, ast.ClassDef):
        in_class = True

    for child in ast.iter_child_nodes(node):
        yield from _naming_violations(child, in_class=in_class)


class TestNamingConventions(unittest.TestCase):
    """Keep framework and test definitions consistent with their scope."""

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
            for path in sorted(folder.rglob("*.py*")):
                if path.suffix not in {".py", ".pyi"}:
                    continue
                relative = path.relative_to(root)
                # Database run artifacts contain historical and invalid fixtures.
                if relative.parts[:3] == ("tests", "real_database", "artifacts"):
                    continue
                tree = ast.parse(
                    path.read_text(encoding="utf-8-sig"), filename=str(path),
                )
                violations.extend(
                    f"{relative.as_posix()}:{violation}"
                    for violation in _naming_violations(tree)
                )

        self.assertEqual(violations, [], "\n".join(violations))
