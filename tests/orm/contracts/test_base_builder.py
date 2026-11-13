# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from typing import Any, TypeVar, get_args, get_origin
from inspect import Signature, signature
from orionis.orm.contracts.base_builder import IQueryBuilderBase
from orionis.orm.query.base_builder import QueryBuilderBase
from orionis.test import TestCase

BASE_METHODS = frozenset(
    [
        "toPlan",
        "toSql",
        "clone",
        "select",
        "addSelect",
        "selectRaw",
        "selectSub",
        "distinct",
        "where",
        "orWhere",
        "whereIn",
        "orWhereIn",
        "whereNotIn",
        "orWhereNotIn",
        "whereNull",
        "orWhereNull",
        "whereNotNull",
        "orWhereNotNull",
        "whereBetween",
        "whereNotBetween",
        "whereLike",
        "whereNotLike",
        "whereILike",
        "whereNotILike",
        "whereStartsWith",
        "whereEndsWith",
        "whereContains",
        "whereRegexpMatch",
        "whereColumn",
        "orWhereColumn",
        "whereRaw",
        "orWhereRaw",
        "whereExists",
        "orWhereExists",
        "whereNotExists",
        "orWhereNotExists",
        "join",
        "leftJoin",
        "rightJoin",
        "fullJoin",
        "crossJoin",
        "joinSub",
        "leftJoinSub",
        "rightJoinSub",
        "orderBy",
        "latest",
        "oldest",
        "groupBy",
        "having",
        "orHaving",
        "havingRaw",
        "limit",
        "offset",
        "take",
        "skip",
        "forPage",
        "lockForUpdate",
        "sharedLock",
        "union",
        "unionAll",
        "count",
        "exists",
        "doesntExist",
        "max",
        "min",
        "avg",
        "sum",
        "insert",
        "update",
        "delete",
    ],
)


def _annotation_shape(annotation: object) -> object:
    """Resolve generic model bounds while preserving container annotations.

    Parameters
    ----------
    annotation : object
        Annotation obtained from an evaluated public signature.

    Returns
    -------
    object
        Comparable annotation with type variables replaced by their bounds.
    """
    if isinstance(annotation, TypeVar):
        return _annotation_shape(annotation.__bound__)
    origin = get_origin(annotation)
    if origin is not None:
        return origin, tuple(_annotation_shape(arg) for arg in get_args(annotation))
    return annotation


def _return_annotation_matches(abstract: object, concrete: object) -> bool:
    """Accept equal return types or a nominal subtype of an unparameterized class.

    Parameters
    ----------
    abstract : object
        Evaluated return annotation declared by the interface.
    concrete : object
        Evaluated return annotation declared by its implementation.

    Returns
    -------
    bool
        Whether the concrete return preserves the interface guarantee.
    """
    if abstract is Signature.empty or concrete is Signature.empty:
        return False
    expected = _annotation_shape(abstract)
    actual = _annotation_shape(concrete)
    if expected == actual:
        return True
    if expected is Any or not isinstance(expected, type):
        return False
    candidate = actual[0] if isinstance(actual, tuple) else actual
    return (
        candidate is not Any
        and isinstance(candidate, type)
        and issubclass(candidate, expected)
    )


def assert_contract_surface(
    test_case: TestCase,
    contract: type,
    implementation: type,
    expected_methods: frozenset[str],
    *,
    nominal: bool = True,
) -> None:
    """Verify the declared abstract API and its concrete parameter signatures.

    Parameters
    ----------
    test_case : TestCase
        Test case owning the assertions.
    contract : type
        Abstract interface to inspect.
    implementation : type
        Framework class implementing that interface.
    expected_methods : frozenset of str
        Complete public abstract surface, including inherited methods.
    nominal : bool, optional
        Whether implementation inherits the contract rather than providing
        the shared methods structurally.

    Returns
    -------
    None
        No return value.
    """
    test_case.assertEqual(contract.__abstractmethods__, expected_methods)
    if nominal:
        test_case.assertTrue(issubclass(implementation, contract))
    test_case.assertFalse(getattr(implementation, "__abstractmethods__", ()))
    for name in sorted(expected_methods):
        abstract = signature(
            getattr(contract, name),
            eval_str=True,
        )
        concrete = signature(
            getattr(implementation, name),
            eval_str=True,
        )
        abstract_parameters = [
            (item.name, item.kind, item.default, _annotation_shape(item.annotation))
            for item in abstract.parameters.values()
            if item.name != "self"
        ]
        concrete_parameters = [
            (item.name, item.kind, item.default, _annotation_shape(item.annotation))
            for item in concrete.parameters.values()
            if item.name != "self"
        ]
        test_case.assertEqual(abstract_parameters, concrete_parameters, name)
        test_case.assertTrue(
            _return_annotation_matches(
                abstract.return_annotation,
                concrete.return_annotation,
            ),
            f"{name}: incompatible return annotations: "
            f"{abstract.return_annotation!r} and {concrete.return_annotation!r}",
        )


class TestQueryBuilderBaseContract(TestCase):
    """Verify the shared query language contract and concrete implementation."""

    def testSurfaceMatchesTheSharedQueryImplementation(self) -> None:
        """Match all shared query methods and their parameter signatures.

        Returns
        -------
        None
            No return value.
        """
        assert_contract_surface(
            self,
            IQueryBuilderBase,
            QueryBuilderBase,
            BASE_METHODS,
            nominal=False,
        )

    def testReturnCovarianceDoesNotAcceptWeakerContracts(self) -> None:
        """Allow nominal narrowing while rejecting wider and unequal generic returns.

        Returns
        -------
        None
            No return value.
        """

        class Parent:
            """Represent an interface's nominal result type."""

        class Child(Parent):
            """Represent a valid narrower implementation result."""

        self.assertTrue(_return_annotation_matches(Parent, Child))
        self.assertTrue(_return_annotation_matches(list[Parent], list[Parent]))
        for abstract, concrete in (
            (Child, Parent),
            (Parent, str),
            (Parent, Any),
            (Any, Parent),
            (object, Signature.empty),
            (Signature.empty, object),
            (list[Parent], list[Child]),
            (list[Parent], tuple[Parent]),
        ):
            with self.subTest(abstract=abstract, concrete=concrete):
                self.assertFalse(_return_annotation_matches(abstract, concrete))

    def testContractDeclaresEmptySlots(self) -> None:
        """Prevent the abstract base from introducing an instance dictionary.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(IQueryBuilderBase.__dict__.get("__slots__"), ())
