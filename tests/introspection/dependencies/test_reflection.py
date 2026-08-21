from orionis.test import TestCase
from orionis.introspection.dependencies.reflection import (
    ReflectDependencies,
)
from orionis.introspection.dependencies.entities.signature import (
    Signature,
)

# ---------------------------------------------------------------------------
# Target fixtures used across multiple test classes
# ---------------------------------------------------------------------------

class _NoArgs:
    """Class with a no-argument constructor (only self)."""

    def __init__(self) -> None:
        pass

class _AllResolved:
    """Class whose constructor uses only type-annotated, non-builtin params."""

    def __init__(self, dep: _AllResolved) -> None:
        self.dep = dep

class _WithDefault:
    """Class whose constructor has a parameter with a default value."""

    def __init__(self, value: int = 10) -> None:
        self.value = value

class _WithBuiltin:
    """Class whose constructor has a bare builtin-typed parameter."""

    def __init__(self, name: str) -> None:
        self.name = name

class _Unannotated:
    """Class whose constructor has a completely unannotated parameter."""

    def __init__(self, x) -> None:
        self.x = x

class _Mixed:
    """Class with a mix of annotated and default-valued constructor params."""

    def __init__(
        self,
        dep: _Mixed,
        name: str,
        count: int = 0,
    ) -> None:
        self.dep = dep
        self.name = name
        self.count = count

    def process(self, value: int, mode: str = "fast") -> str:
        """
        Return a string combining value and mode.

        Parameters
        ----------
        value : int
            Numeric value to process.
        mode : str, optional
            Processing mode, by default 'fast'.

        Returns
        -------
        str
            Formatted result string.
        """
        return f"{value}-{mode}"

class _KeywordOnly:
    """Class whose constructor has keyword-only parameters."""

    def __init__(self, *, label: str, count: int = 0) -> None:
        self.label = label
        self.count = count

class _ForwardRef:
    """Class whose constructor annotates a parameter with a string literal."""

    def __init__(self, dep: "UnknownDependency") -> None:  # noqa: F821, UP037
        self.dep = dep


def _plain_function(a: int, b: str = "hello") -> str:
    """
    Return a concatenation of a and b.

    Parameters
    ----------
    a : int
        Integer operand.
    b : str, optional
        String operand, by default 'hello'.

    Returns
    -------
    str
        String combining both arguments.
    """
    return f"{a}-{b}"

async def _async_function(x: int) -> int: # NOSONAR
    """
    Return x unchanged (async fixture).

    Parameters
    ----------
    x : int
        Input value.

    Returns
    -------
    int
        Same value as x.
    """
    return x

# ---------------------------------------------------------------------------
# ReflectDependencies — constructor
# ---------------------------------------------------------------------------

class TestReflectDependenciesInit(TestCase):

    def testInitWithNoneTarget(self) -> None:
        """
        Assert that ReflectDependencies accepts None as a valid target.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rd = ReflectDependencies(None)
        self.assertIsInstance(rd, ReflectDependencies)

    def testInitWithClassTarget(self) -> None:
        """
        Assert that ReflectDependencies accepts a class as its target.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rd = ReflectDependencies(_Mixed)
        self.assertIsInstance(rd, ReflectDependencies)

    def testInitWithCallableTarget(self) -> None:
        """
        Assert that ReflectDependencies accepts a plain function as target.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rd = ReflectDependencies(_plain_function)
        self.assertIsInstance(rd, ReflectDependencies)

    def testInitWithNoArgs(self) -> None:
        """
        Assert that ReflectDependencies can be instantiated without arguments.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        rd = ReflectDependencies()
        self.assertIsInstance(rd, ReflectDependencies)

# ---------------------------------------------------------------------------
# constructorSignature
# ---------------------------------------------------------------------------

class TestConstructorSignatureNoArgs(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _NoArgs.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_NoArgs)

    def testReturnsSignature(self) -> None:
        """
        Assert that constructorSignature returns a Signature instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rd.constructorSignature(), Signature)

    def testOrderedIsEmpty(self) -> None:
        """
        Assert that ordered is empty when constructor has no parameters.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertEqual(sig.ordered, {})

    def testNoArgumentsRequiredIsTrue(self) -> None:
        """
        Assert that noArgumentsRequired returns True for a no-arg constructor.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertTrue(sig.noArgumentsRequired())

    def testHasUnresolvedArgumentsIsFalse(self) -> None:
        """
        Assert that hasUnresolvedArguments is False for a no-arg constructor.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertFalse(sig.hasUnresolvedArguments())

