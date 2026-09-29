from inspect import Parameter, iscoroutinefunction, signature
from pathlib import Path
from types import MappingProxyType
from orionis.foundation.application import Application
from orionis.foundation.contracts.application import IApplication
from orionis.test import TestCase

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
