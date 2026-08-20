from __future__ import annotations
from abc import ABC
from orionis.session.contracts.session import ISession
from orionis.session.session import Session
from orionis.test import TestCase

class TestISessionContract(TestCase):
    """Unit tests for the ISession abstract contract."""

    def testContractIsAbstract(self) -> None:
        """
        Declare ISession as an abstract base class.

        Validates that the contract participates in the ABC machinery
        instead of being a plain class.
        """
        self.assertIn(ABC.__name__, [base.__name__ for base in ISession.__mro__])

    def testContractCannotBeInstantiated(self) -> None:
        """
        Reject direct instantiation of the contract.

        Validates that abstract members must be implemented by a
        concrete session class.
        """
        with self.assertRaises(TypeError):
            ISession()  # type: ignore[abstract]

    def testContractDeclaresEmptySlots(self) -> None:
        """
        Keep the contract slot-free so implementations stay dictless.

        Validates that ``__slots__`` is empty, otherwise every session
        instance would carry a per-instance dictionary.
        """
        self.assertEqual(ISession.__slots__, ())

    def testSessionImplementsContract(self) -> None:
        """
        Register Session as a concrete implementation of the contract.

        Validates the inheritance relationship relied upon by the
        container binding.
        """
        self.assertIsInstance(Session(), ISession)

    def testSessionImplementsEveryAbstractMember(self) -> None:
        """
        Leave no abstract member unimplemented in Session.

        Validates that the concrete class overrides the full contract,
        so instantiation never fails at runtime.
        """
        self.assertEqual(Session.__abstractmethods__, frozenset())

    def testSessionInstancesHaveNoInstanceDictionary(self) -> None:
        """
        Build sessions without a per-instance dictionary.

        Validates that the slot declarations of both the contract and
        the implementation are effective.
        """
        self.assertFalse(hasattr(Session(), "__dict__"))

    def testContractDeclaresExpectedMembers(self) -> None:
        """
        Expose the full public session API through the contract.

        Validates that every method the framework calls on a session is
        part of the abstract surface.
        """
        expected = {
            "all",
            "clear",
            "dirty",
            "flash",
            "flashErrors",
            "flashInput",
            "forget",
            "get",
            "getErrors",
            "getFlash",
            "getOldInput",
            "getPreviousUrl",
            "has",
            "id",
            "invalidate",
            "invalidated",
            "isNew",
            "put",
            "regenerate",
            "setPreviousUrl",
            "started",
            "wantsRegenerate",
        }
        self.assertEqual(set(ISession.__abstractmethods__), expected)
