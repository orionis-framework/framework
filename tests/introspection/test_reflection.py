# ruff: noqa: B024, PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# A nominal ABC with no abstract members is an intentional classification target.

import abc
import inspect
import types
import sys
import typing

if typing.TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
from orionis.introspection.reflection import Reflection
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _AbstractFixture(abc.ABC):
    """Abstract class fixture for isAbstract / isConcreteClass checks."""

    @abc.abstractmethod
    def run(self) -> None:
        """Run the abstract operation.

        Returns
        -------
        None
            No return value.
        """


class _ConcreteFixture:
    """Concrete user-defined class fixture."""

    def __init__(self, value: int = 0) -> None:
        """Initialize the test helper.

        Parameters
        ----------
        value : int
            Value supplied for ``value``.

        Returns
        -------
        None
            No return value.
        """
        self.value = value


class _ABCDirectBase(abc.ABC):
    """Class that inherits directly from abc.ABC (used in isConcreteClass)."""


class _ProtocolFixture(typing.Protocol):
    """Protocol fixture for isProtocol checks."""

    def greet(self) -> str:
        """Return a greeting.

        Returns
        -------
        str
            Value produced by the helper.
        """
        ...


class _SlottedFixture:
    """Class with __slots__ used to obtain a member descriptor."""

    __slots__ = ("slot_attr",)


class _DescriptorFixture:
    """Class exposing a pure-Python property descriptor."""

    @property
    def value(self) -> int:
        """
        Return a fixed integer.

        Returns
        -------
        int
            Always returns 0.
        """
        return 0


class _OriginFixture:
    """Class carrying a legacy __origin__ marker for isGeneric checks."""

    __origin__ = list


def _sync_gen() -> Iterator[int]:
    """Yield integers as a synchronous generator fixture.

    Yields
    ------
    int
        The fixture value 1.
    """
    yield 1


async def _async_gen() -> AsyncIterator[int]:
    """Yield integers as an asynchronous generator fixture.

    Yields
    ------
    int
        The fixture value 1.
    """
    yield 1


async def _coroutine_fn() -> int:
    """Return 1 as an async coroutine fixture.

    Returns
    -------
    int
        Value produced by the helper.
    """
    return 1


def _plain_fn() -> int:
    """Return 1 as a plain function fixture.

    Returns
    -------
    int
        Value produced by the helper.
    """
    return 1


# ---------------------------------------------------------------------------
# factory methods — instance, abstract, concrete, module, callable
# ---------------------------------------------------------------------------


class TestReflectionInstance(TestCase):
    def testInstanceReturnsWrappedObject(self) -> None:
        """
        Assert that instance() returns a reflection object for a class instance.

        Returns
        -------
        None
            No return value.
        """
        obj = _ConcreteFixture(42)
        ri = Reflection.instance(obj)
        self.assertIs(ri.getInstance(), obj)

    def testInstanceRejectsBuiltinInstance(self) -> None:
        """
        Assert that instance() raises TypeError for built-in type instances.

        Returns
        -------
        None
            No return value.
        """
        # Built-in instances (str, list, int) are not user-defined objects
        for obj in ["hello", [1, 2], {"k": "v"}, 3.14]:
            with self.assertRaises(TypeError):
                Reflection.instance(obj)

    def testInstanceRejectsPrimitiveInt(self) -> None:
        """
        Assert that instance() raises TypeError for a plain integer value.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            Reflection.instance(99)


class TestReflectionAbstract(TestCase):
    def testAbstractReturnsReflectionObject(self) -> None:
        """
        Assert that abstract() returns a reflection object for an ABC.

        Returns
        -------
        None
            No return value.
        """
        ra = Reflection.abstract(_AbstractFixture)
        self.assertIs(ra.getClass(), _AbstractFixture)

    def testAbstractRaisesOnConcreteClass(self) -> None:
        """
        Assert that abstract() raises TypeError when passed a concrete class.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            Reflection.abstract(_ConcreteFixture)