class TestConstructorSignatureWithDefault(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _WithDefault.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_WithDefault)

    def testValueIsInResolved(self) -> None:
        """
        Assert that the 'value' parameter appears in resolved dependencies.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertIn("value", sig.resolved)

    def testValueIsInOrdered(self) -> None:
        """
        Assert that the 'value' parameter appears in ordered dependencies.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertIn("value", sig.ordered)

    def testValueIsNotInUnresolved(self) -> None:
        """
        Assert that the 'value' parameter is absent from unresolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertNotIn("value", sig.unresolved)

    def testArgumentHasCorrectDefault(self) -> None:
        """
        Assert that the Argument for 'value' stores 10 as its default.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertEqual(sig.resolved["value"].default, 10)

    def testArgumentIsResolvedTrue(self) -> None:
        """
        Assert that the Argument for 'value' has resolved set to True.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertTrue(sig.resolved["value"].resolved)

class TestConstructorSignatureWithBuiltin(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _WithBuiltin.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_WithBuiltin)

    def testNameIsInUnresolved(self) -> None:
        """
        Assert that a builtin-typed parameter ends up in unresolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertIn("name", sig.unresolved)

    def testNameIsNotInResolved(self) -> None:
        """
        Assert that a builtin-typed parameter is absent from resolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertNotIn("name", sig.resolved)

    def testArgumentIsResolvedFalse(self) -> None:
        """
        Assert that the Argument for 'name' has resolved set to False.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertFalse(sig.unresolved["name"].resolved)

    def testArgumentClassNameIsStr(self) -> None:
        """
        Assert that the Argument for 'name' records 'str' as class_name.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertEqual(sig.unresolved["name"].class_name, "str")

class TestConstructorSignatureUnannotated(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _Unannotated.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_Unannotated)

    def testXIsInUnresolved(self) -> None:
        """
        Assert that an unannotated parameter appears in unresolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertIn("x", sig.unresolved)

    def testXIsNotInResolved(self) -> None:
        """
        Assert that an unannotated parameter is absent from resolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertNotIn("x", sig.resolved)

    def testArgumentResolvedIsFalse(self) -> None:
        """
        Assert that the Argument for 'x' has resolved set to False.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertFalse(sig.unresolved["x"].resolved)

class TestConstructorSignatureMixed(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _Mixed.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_Mixed)

    def testDepIsInResolved(self) -> None:
        """
        Assert that the non-builtin annotated 'dep' param is in resolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertIn("dep", sig.resolved)

    def testNameIsInUnresolved(self) -> None:
        """
        Assert that the builtin-typed 'name' param is in unresolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertIn("name", sig.unresolved)

    def testCountIsInResolved(self) -> None:
        """
        Assert that the default-valued 'count' param is in resolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertIn("count", sig.resolved)

    def testOrderedHasThreeKeys(self) -> None:
        """
        Assert that ordered contains exactly three entries for _Mixed.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertEqual(len(sig.ordered), 3)

# ---------------------------------------------------------------------------
# methodSignature
# ---------------------------------------------------------------------------

class TestMethodSignature(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _Mixed.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_Mixed)

    def testReturnsSignature(self) -> None:
        """
        Assert that methodSignature returns a Signature instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rd.methodSignature("process"), Signature)

    def testValueIsInUnresolved(self) -> None:
        """
        Assert that 'value' (builtin int) appears in unresolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.methodSignature("process")
        self.assertIn("value", sig.unresolved)

    def testModeIsInResolved(self) -> None:
        """
        Assert that 'mode' (default-valued) appears in resolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.methodSignature("process")
        self.assertIn("mode", sig.resolved)

    def testOrderedHasTwoKeys(self) -> None:
        """
        Assert that ordered contains exactly two entries for process().

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.methodSignature("process")
        self.assertEqual(len(sig.ordered), 2)

    def testModeDefaultIsHello(self) -> None:
        """
        Assert that the Argument for 'mode' stores 'fast' as its default.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.methodSignature("process")
        self.assertEqual(sig.resolved["mode"].default, "fast")

    def testMissingMethodRaisesAttributeError(self) -> None:
        """
        Assert that requesting a non-existent method raises AttributeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(AttributeError):
            self.rd.methodSignature("non_existent_method_xyz")

