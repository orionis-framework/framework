from __future__ import annotations
from dataclasses import FrozenInstanceError
from orionis.introspection.dependencies.entities.argument import Argument
from orionis.introspection.dependencies.entities.signature import Signature
from orionis.test import TestCase

def _make_argument(name: str = "dep", *, resolved: bool = True) -> Argument:
    """Create a minimal resolved Argument."""
    return Argument(
        name=name,
        resolved=resolved,
        module_name="orionis.services.cache",
        class_name="FileBasedCache",
        type=object,
        full_class_path="orionis.services.cache.FileBasedCache",
    )

def _make_signature(
    resolved: dict | None = None,
    unresolved: dict | None = None,
    ordered: dict | None = None,
) -> Signature:
    """Create a Signature instance with sensible defaults."""
    return Signature(
        resolved=resolved if resolved is not None else {},
        unresolved=unresolved if unresolved is not None else {},
        ordered=ordered if ordered is not None else {},
    )

def _make_typed_argument(
    name: str,
    *,
    resolved: bool = True,
    is_keyword_only: bool = False,
    default: object = None,
) -> Argument:
    """
    Create a minimal Argument annotated as a builtin integer.

    Parameters
    ----------
    name : str
        Argument name.
    resolved : bool, optional
        Whether the argument is resolved, by default True.
    is_keyword_only : bool, optional
        Whether the argument is keyword-only, by default False.
    default : object, optional
        Default value, by default None.

    Returns
    -------
    Argument
        Constructed Argument instance.
    """
    return Argument(
        name=name,
        resolved=resolved,
        module_name="builtins",
        class_name="int",
        type=int,
        full_class_path="builtins.int",
        is_keyword_only=is_keyword_only,
        default=default,
    )

# ===========================================================================
# TestSignature
# ===========================================================================

class TestSignature(TestCase):

    def testCanBeInstantiatedWithEmptyDicts(self) -> None:
        """
        Assert that Signature can be created with empty dicts.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = _make_signature()
        self.assertIsInstance(sig, Signature)

    def testResolvedFieldIsPersisted(self) -> None:
        """
        Assert that the resolved dict is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument()
        sig = _make_signature(resolved={"dep": arg})
        self.assertIn("dep", sig.resolved)

    def testUnresolvedFieldIsPersisted(self) -> None:
        """
        Assert that the unresolved dict is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument("missing", resolved=False)
        sig = _make_signature(unresolved={"missing": arg})
        self.assertIn("missing", sig.unresolved)

    def testOrderedFieldIsPersisted(self) -> None:
        """
        Assert that the ordered dict is stored correctly.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument("a")
        sig = _make_signature(ordered={"a": arg})
        self.assertIn("a", sig.ordered)

    def testIsFrozenDataclass(self) -> None:
        """
        Assert that Signature raises FrozenInstanceError on mutation.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = _make_signature()
        with self.assertRaises(FrozenInstanceError):
            sig.ordered = {}  # type: ignore[misc]

    def testNoArgumentsRequiredWhenOrderedIsEmpty(self) -> None:
        """
        Assert that noArgumentsRequired returns True when ordered is empty.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = _make_signature()
        self.assertTrue(sig.noArgumentsRequired())

    def testNoArgumentsRequiredReturnsFalseWhenOrderedHasItems(self) -> None:
        """
        Assert that noArgumentsRequired returns False when ordered has items.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument()
        sig = _make_signature(ordered={"dep": arg})
        self.assertFalse(sig.noArgumentsRequired())

    def testArgumentsReturnsOrderedItems(self) -> None:
        """
        Assert that arguments() returns items from ordered dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument("svc")
        sig = _make_signature(ordered={"svc": arg})
        items = list(sig.arguments())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0], "svc")

    def testHasUnresolvedArgumentsReturnsFalseWhenEmpty(self) -> None:
        """
        Assert that hasUnresolvedArguments returns False when unresolved is empty.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig = _make_signature()
        self.assertFalse(sig.hasUnresolvedArguments())

    def testHasUnresolvedArgumentsReturnsTrueWhenPresent(self) -> None:
        """
        Assert that hasUnresolvedArguments returns True when unresolved has items.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument("x", resolved=False)
        sig = _make_signature(unresolved={"x": arg})
        self.assertTrue(sig.hasUnresolvedArguments())

    def testToDictReturnsDict(self) -> None:
        """
        Assert that toDict converts ordered arguments to a plain dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument("svc")
        sig = _make_signature(ordered={"svc": arg})
        result = sig.toDict()
        self.assertIsInstance(result, dict)
        self.assertIn("svc", result)

    def testGetAllOrderedReturnsSameAsOrdered(self) -> None:
        """
        Assert that getAllOrdered returns the ordered dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument("svc")
        ordered = {"svc": arg}
        sig = _make_signature(ordered=ordered)
        self.assertEqual(sig.getAllOrdered(), ordered)

    def testArgumentsReturnsIterableOfTuples(self) -> None:
        """
        Assert that arguments() returns name-argument pairs from ordered.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        arg = _make_argument("x")
        sig = _make_signature(ordered={"x": arg})
        pairs = list(sig.arguments())
        self.assertEqual(pairs[0][0], "x")
        self.assertIs(pairs[0][1], arg)

    def testEqualityBetweenIdenticalSignatures(self) -> None:
        """
        Assert that two Signature instances with equal fields compare equal.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        sig1 = _make_signature()
        sig2 = _make_signature()
        self.assertEqual(sig1, sig2)