class TestReflectionConcrete(TestCase):
    def testConcreteReturnsReflectionObject(self) -> None:
        """
        Assert that concrete() returns a reflection object for a concrete class.

        Returns
        -------
        None
            No return value.
        """
        rc = Reflection.concrete(_ConcreteFixture)
        self.assertIs(rc.getClass(), _ConcreteFixture)

    def testConcreteRaisesOnAbstractClass(self) -> None:
        """
        Assert that concrete() raises TypeError when passed an abstract class.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            Reflection.concrete(_AbstractFixture)


class TestReflectionModule(TestCase):
    def testModuleReturnsReflectionObject(self) -> None:
        """
        Assert that module() returns a reflection object for a valid module.

        Returns
        -------
        None
            No return value.
        """
        rm = Reflection.module("os")
        self.assertIs(rm.getModule(), sys.modules["os"])

    def testModuleWithBuiltinModuleName(self) -> None:
        """
        Assert that module() works with the built-in 'sys' module name.

        Returns
        -------
        None
            No return value.
        """
        rm = Reflection.module("sys")
        self.assertIs(rm.getModule(), sys)

    def testModuleWithInvalidNameRaisesTypeError(self) -> None:
        """
        Assert that module() raises TypeError for an unknown module name.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            Reflection.module("this.module.does.not.exist.xyz")

    def testModuleWithEmptyStringRaisesTypeError(self) -> None:
        """
        Assert that module() raises TypeError for an empty string.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            Reflection.module("")


class TestReflectionCallable(TestCase):
    def testCallableReturnsReflectionObject(self) -> None:
        """
        Assert that callable() returns a reflection object for a plain function.

        Returns
        -------
        None
            No return value.
        """
        rc = Reflection.callable(_plain_fn)
        self.assertIs(rc.getCallable(), _plain_fn)

    def testCallableWithLambda(self) -> None:
        """
        Assert that callable() accepts a lambda without raising.

        Returns
        -------
        None
            No return value.
        """
        rc = Reflection.callable(lambda x: x)
        self.assertIsNotNone(rc)

    def testCallableWithClassRaisesTypeError(self) -> None:
        """
        Assert that callable() raises TypeError when passed a class type.

        Returns
        -------
        None
            No return value.
        """
        # ReflectionCallable only accepts functions, methods, and lambdas
        with self.assertRaises(TypeError):
            Reflection.callable(_ConcreteFixture)


# ---------------------------------------------------------------------------
# isAbstract
# ---------------------------------------------------------------------------


class TestIsAbstract(TestCase):
    def testAbstractClassReturnsTrue(self) -> None:
        """
        Assert that isAbstract returns True for an ABC with abstract methods.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isAbstract(_AbstractFixture))

    def testConcreteClassReturnsFalse(self) -> None:
        """
        Assert that isAbstract returns False for a concrete class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAbstract(_ConcreteFixture))

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isAbstract returns False for a plain function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAbstract(_plain_fn))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isAbstract returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAbstract(None))

    def testIntReturnsFalse(self) -> None:
        """
        Assert that isAbstract returns False for an integer value.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAbstract(42))


# ---------------------------------------------------------------------------
# isConcreteClass
# ---------------------------------------------------------------------------


