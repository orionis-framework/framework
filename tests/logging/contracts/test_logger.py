import inspect
import logging
from abc import ABC
from orionis.logging.contracts.logger import ILogger
from orionis.logging.logger import Logger
from orionis.test import TestCase

# Complete abstract surface published by the logging contract.
_ABSTRACT_MEMBERS = frozenset({
    "close",
    "critical",
    "debug",
    "error",
    "getActiveChannel",
    "getActiveChannels",
    "getAvailableChannels",
    "getLogger",
    "info",
    "name",
    "reloadConfiguration",
    "switchChannel",
    "warning",
})

class _CompleteLogger(ILogger):
    """Fully implemented logger used to verify the contract surface."""

    @property
    def name(self) -> str:
        """Return the logger name."""
        return "complete"

    def info(self, _message: str) -> None:
        """Discard an informational message."""

    def error(self, _message: str) -> None:
        """Discard an error message."""

    def warning(self, _message: str) -> None:
        """Discard a warning message."""

    def debug(self, _message: str) -> None:
        """Discard a debug message."""

    def critical(self, _message: str) -> None:
        """Discard a critical message."""

    def getLogger(self) -> logging.Logger:
        """Return a standard library logger."""
        return logging.getLogger("orionis-contract-probe")

    def reloadConfiguration(self) -> None:
        """Ignore the configuration reload request."""

    def switchChannel(self, _channel_name: str) -> bool:
        """Report a successful channel switch."""
        return True

    def close(self) -> None:
        """Ignore the shutdown request."""

    def getAvailableChannels(self) -> list[str]:
        """Return no configured channel."""
        return []

    def getActiveChannel(self) -> str | None:
        """Return no active channel."""
        return None

    def getActiveChannels(self) -> list[str]:
        """Return no active channel."""
        return []

class _IncompleteLogger(ILogger):
    """Logger implementing a single member of the contract on purpose."""

    @property
    def name(self) -> str:
        """Return the logger name."""
        return "incomplete"

class TestILoggerContract(TestCase):

    def testIsAnAbstractContract(self) -> None:
        """
        Expose the logger contract as a non instantiable abstraction.

        Validates that consumers can only depend on implementations bound in
        the container.
        """
        self.assertTrue(issubclass(ILogger, ABC))
        self.assertTrue(inspect.isabstract(ILogger))
        with self.assertRaises(TypeError):
            ILogger()

    def testDeclaresTheCompleteAbstractSurface(self) -> None:
        """
        Declare every member required from a logging implementation.

        Validates the public contract so that adding or removing a member is
        an explicit decision.
        """
        self.assertEqual(ILogger.__abstractmethods__, _ABSTRACT_MEMBERS)

    def testNameIsDeclaredAsAProperty(self) -> None:
        """
        Expose the service name as a read only property.

        Validates that implementations may shadow it with a plain class
        attribute without breaking the contract.
        """
        self.assertIsInstance(ILogger.__dict__["name"], property)

    def testEveryAbstractMemberIsDocumented(self) -> None:
        """
        Document every member of the contract.

        Validates that implementers always find the expected behaviour
        described in the abstraction itself.
        """
        for member in sorted(_ABSTRACT_MEMBERS):
            self.assertTrue(inspect.getdoc(getattr(ILogger, member)))

    def testIncompleteImplementationCannotBeInstantiated(self) -> None:
        """
        Reject an implementation missing part of the contract.

        Validates that the abstraction is enforced at instantiation time.
        """
        with self.assertRaises(TypeError):
            _IncompleteLogger()

    def testCompleteImplementationCanBeInstantiated(self) -> None:
        """
        Accept an implementation covering the whole contract.

        Validates that the declared surface is sufficient to build a usable
        logging service.
        """
        self.assertIsInstance(_CompleteLogger(), ILogger)

    def testFrameworkLoggerMatchesTheContractSignatures(self) -> None:
        """
        Keep the framework logger aligned with the contract signatures.

        Validates that every implemented member accepts exactly the parameters
        declared by the abstraction.
        """
        for member in sorted(_ABSTRACT_MEMBERS - {"name"}):
            expected = inspect.signature(getattr(ILogger, member))
            actual = inspect.signature(getattr(Logger, member))
            self.assertEqual(
                list(actual.parameters),
                list(expected.parameters),
                msg=f"Signature drift detected on '{member}'.",
            )