# ===========================================================================
# TestSignatureAccessors
# ===========================================================================

class TestSignatureAccessors(TestCase):

    def setUp(self) -> None:
        """
        Build a Signature holding resolved, unresolved and keyword arguments.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.res_arg = _make_typed_argument("res", default=1)
        self.unres_arg = _make_typed_argument("unres", resolved=False, default=0)
        self.kw_arg = _make_typed_argument("kw", is_keyword_only=True, default=2)
        self.sig = _make_signature(
            resolved={"res": self.res_arg, "kw": self.kw_arg},
            unresolved={"unres": self.unres_arg},
            ordered={
                "res": self.res_arg,
                "unres": self.unres_arg,
                "kw": self.kw_arg,
            },
        )

    def testGetResolvedReturnsOnlyResolvedArguments(self) -> None:
        """
        Assert that getResolved exposes the resolved bucket only.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        resolved = self.sig.getResolved()
        self.assertIn("res", resolved)
        self.assertNotIn("unres", resolved)

    def testGetUnresolvedReturnsOnlyUnresolvedArguments(self) -> None:
        """
        Assert that getUnresolved exposes the unresolved bucket only.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        unresolved = self.sig.getUnresolved()
        self.assertIn("unres", unresolved)
        self.assertNotIn("res", unresolved)

    def testGetAllOrderedReturnsEveryArgument(self) -> None:
        """
        Assert that getAllOrdered returns every declared argument.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertEqual(len(self.sig.getAllOrdered()), 3)

    def testResolvedToDictReturnsPlainDict(self) -> None:
        """
        Assert that resolvedToDict copies the resolved bucket.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        result = self.sig.resolvedToDict()
        self.assertIsInstance(result, dict)
        self.assertIn("res", result)

    def testUnresolvedToDictReturnsPlainDict(self) -> None:
        """
        Assert that unresolvedToDict copies the unresolved bucket.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        result = self.sig.unresolvedToDict()
        self.assertIsInstance(result, dict)
        self.assertIn("unres", result)

    def testGetPositionalOnlyExcludesKeywordArguments(self) -> None:
        """
        Assert that getPositionalOnly drops keyword-only arguments.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        positional = self.sig.getPositionalOnly()
        self.assertIn("res", positional)
        self.assertNotIn("kw", positional)

    def testGetKeywordOnlyKeepsKeywordArgumentsOnly(self) -> None:
        """
        Assert that getKeywordOnly keeps keyword-only arguments only.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        keyword = self.sig.getKeywordOnly()
        self.assertIn("kw", keyword)
        self.assertNotIn("res", keyword)

# ===========================================================================
# TestSignatureValidation
# ===========================================================================

class TestSignatureValidation(TestCase):

    def testResolvedMustBeADict(self) -> None:
        """
        Assert that a non-dict resolved bucket raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            Signature(
                resolved="bad",  # type: ignore[arg-type]
                unresolved={},
                ordered={},
            )

    def testUnresolvedMustBeADict(self) -> None:
        """
        Assert that a non-dict unresolved bucket raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            Signature(
                resolved={},
                unresolved="bad",  # type: ignore[arg-type]
                ordered={},
            )

    def testOrderedMustBeADict(self) -> None:
        """
        Assert that a non-dict ordered bucket raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            Signature(
                resolved={},
                unresolved={},
                ordered="bad",  # type: ignore[arg-type]
            )