class TestIsConcreteClass(TestCase):
    def testConcreteClassReturnsTrue(self) -> None:
        """
        Assert that isConcreteClass returns True for a plain concrete class.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isConcreteClass(_ConcreteFixture))

    def testAbstractClassReturnsFalse(self) -> None:
        """
        Assert that isConcreteClass returns False for an abstract class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isConcreteClass(_AbstractFixture))

    def testBuiltinIntIsNotAUserDefinedConcreteClass(self) -> None:
        """Reject builtin classes from the user-defined concrete wrapper."""
        self.assertFalse(Reflection.isConcreteClass(int))
        with self.assertRaises(TypeError):
            Reflection.concrete(int)

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isConcreteClass returns False for a function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isConcreteClass(_plain_fn))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isConcreteClass returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isConcreteClass(None))

    def testABCDirectBaseReturnsFalse(self) -> None:
        """
        Assert that isConcreteClass returns False for a class with abc.ABC base.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isConcreteClass(_ABCDirectBase))

    def testStringReturnsFalse(self) -> None:
        """
        Assert that isConcreteClass returns False for a string instance.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isConcreteClass("hello"))

    def testProtocolReturnsFalse(self) -> None:
        """
        Assert that isConcreteClass returns False for a Protocol subclass.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isConcreteClass(_ProtocolFixture))


# ---------------------------------------------------------------------------
# isAsyncGen / isAsyncGenFunction
# ---------------------------------------------------------------------------


class TestIsAsyncGen(TestCase):
    async def testAsyncGenObjectReturnsTrue(self) -> None:
        """
        Assert that isAsyncGen returns True for an async generator object.

        Returns
        -------
        None
            No return value.
        """
        gen = _async_gen()
        try:
            self.assertTrue(Reflection.isAsyncGen(gen))
        finally:
            await gen.aclose()

    def testSyncGenObjectReturnsFalse(self) -> None:
        """
        Assert that isAsyncGen returns False for a synchronous generator.

        Returns
        -------
        None
            No return value.
        """
        gen = _sync_gen()
        self.addCleanup(gen.close)
        self.assertFalse(Reflection.isAsyncGen(gen))

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isAsyncGen returns False for a plain function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAsyncGen(_plain_fn))


class TestIsAsyncGenFunction(TestCase):
    def testAsyncGenFunctionReturnsTrue(self) -> None:
        """
        Assert that isAsyncGenFunction returns True for an async gen function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isAsyncGenFunction(_async_gen))

    def testSyncGenFunctionReturnsFalse(self) -> None:
        """
        Assert that isAsyncGenFunction returns False for a sync gen function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAsyncGenFunction(_sync_gen))

    def testPlainFunctionReturnsFalse(self) -> None:
        """
        Assert that isAsyncGenFunction returns False for a plain function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAsyncGenFunction(_plain_fn))


# ---------------------------------------------------------------------------
# isAwaitable
# ---------------------------------------------------------------------------


class TestIsAwaitable(TestCase):
    def testCoroutineObjectReturnsTrue(self) -> None:
        """
        Assert that isAwaitable returns True for a coroutine object.

        Returns
        -------
        None
            No return value.
        """
        coro = _coroutine_fn()
        self.addCleanup(coro.close)
        self.assertTrue(Reflection.isAwaitable(coro))

    def testPlainFunctionReturnsFalse(self) -> None:
        """
        Assert that isAwaitable returns False for a plain sync function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAwaitable(_plain_fn))

    def testIntReturnsFalse(self) -> None:
        """
        Assert that isAwaitable returns False for an integer.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isAwaitable(123))


# ---------------------------------------------------------------------------
# isBuiltIn
# ---------------------------------------------------------------------------


class TestIsBuiltIn(TestCase):
    def testBuiltinLenReturnsTrue(self) -> None:
        """
        Assert that isBuiltIn returns True for the built-in len function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isBuiltIn(len))

    def testBuiltinPrintReturnsTrue(self) -> None:
        """
        Assert that isBuiltIn returns True for the built-in print function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isBuiltIn(print))

    def testPlainFunctionReturnsFalse(self) -> None:
        """
        Assert that isBuiltIn returns False for a user-defined function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isBuiltIn(_plain_fn))

    def testClassReturnsFalse(self) -> None:
        """
        Assert that isBuiltIn returns False for a user-defined class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isBuiltIn(_ConcreteFixture))


# ---------------------------------------------------------------------------
# isClass
# ---------------------------------------------------------------------------


