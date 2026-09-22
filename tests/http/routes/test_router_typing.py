import ast
from pathlib import Path
from orionis.test import TestCase

def public_signatures(path: Path, class_name: str) -> dict:
    """Read public method signatures without importing stub-only definitions."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    definition = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    result = {}
    for method in definition.body:
        if not isinstance(method, ast.FunctionDef) or method.name.startswith("_"):
            continue
        arguments = method.args
        arguments.args = arguments.args[1:]
        result[method.name] = (
            ast.dump(arguments, include_attributes=False),
            ast.dump(method.returns, include_attributes=False),
        )
    return result

class TestRouterTyping(TestCase):
    """Check shared API structure in addition to behavioral integration tests."""

    def testFacadeStubMatchesRuntimeSignatures(self) -> None:
        """Keep argument kinds, defaults, annotations and group return aligned."""
        root = Path(__file__).resolve().parents[3]
        runtime = public_signatures(root / "orionis/http/routes/router.py", "Router")
        stub = public_signatures(root / "orionis/support/facades/router.pyi", "Route")
        for name, signature in runtime.items():
            with self.subTest(method=name):
                self.assertEqual(stub[name], signature)

    def testContractMatchesRuntimeSignatures(self) -> None:
        """Keep the router contract consistent with both runtime and facade."""
        root = Path(__file__).resolve().parents[3]
        runtime = public_signatures(root / "orionis/http/routes/router.py", "Router")
        contract = public_signatures(
            root / "orionis/http/routes/contracts/router.py", "IRouter",
        )
        self.assertEqual(contract, runtime)
