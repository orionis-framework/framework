from __future__ import annotations
import threading
from orionis.test import TestCase
from orionis.support.patterns.final.meta import Final

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

class _BaseFinal(metaclass=Final):
    """Minimal class marked as final."""

    def value(self) -> int:
        """Return the value exposed by the final test class.

        Returns
        -------
        int
            Value produced by the helper.
        """
        return 42

class _UnrelatedBase:
    """Non-final class used for valid inheritance checks."""

# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestFinalMeta(TestCase):

    # ------------------------------------------------ creation

    def testFinalClassCanBeCreated(self) -> None:
        """Create a class with the Final metaclass without errors.

        Validates that defining a class with ``metaclass=Final`` succeeds
        and produces a usable type object.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(type(_BaseFinal), Final))

    def testFinalClassIsMarkedAsFinal(self) -> None:
        """Mark a new class with the __is_final__ attribute.

        Validates that every class whose metaclass is Final gets the
        ``__is_final__`` flag set to True in its own ``__dict__``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(_BaseFinal.__dict__.get("__is_final__", False))

    def testFinalClassIsInstantiable(self) -> None:
        """Instantiate a final class successfully.

        Validates that a class created with the Final metaclass can be
        instantiated and its methods are accessible.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        obj = _BaseFinal()
        self.assertEqual(obj.value(), 42)

    # ------------------------------------------------ inheritance prevention

    def testInheritingFromFinalClassRaisesTypeError(self) -> None:
        """Raise TypeError when inheriting from a final class.

        Validates that attempting to subclass a Final-marked class raises
        a TypeError with a descriptive message.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            class _Child(_BaseFinal):
                pass

    def testErrorMessageContainsFinalClassName(self) -> None:
        """Include the final class name in the TypeError message.

        Validates that the error message raised when inheriting from a
        final class explicitly names the class that cannot be subclassed.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        AssertionError
            Raised by this helper to exercise the failure path.
        """
        try:
            class _Child(_BaseFinal):
                pass
        except TypeError as exc:
            self.assertIn("_BaseFinal", str(exc))
        else:
            error_msg = "Expected TypeError was not raised"
            raise AssertionError(error_msg)

    def testInheritingFromNonFinalBaseSucceeds(self) -> None:
        """Allow subclassing of a non-final class.

        Validates that ordinary classes that do not use the Final metaclass
        can still be freely subclassed.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _Child(_UnrelatedBase):
            pass

        obj = _Child()
        self.assertIsInstance(obj, _UnrelatedBase)

    def testMultipleLevelFinalInheritanceRaisesTypeError(self) -> None:
        """Raise TypeError for indirect inheritance via an intermediate class.

        Validates that inheriting indirectly through a non-final class from
        a final class is still blocked.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _NonFinal(_UnrelatedBase):
            pass

        # Directly from the final class — must still be blocked
        with self.assertRaises(TypeError):
            class _GrandChild(_BaseFinal, _NonFinal):
                pass

    # ------------------------------------------------ multiple final classes

    def testTwoIndependentFinalClassesCanCoexist(self) -> None:
        """Create two independent final classes without interference.

        Validates that multiple unrelated classes can each independently
        carry the Final metaclass without blocking each other's creation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _FinalA(metaclass=Final):
            pass

        class _FinalB(metaclass=Final):
            pass

        self.assertTrue(_FinalA.__dict__.get("__is_final__", False))
        self.assertTrue(_FinalB.__dict__.get("__is_final__", False))

    def testFinalClassWithCustomAttributes(self) -> None:
        """Create a final class with class-level and instance attributes.

        Validates that the Final metaclass does not interfere with normal
        class body definitions such as constants and methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class _Config(metaclass=Final):
            VERSION: str = "1.0"

            def get_version(self) -> str:
                """Return the configured version.

                Returns
                -------
                str
                    Value produced by the helper.
                """
                return self.VERSION

        obj = _Config()
        self.assertEqual(obj.get_version(), "1.0")
        self.assertEqual(_Config.VERSION, "1.0")

    # ------------------------------------------------ identity / type checks

    def testFinalMetaclassIsFinalType(self) -> None:
        """Confirm the metaclass of a final class is Final.

        Validates that ``type(_BaseFinal)`` is exactly ``Final``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(type(_BaseFinal), Final)

    def testFinalClassDoesNotBreakIsinstance(self) -> None:
        """Preserve isinstance semantics for final class instances.

        Validates that an instance of a final class is correctly recognised
        by isinstance checks against its own class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        obj = _BaseFinal()
        self.assertIsInstance(obj, _BaseFinal)

    def testFinalClassSupportsInheritanceGuardInConcurrency(self) -> None:
        """Raise TypeError consistently under concurrent class creation.

        Validates that the inheritance guard works correctly when multiple
        threads simultaneously attempt to subclass a final class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        errors: list[Exception] = []
        results: list[bool] = []

        def _try_subclass() -> None:
            """Attempt inheritance and record whether the final guard rejects it.

            Returns
            -------
            None
                Completes the operation described above.
            """
            try:
                type("_Dynamic", (_BaseFinal,), {})
            except TypeError:
                results.append(True)
            except (RuntimeError, AttributeError, NameError) as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_try_subclass) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 10)