class TestIsClass(TestCase):
    def testUserClassReturnsTrue(self) -> None:
        """
        Assert that isClass returns True for a user-defined class.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isClass(_ConcreteFixture))

    def testBuiltinIntReturnsTrue(self) -> None:
        """
        Assert that isClass returns True for the built-in int type.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isClass(int))

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isClass returns False for a function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isClass(_plain_fn))

    def testInstanceReturnsFalse(self) -> None:
        """
        Assert that isClass returns False for an instance of a class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isClass(_ConcreteFixture()))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isClass returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isClass(None))


# ---------------------------------------------------------------------------
# isCode
# ---------------------------------------------------------------------------


class TestIsCode(TestCase):
    def testCodeObjectReturnsTrue(self) -> None:
        """
        Assert that isCode returns True for a function's __code__ attribute.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isCode(_plain_fn.__code__))

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isCode returns False for a function object itself.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isCode(_plain_fn))

    def testIntReturnsFalse(self) -> None:
        """
        Assert that isCode returns False for an integer.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isCode(1))


# ---------------------------------------------------------------------------
# isCoroutine / isCoroutineFunction
# ---------------------------------------------------------------------------


class TestIsCoroutine(TestCase):
    def testCoroutineObjectReturnsTrue(self) -> None:
        """
        Assert that isCoroutine returns True for a running coroutine object.

        Returns
        -------
        None
            No return value.
        """
        coro = _coroutine_fn()
        self.addCleanup(coro.close)
        self.assertTrue(Reflection.isCoroutine(coro))

    def testCoroutineFunctionReturnsFalse(self) -> None:
        """
        Assert that isCoroutine returns False for the coroutine function itself.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isCoroutine(_coroutine_fn))

    def testPlainFunctionReturnsFalse(self) -> None:
        """
        Assert that isCoroutine returns False for a plain sync function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isCoroutine(_plain_fn))


class TestIsCoroutineFunction(TestCase):
    def testAsyncFunctionReturnsTrue(self) -> None:
        """
        Assert that isCoroutineFunction returns True for an async function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isCoroutineFunction(_coroutine_fn))

    def testCoroutineObjectReturnsFalse(self) -> None:
        """
        Assert that isCoroutineFunction returns False for a coroutine object.

        Returns
        -------
        None
            No return value.
        """
        coro = _coroutine_fn()
        self.addCleanup(coro.close)
        self.assertFalse(Reflection.isCoroutineFunction(coro))

    def testPlainFunctionReturnsFalse(self) -> None:
        """
        Assert that isCoroutineFunction returns False for a sync function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isCoroutineFunction(_plain_fn))


# ---------------------------------------------------------------------------
# isDataDescriptor
# ---------------------------------------------------------------------------


class TestIsDataDescriptor(TestCase):
    def testPropertyReturnsTrue(self) -> None:
        """
        Assert that isDataDescriptor returns True for a property object.

        Returns
        -------
        None
            No return value.
        """
        # property defines __get__ and __set__ — it is a data descriptor
        self.assertTrue(Reflection.isDataDescriptor(property()))

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isDataDescriptor returns False for a plain function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isDataDescriptor(_plain_fn))

    def testIntReturnsFalse(self) -> None:
        """
        Assert that isDataDescriptor returns False for an integer.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isDataDescriptor(42))


# ---------------------------------------------------------------------------
# isFunction
# ---------------------------------------------------------------------------


