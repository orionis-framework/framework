from dataclasses import dataclass
from types import SimpleNamespace
from typing import ClassVar
from orionis.test import TestCase
from tests.http._support import replace_attribute

class _InheritedValue:
    """Expose a class-owned value for instance override checks."""

    value: ClassVar[int] = 1

class _DescriptorOwner:
    """Expose a descriptor whose original object must survive replacement."""

    @staticmethod
    def read() -> int:
        """Return the original descriptor result."""
        return 1

@dataclass(slots=True)
class _SlottedValue:
    """Store a replaceable value without an instance dictionary."""

    value: int = 1

class TestTemporaryAttributeReplacement(TestCase):
    """Verify restoration of attributes used to isolate HTTP collaborators."""

    def testRestoresAnOwnedAttributeIncludingNone(self) -> None:
        """
        Restore an existing value after the replacement context exits.

        Validates that None is retained as a real value rather than absence.
        """
        target = SimpleNamespace(value=None)
        with replace_attribute(target, "value", 2):
            self.assertEqual(target.value, 2)
        self.assertIsNone(target.value)

    def testRemovesAnAttributeCreatedByTheContext(self) -> None:
        """
        Remove a temporary attribute that did not originally exist.

        Validates that a test cannot leave a new attribute on its collaborator.
        """
        target = SimpleNamespace()
        with replace_attribute(target, "value", 2):
            self.assertEqual(target.value, 2)
        self.assertFalse(hasattr(target, "value"))

    def testRestoresInheritedAttributeOwnership(self) -> None:
        """
        Remove an instance override while retaining its inherited class value.

        Validates that restoration does not materialize inherited attributes.
        """
        target = _InheritedValue()
        with replace_attribute(target, "value", 2):
            self.assertEqual(target.value, 2)
        self.assertEqual(target.value, 1)
        self.assertNotIn("value", vars(target))

    def testRestoresTheOriginalDescriptor(self) -> None:
        """
        Restore the descriptor itself after temporarily replacing a method.

        Validates that static binding semantics remain intact for later tests.
        """
        def replacement() -> int:
            """Return the temporary descriptor result."""
            return 2

        original = vars(_DescriptorOwner)["read"]
        with replace_attribute(_DescriptorOwner, "read", staticmethod(replacement)):
            self.assertEqual(_DescriptorOwner.read(), 2)
        self.assertIs(vars(_DescriptorOwner)["read"], original)
        self.assertEqual(_DescriptorOwner().read(), 1)

    def testRestoresSlottedValues(self) -> None:
        """
        Restore a value on an object without an instance dictionary.

        Validates replacement of slotted transport and request collaborators.
        """
        target = _SlottedValue()
        with replace_attribute(target, "value", 2):
            self.assertEqual(target.value, 2)
        self.assertEqual(target.value, 1)

    def testRestoresValuesAfterAnException(self) -> None:
        """
        Restore the original value when the tested operation raises.

        Validates that failed assertions or collaborators cannot leak overrides.
        """
        target = SimpleNamespace(value=1)
        with (
            self.assertRaises(ValueError),
            replace_attribute(target, "value", 2),
        ):
            error_msg = "The collaborator failed."
            raise ValueError(error_msg)
        self.assertEqual(target.value, 1)
