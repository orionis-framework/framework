import ast
import re
from inspect import Parameter, iscoroutinefunction, signature
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING
from orionis.foundation.application import Application
from orionis.foundation.contracts.application import IApplication
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterator

def foundation_definitions() -> Iterator[
    tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef, bool]
]:
    """Collect explicit function definitions across the foundation package.

    Yields
    ------
    tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef, bool]
        Source path, definition and whether it belongs directly to a class.
    """
    root = Path(__file__).resolve().parents[3] / "orionis" / "foundation"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for parent in ast.walk(tree):
            for node in ast.iter_child_nodes(parent):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield path, node, isinstance(parent, ast.ClassDef)

class TestApplicationContract(TestCase):
    """Verify that the interface describes Application's public API."""

    def testPublicApplicationApiMatchesTheContract(self) -> None:
        """
        Keep every public implementation member in the application contract.

        Returns
        -------
        None
            Assert that both classes expose the same public members.
        """
        implementation_members = {
            name: member
            for name, member in vars(Application).items()
            if not name.startswith("_")
            and (callable(member) or isinstance(member, property))
        }
        contract_members = {
            name: member
            for name, member in vars(IApplication).items()
            if not name.startswith("_")
            and (callable(member) or isinstance(member, property))
        }
        self.assertEqual(set(contract_members), set(implementation_members))
        self.assertTrue(IApplication.__abstractmethods__)
        self.assertFalse(Application.__abstractmethods__)

    def testContractDoesNotIntroduceAnInstanceDictionary(self) -> None:
        """Declare the application contract as a stateless slotted interface.

        Returns
        -------
        None
            The contract itself adds no instance dictionary to implementations.
        """
        self.assertEqual(vars(IApplication)["__slots__"], ())

    def testFoundationNamesFollowProjectConventions(self) -> None:
        """Require camelCase methods and snake_case standalone functions.

        Returns
        -------
        None
            All explicit definitions follow naming or protocol conventions.
        """
        violations = []
        for path, node, is_method in foundation_definitions():
            name = node.name
            if name.startswith("__") and name.endswith("__"):
                continue
            pattern = r"_{0,2}[a-z][a-zA-Z0-9]*" if is_method else r"_?[a-z][a-z0-9_]*"
            if re.fullmatch(pattern, name) is None:
                violations.append(f"{path.name}:{node.lineno}:{name}")
        self.assertEqual(violations, [])

    def testFoundationDefinitionsHaveNumpyDocsAndAnnotations(self) -> None:
        """Require NumPy result sections and annotated function signatures.

        Returns
        -------
        None
            Every explicit definition is documented and annotated.
        """
        violations = []
        for path, node, _ in foundation_definitions():
            doc = ast.get_docstring(node) or ""
            parameters = [
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            ]
            if node.args.vararg is not None:
                parameters.append(node.args.vararg)
            if node.args.kwarg is not None:
                parameters.append(node.args.kwarg)
            missing_annotations = any(
                parameter.annotation is None
                for parameter in parameters
                if parameter.arg not in {"self", "cls"}
            )
            missing_result = not (
                "Returns\n-------" in doc or "Yields\n------" in doc
            )
            if (
                missing_result
                or missing_annotations
                or node.returns is None
                or "Examples\n--------" in doc
            ):
                violations.append(f"{path.name}:{node.lineno}:{node.name}")
        self.assertEqual(violations, [])

    def testMethodSignaturesMatchImplementation(self) -> None:
        """
        Match parameter order, kinds, annotations, defaults and async behavior.

        Returns
        -------
        None
            Assert that every public method has the same call signature.
        """
        for name, contract_member in vars(IApplication).items():
            implementation_member = vars(Application).get(name)
            if not name.startswith("_") and callable(contract_member):
                with self.subTest(method=name):
                    contract_signature = signature(contract_member)
                    implementation_signature = signature(implementation_member)
                    contract_parameters = tuple(
                        contract_signature.parameters.values(),
                    )
                    implementation_parameters = tuple(
                        implementation_signature.parameters.values(),
                    )
                    self.assertEqual(
                        len(contract_parameters),
                        len(implementation_parameters),
                    )
                    for contract_parameter, implementation_parameter in zip(
                        contract_parameters,
                        implementation_parameters,
                        strict=True,
                    ):
                        self.assertEqual(
                            contract_parameter.name,
                            implementation_parameter.name,
                        )
                        self.assertEqual(
                            contract_parameter.kind,
                            implementation_parameter.kind,
                        )
                        self.assertEqual(
                            contract_parameter.annotation,
                            implementation_parameter.annotation,
                        )
                        self.assertEqual(
                            contract_parameter.default is not Parameter.empty,
                            implementation_parameter.default is not Parameter.empty,
                        )
                        self.assertEqual(
                            type(contract_parameter.default),
                            type(implementation_parameter.default),
                        )
                    self.assertEqual(
                        contract_signature.return_annotation,
                        implementation_signature.return_annotation,
                    )
                    self.assertEqual(
                        iscoroutinefunction(contract_member),
                        iscoroutinefunction(implementation_member),
                    )

    def testConfigurationKeywordArgumentsDescribeValues(self) -> None:
        """
        Type each variadic keyword value according to what callers pass.

        Returns
        -------
        None
            Assert that configuration values and path values are correctly typed.
        """
        self.assertEqual(
            signature(IApplication.withConfigApp)
            .parameters["app_config"]
            .annotation,
            "object",
        )
        self.assertEqual(
            signature(IApplication.withConfigPaths)
            .parameters["paths"]
            .annotation,
            "str | Path | None",
        )
        self.assertEqual(
            signature(IApplication.path).return_annotation,
            "Path | Mapping[str, Path] | None",
        )

    def testPathReturnsReadOnlyMappingWhenAllPathsAreRequested(self) -> None:
        """
        Preserve the actual immutable bootstrap mapping promised by the contract.

        Returns
        -------
        None
            Assert that full path access returns a read-only mapping.
        """
        app = object.__new__(Application)
        Application.__init__(app)
        root = Path.cwd()
        app._Application__bootstrap = {"paths": {"root": root}}
        app._Application__commitConfig()

        paths = app.path()

        self.assertIsInstance(paths, MappingProxyType)
        self.assertEqual(paths["root"], root)
        with self.assertRaises(TypeError):
            paths["root"] = Path("/")