class TestIsFunction(TestCase):
    def testUserFunctionReturnsTrue(self) -> None:
        """
        Assert that isFunction returns True for a user-defined function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isFunction(_plain_fn))

    def testLambdaReturnsTrue(self) -> None:
        """
        Assert that isFunction returns True for a lambda expression.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isFunction(lambda: None))

    def testBuiltinReturnsFalse(self) -> None:
        """
        Assert that isFunction returns False for a built-in function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isFunction(len))

    def testClassReturnsFalse(self) -> None:
        """
        Assert that isFunction returns False for a class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isFunction(_ConcreteFixture))

    def testAsyncFunctionReturnsTrue(self) -> None:
        """
        Assert that isFunction returns True for an async def function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isFunction(_coroutine_fn))


# ---------------------------------------------------------------------------
# isGenerator / isGeneratorFunction
# ---------------------------------------------------------------------------


class TestIsGenerator(TestCase):
    def testSyncGenObjectReturnsTrue(self) -> None:
        """
        Assert that isGenerator returns True for a sync generator object.

        Returns
        -------
        None
            No return value.
        """
        gen = _sync_gen()
        self.addCleanup(gen.close)
        self.assertTrue(Reflection.isGenerator(gen))

    async def testAsyncGenObjectReturnsFalse(self) -> None:
        """
        Assert that isGenerator returns False for an async generator object.

        Returns
        -------
        None
            No return value.
        """
        gen = _async_gen()
        try:
            self.assertFalse(Reflection.isGenerator(gen))
        finally:
            await gen.aclose()

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isGenerator returns False for a plain function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isGenerator(_plain_fn))


class TestIsGeneratorFunction(TestCase):
    def testSyncGenFunctionReturnsTrue(self) -> None:
        """
        Assert that isGeneratorFunction returns True for a sync gen function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isGeneratorFunction(_sync_gen))

    def testAsyncGenFunctionReturnsFalse(self) -> None:
        """
        Assert that isGeneratorFunction returns False for an async gen function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isGeneratorFunction(_async_gen))

    def testPlainFunctionReturnsFalse(self) -> None:
        """
        Assert that isGeneratorFunction returns False for a plain function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isGeneratorFunction(_plain_fn))


# ---------------------------------------------------------------------------
# isMethod
# ---------------------------------------------------------------------------


class TestIsMethod(TestCase):
    def testBoundMethodReturnsTrue(self) -> None:
        """
        Assert that isMethod returns True for a bound method on an instance.

        Returns
        -------
        None
            No return value.
        """
        obj = _ConcreteFixture()
        # __init__ bound to an instance is a bound method
        self.assertTrue(Reflection.isMethod(obj.__init__))

    def testUnboundFunctionReturnsFalse(self) -> None:
        """
        Assert that isMethod returns False for an unbound class function.

        Returns
        -------
        None
            No return value.
        """
        # Accessing via class gives a plain function in Python 3
        self.assertFalse(Reflection.isMethod(_ConcreteFixture.__init__))

    def testPlainFunctionReturnsFalse(self) -> None:
        """
        Assert that isMethod returns False for a module-level function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isMethod(_plain_fn))


# ---------------------------------------------------------------------------
# isModule
# ---------------------------------------------------------------------------


class TestIsModule(TestCase):
    def testRealModuleReturnsTrue(self) -> None:
        """
        Assert that isModule returns True for the built-in inspect module.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isModule(inspect))

    def testSyntheticModuleReturnsTrue(self) -> None:
        """
        Assert that isModule returns True for a synthetic types.ModuleType.

        Returns
        -------
        None
            No return value.
        """
        mod = types.ModuleType("_test_mod")
        self.assertTrue(Reflection.isModule(mod))

    def testClassReturnsFalse(self) -> None:
        """
        Assert that isModule returns False for a class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isModule(_ConcreteFixture))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isModule returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isModule(None))


# ---------------------------------------------------------------------------
# isRoutine
# ---------------------------------------------------------------------------


class TestIsRoutine(TestCase):
    def testUserFunctionReturnsTrue(self) -> None:
        """
        Assert that isRoutine returns True for a user-defined function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isRoutine(_plain_fn))

    def testBuiltinFunctionReturnsTrue(self) -> None:
        """
        Assert that isRoutine returns True for a built-in function.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isRoutine(len))

    def testBoundMethodReturnsTrue(self) -> None:
        """
        Assert that isRoutine returns True for a bound method.

        Returns
        -------
        None
            No return value.
        """
        obj = _ConcreteFixture()
        self.assertTrue(Reflection.isRoutine(obj.__init__))

    def testClassReturnsFalse(self) -> None:
        """
        Assert that isRoutine returns False for a class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isRoutine(_ConcreteFixture))

    def testIntReturnsFalse(self) -> None:
        """
        Assert that isRoutine returns False for an integer.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isRoutine(42))


# ---------------------------------------------------------------------------
# isGeneric
# ---------------------------------------------------------------------------


class TestIsGeneric(TestCase):
    def testListIntReturnsTrue(self) -> None:
        """
        Assert that isGeneric returns True for list[int] generic alias.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isGeneric(list[int]))

    def testDictStrIntReturnsTrue(self) -> None:
        """
        Assert that isGeneric returns True for dict[str, int] generic alias.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isGeneric(dict[str, int]))

    def testTypeVarReturnsTrue(self) -> None:
        """
        Assert that isGeneric returns True for a TypeVar.

        Returns
        -------
        None
            No return value.
        """
        T = typing.TypeVar("T")
        self.assertTrue(Reflection.isGeneric(T))

    def testLegacyOriginAttributeReturnsTrue(self) -> None:
        """
        Assert that a bare typing construct exposing __origin__ is generic.

        Returns
        -------
        None
            No return value.

        Notes
        -----
        ``typing.get_origin(typing.Union)`` is None, so the fallback branch
        based on the ``__origin__`` attribute is the one that answers here.
        """
        self.assertIsNone(typing.get_origin(typing.Union))
        self.assertTrue(Reflection.isGeneric(typing.Union))

    def testCustomOriginAttributeReturnsTrue(self) -> None:
        """
        Assert that user classes declaring __origin__ are treated as generic.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isGeneric(_OriginFixture))

    def testConcreteClassReturnsFalse(self) -> None:
        """
        Assert that isGeneric returns False for a plain concrete class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isGeneric(_ConcreteFixture))

    def testIntReturnsFalse(self) -> None:
        """
        Assert that isGeneric returns False for the plain int type.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isGeneric(int))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isGeneric returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isGeneric(None))


