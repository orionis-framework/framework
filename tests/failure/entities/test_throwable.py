from __future__ import annotations
import dataclasses
import sys
import types
from orionis.failure.entities.throwable import Throwable
from orionis.test import TestCase

class TestThrowableCreation(TestCase):

    def testCreatesWithAllFields(self) -> None:
        """Create a Throwable with all fields explicitly supplied.

        Validates that classtype, message, args, and traceback are stored
        correctly when every argument is provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        tb = None
        throwable = Throwable(
            classtype=ValueError,
            message="bad value",
            args=("bad value",),
            traceback=tb,
        )
        self.assertIs(throwable.classtype, ValueError)
        self.assertEqual(throwable.message, "bad value")
        self.assertEqual(throwable.args, ("bad value",))
        self.assertIsNone(throwable.traceback)

    def testCreatesWithDefaultTraceback(self) -> None:
        """Create a Throwable without supplying a traceback.

        Validates that the traceback field defaults to None when omitted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        throwable = Throwable(
            classtype=RuntimeError,
            message="oops",
            args=("oops",),
        )
        self.assertIsNone(throwable.traceback)

    def testCreatesWithLiveTraceback(self) -> None:
        """Store a real traceback object inside a Throwable.

        Validates that the traceback field accepts an actual TracebackType
        captured from a live exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        KeyError
            Raised by this helper to exercise the failure path.
        """
        tb: types.TracebackType | None = None
        key_msg = "missing"
        try:
            raise KeyError(key_msg)
        except KeyError:
            tb = sys.exc_info()[2]

        throwable = Throwable(
            classtype=KeyError,
            message="missing",
            args=("missing",),
            traceback=tb,
        )
        self.assertIsInstance(throwable.traceback, types.TracebackType)

    def testClasstypeIsStoredExactly(self) -> None:
        """Store the supplied exception class without modification.

        Validates identity equality between the stored classtype and the
        original class passed to the constructor.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        throwable = Throwable(
            classtype=TypeError,
            message="type error",
            args=("type error",),
        )
        self.assertIs(throwable.classtype, TypeError)

    def testArgsCanBeEmptyTuple(self) -> None:
        """Accept an empty tuple for the args field.

        Validates that Throwable does not reject a zero-length args tuple,
        which may occur when an exception is raised without arguments.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        throwable = Throwable(
            classtype=Exception,
            message="",
            args=(),
        )
        self.assertEqual(throwable.args, ())
        self.assertEqual(throwable.message, "")

    def testArgsCanContainMultipleElements(self) -> None:
        """Store a multi-element args tuple without modification.

        Validates that Throwable preserves all elements when more than
        one argument is supplied.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        throwable = Throwable(
            classtype=ValueError,
            message="first",
            args=("first", "second", "third"),
        )
        self.assertEqual(len(throwable.args), 3)
        self.assertEqual(throwable.args[1], "second")

class TestThrowableImmutability(TestCase):

    def testIsFrozen(self) -> None:
        """Raise FrozenInstanceError when mutating a Throwable field.

        Validates that the frozen dataclass prevents attribute assignment
        after construction.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        throwable = Throwable(
            classtype=Exception,
            message="immutable",
            args=("immutable",),
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            throwable.message = "changed"  # type: ignore[misc]

    def testHashable(self) -> None:
        """Confirm that a Throwable instance is hashable.

        Validates that frozen dataclasses are accepted as dict keys and
        set members, which requires a valid __hash__ implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        throwable = Throwable(
            classtype=Exception,
            message="hashable",
            args=("hashable",),
        )
        mapping = {throwable: True}
        self.assertTrue(mapping[throwable])

    def testEqualityBasedOnFields(self) -> None:
        """Compare two Throwable instances by field values.

        Validates that two instances with identical fields are considered
        equal by the dataclass-generated __eq__ method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        t1 = Throwable(classtype=ValueError, message="x", args=("x",))
        t2 = Throwable(classtype=ValueError, message="x", args=("x",))
        self.assertEqual(t1, t2)

    def testInequalityOnDifferentMessage(self) -> None:
        """Distinguish two Throwable instances with different messages.

        Validates that field-level equality is strict so that differing
        messages produce unequal instances.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        t1 = Throwable(classtype=ValueError, message="a", args=("a",))
        t2 = Throwable(classtype=ValueError, message="b", args=("b",))
        self.assertNotEqual(t1, t2)

    def testInequalityOnDifferentClasstype(self) -> None:
        """Distinguish two Throwable instances with different classtypes.

        Validates that the classtype participates in equality comparison
        so that differing exception classes produce unequal instances.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        t1 = Throwable(classtype=ValueError, message="x", args=("x",))
        t2 = Throwable(classtype=TypeError, message="x", args=("x",))
        self.assertNotEqual(t1, t2)

class TestThrowableRepr(TestCase):

    def testReprContainsClassName(self) -> None:
        """Include the class name in the Throwable repr string.

        Validates that the default dataclass repr includes
        the ``Throwable`` identifier for easy identification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        throwable = Throwable(
            classtype=OSError,
            message="io",
            args=("io",),
        )
        self.assertIn("Throwable", repr(throwable))

    def testReprContainsMessage(self) -> None:
        """Include the message value in the Throwable repr string.

        Validates that the message field appears in the representation
        output so it can be identified in logs and debug sessions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        throwable = Throwable(
            classtype=OSError,
            message="disk full",
            args=("disk full",),
        )
        self.assertIn("disk full", repr(throwable))
