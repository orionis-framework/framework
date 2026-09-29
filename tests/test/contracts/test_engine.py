from abc import ABC
from orionis.test import TestCase
from orionis.test.contracts.engine import ITestingEngine
from orionis.test.core.engine import TestingEngine

# Complete catalogue of behaviours every testing engine must implement.
_CONTRACT_METHODS: tuple[str, ...] = (
    "setVerbosity",
    "setFailFast",
    "setStartDir",
    "setFilePattern",
    "setMethodPattern",
    "withoutPanel",
    "discover",
    "run",
)

def _noop_implementation(self: object, *_args: object, **_kwargs: object) -> object:
    """Return the instance itself, satisfying the fluent contract."""
    return self

def _make_engine(*, skip: str | None = None) -> type:
    """Create a concrete engine implementing the contract except one member."""
    namespace = {
        name: _noop_implementation
        for name in _CONTRACT_METHODS
        if name != skip
    }
    return type("_EngineDouble", (ITestingEngine,), namespace)

class TestITestingEngineDefinition(TestCase):

    def testContractIsAbstract(self) -> None:
        """
        Derive the contract from the abstract base class helper.

        Validates that implementations are enforced instead of merely
        suggested.
        """
        self.assertTrue(issubclass(ITestingEngine, ABC))

    def testContractCannotBeInstantiated(self) -> None:
        """
        Raise TypeError when the bare contract is instantiated.

        Validates that no partially defined engine can be created by
        accident.
        """
        with self.assertRaises(TypeError):
            ITestingEngine()  # type: ignore[abstract]

    def testDeclaresExpectedAbstractMethods(self) -> None:
        """
        Declare exactly the documented catalogue of abstract methods.

        Validates the public surface every engine implementation must
        provide.
        """
        self.assertEqual(
            set(ITestingEngine.__abstractmethods__),
            set(_CONTRACT_METHODS),
        )

    def testEveryContractMethodIsDocumented(self) -> None:
        """
        Attach a docstring to every declared contract method.

        Validates that the interface remains self-describing for
        implementers.
        """
        for name in _CONTRACT_METHODS:
            self.assertIsNotNone(getattr(ITestingEngine, name).__doc__)

class TestITestingEngineImplementations(TestCase):

    def testCompleteImplementationCanBeInstantiated(self) -> None:
        """
        Instantiate a subclass implementing every abstract method.

        Validates that the contract imposes no hidden requirement beyond
        its declared members.
        """
        engine = _make_engine()()
        self.assertIsInstance(engine, ITestingEngine)

    def testIncompleteImplementationIsRejected(self) -> None:
        """
        Raise TypeError when any single contract method is missing.

        Validates that every declared member is individually mandatory.
        """
        for name in _CONTRACT_METHODS:
            with self.assertRaises(TypeError):
                _make_engine(skip=name)()

    def testEngineSatisfiesTheContract(self) -> None:
        """
        Confirm the production engine implements the contract.

        Validates that TestingEngine can be resolved wherever the
        contract is requested.
        """
        self.assertTrue(issubclass(TestingEngine, ITestingEngine))

    def testEngineOverridesEveryContractMethod(self) -> None:
        """
        Override every abstract member in the production engine.

        Validates that no contract method is inherited unimplemented
        from the abstract base class.
        """
        for name in _CONTRACT_METHODS:
            self.assertIsNot(
                getattr(TestingEngine, name),
                getattr(ITestingEngine, name),
            )