# ---------------------------------------------------------------------------
# isProtocol
# ---------------------------------------------------------------------------


class TestIsProtocol(TestCase):
    def testProtocolSubclassReturnsTrue(self) -> None:
        """
        Assert that isProtocol returns True for a user-defined Protocol.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isProtocol(_ProtocolFixture))

    def testConcreteClassReturnsFalse(self) -> None:
        """
        Assert that isProtocol returns False for a concrete class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isProtocol(_ConcreteFixture))

    def testProtocolItselfReturnsFalse(self) -> None:
        """
        Assert that isProtocol returns False for typing.Protocol itself.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isProtocol(typing.Protocol))

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isProtocol returns False for a function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isProtocol(_plain_fn))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isProtocol returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isProtocol(None))


# ---------------------------------------------------------------------------
# isInstance
# ---------------------------------------------------------------------------


class TestIsInstance(TestCase):
    def testUserDefinedInstanceReturnsTrue(self) -> None:
        """
        Assert that isInstance returns True for an instance of a user class.

        Returns
        -------
        None
            No return value.
        """
        obj = _ConcreteFixture(5)
        self.assertTrue(Reflection.isInstance(obj))

    def testClassReturnsFalse(self) -> None:
        """
        Assert that isInstance returns False for a class object itself.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isInstance(_ConcreteFixture))

    def testBuiltinStringReturnsFalse(self) -> None:
        """
        Assert that isInstance returns False for a built-in string instance.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isInstance("hello"))

    def testIntValueReturnsFalse(self) -> None:
        """
        Assert that isInstance returns False for an integer value.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isInstance(42))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isInstance returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isInstance(None))


# ---------------------------------------------------------------------------
# isTypingConstruct
# ---------------------------------------------------------------------------


