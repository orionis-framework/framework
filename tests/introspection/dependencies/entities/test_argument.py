from __future__ import annotations
from dataclasses import FrozenInstanceError
from orionis.introspection.dependencies.entities.argument import Argument
from orionis.test import TestCase

def _make_argument(**overrides: object) -> Argument:
    """Create a valid Argument instance with sensible defaults."""
    defaults = {
        "name": "my_service",
        "resolved": True,
        "module_name": "orionis.services.cache",
        "class_name": "FileBasedCache",
        "type": object,
        "full_class_path": "orionis.services.cache.FileBasedCache",
    }
    defaults.update(overrides)
    return Argument(**defaults)  # type: ignore[arg-type]

# ===========================================================================
# TestArgument
# ===========================================================================

class TestArgument(TestCase):

    def testCanBeInstantiatedWithRequiredFields(self) -> None:
        """
        Assert that Argument can be created with all required fields.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument()
        self.assertIsInstance(arg, Argument)

    def testNameIsPersisted(self) -> None:
        """
        Assert that the name field is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument(name="my_dep")
        self.assertEqual(arg.name, "my_dep")

    def testResolvedIsPersisted(self) -> None:
        """
        Assert that the resolved flag is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument(resolved=True)
        self.assertTrue(arg.resolved)

    def testModuleNameIsPersisted(self) -> None:
        """
        Assert that module_name is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument(module_name="orionis.services.log")
        self.assertEqual(arg.module_name, "orionis.services.log")

    def testClassNameIsPersisted(self) -> None:
        """
        Assert that class_name is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument(class_name="Logger")
        self.assertEqual(arg.class_name, "Logger")

    def testTypeIsPersisted(self) -> None:
        """
        Assert that the type field is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument(type=str)
        self.assertIs(arg.type, str)

    def testFullClassPathIsPersisted(self) -> None:
        """
        Assert that full_class_path is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument(full_class_path="orionis.services.log.Logger")
        self.assertEqual(arg.full_class_path, "orionis.services.log.Logger")

    def testIsKeywordOnlyDefaultsFalse(self) -> None:
        """
        Assert that is_keyword_only defaults to False.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument()
        self.assertFalse(arg.is_keyword_only)

    def testIsKeywordOnlyCanBeSetTrue(self) -> None:
        """
        Assert that is_keyword_only can be set to True.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument(is_keyword_only=True)
        self.assertTrue(arg.is_keyword_only)

    def testDefaultIsNoneByDefault(self) -> None:
        """
        Assert that default is None when not provided.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument()
        self.assertIsNone(arg.default)

    def testDefaultCanBeSet(self) -> None:
        """
        Assert that a non-None default is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument(default="fallback", resolved=False)
        self.assertEqual(arg.default, "fallback")

    def testIsFrozenDataclass(self) -> None:
        """
        Assert that Argument raises FrozenInstanceError on attribute mutation.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument()
        with self.assertRaises(FrozenInstanceError):
            arg.name = "changed"  # type: ignore[misc]

    def testTypeErrorWhenModuleNameIsNotString(self) -> None:
        """
        Assert that TypeError is raised when module_name is not a string.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            _make_argument(module_name=123)

    def testTypeErrorWhenClassNameIsNotString(self) -> None:
        """
        Assert that TypeError is raised when class_name is not a string.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            _make_argument(class_name=42)

    def testTypeErrorWhenFullClassPathIsNotString(self) -> None:
        """
        Assert that TypeError is raised when full_class_path is not a string.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            _make_argument(full_class_path=99)

    def testValueErrorWhenTypeIsNoneAndResolvedAndNoDefault(self) -> None:
        """
        Assert that ValueError is raised when type is None, resolved=True, default=None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(ValueError):
            _make_argument(type=None, resolved=True, default=None)

    def testNoValidationWhenDefaultIsProvided(self) -> None:
        """
        Assert that validation is skipped when a default value is given.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = Argument(
            name="optional_dep",
            resolved=False,
            module_name="",
            class_name="",
            type=None,
            full_class_path="",
            default="some_default",
        )
        self.assertEqual(arg.default, "some_default")

    def testEqualityBetweenIdenticalArguments(self) -> None:
        """
        Assert that two Argument instances with equal fields are equal.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg1 = _make_argument()
        arg2 = _make_argument()
        self.assertEqual(arg1, arg2)

    def testIsHashable(self) -> None:
        """
        Assert that a frozen Argument instance can be hashed.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(hash(_make_argument()), hash(_make_argument()))

