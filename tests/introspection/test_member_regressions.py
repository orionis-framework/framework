# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Exercise member visibility and reversible instance mutations."""

from orionis.introspection.concretes.reflection import ReflectionConcrete
from orionis.introspection.instances.reflection import ReflectionInstance
from orionis.introspection.reflection import Reflection
from orionis.test import TestCase


class _MemberFixture:
    """Provide names that merely resemble private-name mangling."""

    _MemberFixtureExtra: int = 7
    __private: int = 9

    def __init__(self) -> None:
        """Create matching instance values and a removable null attribute."""
        self._MemberFixtureExtra = 7
        self.__private = 9
        self.empty = None

    def _protectedAction(self) -> int:
        """Return a protected member with a class-name prefix."""
        return 7

    _MemberFixtureAction = _protectedAction
    """Expose a deliberately misleading name as fixture data for mangling checks."""


def _injected(value: int = 11) -> int:
    """Return the injected method value."""
    return value


class TestMemberRegressions(TestCase):
    """Keep member metadata aligned with the reflected Python object."""

    def testPrivateNamesRequireTheFullMangledPrefix(self) -> None:
        """Do not demangle protected names that start with the class name."""
        for reflected in (
            ReflectionConcrete(_MemberFixture),
            ReflectionInstance(_MemberFixture()),
        ):
            with self.subTest(reflection=type(reflected).__name__):
                self.assertEqual(
                    reflected.getProtectedAttributes(),
                    {"_MemberFixtureExtra": 7},
                )
                self.assertEqual(reflected.getPrivateAttributes(), {"__private": 9})
                self.assertIn("_MemberFixtureAction", reflected.getProtectedMethods())
                self.assertIn("_MemberFixtureExtra", reflected.getAnnotations())

    def testNullAttributesCanBeRemoved(self) -> None:
        """Distinguish a missing attribute from a present null value."""
        instance = _MemberFixture()
        reflected = ReflectionInstance(instance)
        self.assertTrue(reflected.removeAttribute("empty"))
        self.assertFalse(hasattr(instance, "empty"))

    def testInjectedMethodsAreDiscoverableAndRemovable(self) -> None:
        """Read and remove instance callables without modifying the class."""
        instance = _MemberFixture()
        reflected = ReflectionInstance(instance)
        self.assertTrue(reflected.setMethod("injected", _injected))
        self.assertTrue(reflected.hasMethod("injected"))
        self.assertIn("injected", reflected.getPublicMethods())
        self.assertEqual(
            tuple(reflected.getMethodSignature("injected").parameters),
            ("value",),
        )
        self.assertEqual(reflected.getMethodDocstring("injected"), _injected.__doc__)
        self.assertEqual(
            reflected.methodSignature("injected").ordered["value"].default,
            11,
        )
        self.assertIn("def _injected", reflected.getSourceCode("injected"))
        reflected.removeMethod("injected")
        self.assertFalse(reflected.hasMethod("injected"))
        self.assertFalse(hasattr(instance, "injected"))
        self.assertTrue(hasattr(_MemberFixture, "_MemberFixtureAction"))

    def testDunderMethodNamesExcludeDataDescriptors(self) -> None:
        """List callable special methods rather than every special attribute."""
        methods = ReflectionInstance(_MemberFixture()).getDunderMethods()
        self.assertIn("__init__", methods)
        for name in ("__dict__", "__weakref__", "__module__", "__doc__"):
            with self.subTest(name=name):
                self.assertNotIn(name, methods)

    def testUserClassesAreNotClassifiedByTheirNames(self) -> None:
        """Reject built-in classes and distinguish real typing constructs."""
        fake_typing = type("List", (), {})()
        self.assertFalse(Reflection.isTypingConstruct(fake_typing))
        for builtin in (int, str, dict, list):
            with self.subTest(builtin=builtin):
                self.assertFalse(Reflection.isConcreteClass(builtin))
                with self.assertRaises(TypeError):
                    ReflectionConcrete(builtin)

    def testSlotValuesAndUnmangledPrivateNamesRemainAccessible(self) -> None:
        """Reflect stored slot values and classes whose names are underscores."""
        base = type("SlotBase", (), {"__slots__": ("inherited",)})
        derived = type("SlotDerived", (base,), {"__slots__": ("value", "unused")})
        instance = derived()
        instance.inherited = 2
        instance.value = 3
        reflected = ReflectionInstance(instance)
        self.assertEqual(reflected.getAttributes(), {"inherited": 2, "value": 3})
        self.assertEqual(reflected.getAttribute("value"), 3)
        self.assertTrue(reflected.removeAttribute("value"))
        self.assertNotIn("value", reflected.getAttributes())
        underscore_class = type(
            "___",
            (),
            {"__private": 7, "__annotations__": {"__private": int}},
        )
        underscore_instance = underscore_class()
        setattr(underscore_instance, "__private", 7)
        for target in (
            ReflectionConcrete(underscore_class),
            ReflectionInstance(underscore_instance),
        ):
            with self.subTest(reflection=type(target).__name__):
                self.assertEqual(target.getPrivateAttributes(), {"__private": 7})
                self.assertIn("__private", target.getAnnotations())
                self.assertTrue(target.setAttribute("__private", 9))
                self.assertEqual(target.getAttribute("__private"), 9)
                self.assertTrue(target.removeAttribute("__private"))

    def testIdentityRefreshPreservesDeclaredPrivateNames(self) -> None:
        """Refresh mutable class identity without remangling existing fields."""
        for wrapper in (ReflectionConcrete, ReflectionInstance):
            with self.subTest(wrapper=wrapper.__name__):
                cls = type("Original", (), {"_Original__private": 7})
                instance = cls()
                instance._Original__private = 7
                reflected = wrapper(cls if wrapper is ReflectionConcrete else instance)
                reflected.getModuleWithClassName()
                reflected.getPrivateAttributes()
                if wrapper is ReflectionConcrete:
                    reflected.setAttribute("__name__", "Renamed")
                    reflected.setAttribute("__module__", "synthetic.reflected")
                else:
                    cls.__name__ = "Renamed"
                    cls.__module__ = "synthetic.reflected"
                    reflected.clearCache()
                self.assertEqual(reflected.getClassName(), "Renamed")
                self.assertEqual(reflected.getModuleName(), "synthetic.reflected")
                self.assertEqual(
                    reflected.getModuleWithClassName(),
                    "synthetic.reflected.Renamed",
                )
                self.assertEqual(reflected.getPrivateAttributes(), {"__private": 7})
                cls.__name__ = "RenamedAgain"
                reflected.clearCache()
                self.assertEqual(reflected.getClassName(), "RenamedAgain")
                self.assertEqual(reflected.getPrivateAttributes(), {"__private": 7})