class TestIsTypingConstruct(TestCase):
    def testAnyReturnsTrue(self) -> None:
        """Recognize the public typing construct."""
        self.assertTrue(Reflection.isTypingConstruct(typing.Any))

    def testTypeVarReturnsTrue(self) -> None:
        """
        Assert that isTypingConstruct returns True for a TypeVar instance.

        Returns
        -------
        None
            No return value.
        """
        T = typing.TypeVar("T")
        self.assertTrue(Reflection.isTypingConstruct(T))

    def testLiteralReturnsTrue(self) -> None:
        """Recognize the public typing construct."""
        self.assertTrue(Reflection.isTypingConstruct(typing.Literal[1]))

    def testConcreteClassReturnsFalse(self) -> None:
        """
        Assert that isTypingConstruct returns False for a concrete class.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isTypingConstruct(_ConcreteFixture))

    def testIntReturnsFalse(self) -> None:
        """
        Assert that isTypingConstruct returns False for the plain int type.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isTypingConstruct(int))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isTypingConstruct returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isTypingConstruct(None))


# ---------------------------------------------------------------------------
# isTraceback
# ---------------------------------------------------------------------------


class TestIsTraceback(TestCase):
    def testRealTracebackReturnsTrue(self) -> None:
        """Assert that isTraceback returns True for a live traceback object.

        Returns
        -------
        None
            No return value.

        """
        try:
            _err_msg = "fixture"
            raise RuntimeError(_err_msg)
        except RuntimeError:
            tb = sys.exc_info()[2]
        self.assertTrue(Reflection.isTraceback(tb))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isTraceback returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isTraceback(None))

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isTraceback returns False for a function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isTraceback(_plain_fn))


# ---------------------------------------------------------------------------
# isFrame
# ---------------------------------------------------------------------------


class TestIsFrame(TestCase):
    def testLiveFrameReturnsTrue(self) -> None:
        """
        Assert that isFrame returns True for a live frame object.

        Returns
        -------
        None
            No return value.
        """
        frame = inspect.currentframe()
        try:
            self.assertTrue(Reflection.isFrame(frame))
        finally:
            del frame

    def testFunctionReturnsFalse(self) -> None:
        """
        Assert that isFrame returns False for a plain function.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isFrame(_plain_fn))

    def testNoneReturnsFalse(self) -> None:
        """
        Assert that isFrame returns False for None.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isFrame(None))


# ---------------------------------------------------------------------------
# isGetSetDescriptor
# ---------------------------------------------------------------------------


class TestIsGetSetDescriptor(TestCase):
    def testFunctionDunderDictReturnsTrue(self) -> None:
        """
        Assert that a getset descriptor is recognised.

        Returns
        -------
        None
            No return value.

        Notes
        -----
        ``function.__dict__`` is implemented as a getset descriptor by CPython.
        """
        descriptor = types.FunctionType.__dict__["__dict__"]
        self.assertTrue(Reflection.isGetSetDescriptor(descriptor))

    def testPlainPropertyReturnsFalse(self) -> None:
        """
        Assert that a pure-Python property is not a getset descriptor.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isGetSetDescriptor(_DescriptorFixture.value))


# ---------------------------------------------------------------------------
# isMemberDescriptor
# ---------------------------------------------------------------------------


class TestIsMemberDescriptor(TestCase):
    def testSlotEntryReturnsTrue(self) -> None:
        """
        Assert that a slot descriptor is recognised as a member descriptor.

        Returns
        -------
        None
            No return value.
        """
        descriptor = _SlottedFixture.__dict__["slot_attr"]
        self.assertTrue(Reflection.isMemberDescriptor(descriptor))

    def testPlainPropertyReturnsFalse(self) -> None:
        """
        Assert that a pure-Python property is not a member descriptor.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isMemberDescriptor(_DescriptorFixture.value))


# ---------------------------------------------------------------------------
# isMethodDescriptor
# ---------------------------------------------------------------------------


class TestIsMethodDescriptor(TestCase):
    def testBuiltinMethodDescriptorReturnsTrue(self) -> None:
        """
        Assert that an unbound C method is recognised as a method descriptor.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(Reflection.isMethodDescriptor(str.upper))

    def testPlainFunctionReturnsFalse(self) -> None:
        """
        Assert that a Python function is not a method descriptor.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(Reflection.isMethodDescriptor(_plain_fn))