# ---------------------------------------------------------------------------
# callableSignature
# ---------------------------------------------------------------------------

class TestCallableSignaturePlainFunction(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _plain_function.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_plain_function)

    def testReturnsSignature(self) -> None:
        """
        Assert that callableSignature returns a Signature instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rd.callableSignature(), Signature)

    def testAIsInUnresolved(self) -> None:
        """
        Assert that 'a' (builtin int, no default) appears in unresolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.callableSignature()
        self.assertIn("a", sig.unresolved)

    def testBIsInResolved(self) -> None:
        """
        Assert that 'b' (default value) appears in resolved.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.callableSignature()
        self.assertIn("b", sig.resolved)

    def testOrderedHasTwoKeys(self) -> None:
        """
        Assert that ordered contains exactly two entries.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.callableSignature()
        self.assertEqual(len(sig.ordered), 2)

    def testBDefaultIsHello(self) -> None:
        """
        Assert that the Argument for 'b' stores 'hello' as its default.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.callableSignature()
        self.assertEqual(sig.resolved["b"].default, "hello")

class TestCallableSignatureAsyncFunction(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _async_function.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_async_function)

    def testReturnsSignature(self) -> None:
        """
        Assert that callableSignature on an async function returns Signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.rd.callableSignature(), Signature)

    def testXIsInUnresolved(self) -> None:
        """
        Assert that 'x' (builtin int) appears in unresolved for async fn.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.callableSignature()
        self.assertIn("x", sig.unresolved)

class TestCallableSignatureNonCallable(TestCase):

    def testNonCallableRaisesTypeError(self) -> None:
        """
        Assert that calling callableSignature on a non-callable raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        # A plain integer is not callable; signature inspection must fail
        rd = ReflectDependencies(42)
        with self.assertRaises(TypeError):
            rd.callableSignature()

    def testUninspectableCallableRaisesValueError(self) -> None:
        """
        Assert that builtins without a signature surface a ValueError.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        ``inspect.signature(min)`` raises because the builtin exposes no
        text signature.
        """
        rd = ReflectDependencies(min)
        with self.assertRaises(ValueError):
            rd.callableSignature()

# ---------------------------------------------------------------------------
# Forward-referenced (string) annotations
# ---------------------------------------------------------------------------

class TestForwardReferencedAnnotations(TestCase):

    def setUp(self) -> None:
        """
        Instantiate a ReflectDependencies over the forward-reference fixture.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.rd = ReflectDependencies(_ForwardRef)

    def testForwardReferenceIsResolvedAsString(self) -> None:
        """
        Assert that string annotations fall back to the typing module.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        argument = self.rd.constructorSignature().ordered["dep"]
        self.assertEqual(argument.module_name, "typing")
        self.assertEqual(argument.class_name, "UnknownDependency")
        self.assertIs(argument.type, str)

    def testForwardReferenceIsMarkedResolvedButNotSchema(self) -> None:
        """
        Assert that forward references never qualify as msgspec schemas.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        argument = self.rd.constructorSignature().ordered["dep"]
        self.assertTrue(argument.resolved)
        self.assertFalse(argument.is_schema)

# ---------------------------------------------------------------------------
# Keyword-only parameters
# ---------------------------------------------------------------------------

class TestKeywordOnlyParameters(TestCase):

    def setUp(self) -> None:
        """
        Prepare a ReflectDependencies instance wrapping _KeywordOnly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.rd = ReflectDependencies(_KeywordOnly)

    def testLabelIsKeywordOnly(self) -> None:
        """
        Assert that 'label' is marked is_keyword_only in the Argument.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertTrue(sig.unresolved["label"].is_keyword_only)

    def testCountIsKeywordOnly(self) -> None:
        """
        Assert that 'count' (with default) is marked is_keyword_only.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertTrue(sig.resolved["count"].is_keyword_only)

    def testGetKeywordOnlyContainsLabel(self) -> None:
        """
        Assert that getKeywordOnly returns 'label' from the signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertIn("label", sig.getKeywordOnly())

    def testGetPositionalOnlyIsEmpty(self) -> None:
        """
        Assert that getPositionalOnly is empty for an all-keyword-only class.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = self.rd.constructorSignature()
        self.assertEqual(sig.getPositionalOnly(), {})
