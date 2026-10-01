from annotationlib import Format
from inspect import signature
from orionis.orm.contracts.base_builder import IQueryBuilderBase
from orionis.orm.query.base_builder import QueryBuilderBase
from orionis.test import TestCase

BASE_METHODS = frozenset(
    [
        "toPlan",
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
        Verify interface inheritance, method names, and parameter kinds.
    """
    test_case.assertEqual(contract.__abstractmethods__, expected_methods)
    if nominal:
        test_case.assertTrue(issubclass(implementation, contract))
    test_case.assertFalse(getattr(implementation, "__abstractmethods__", ()))
    for name in sorted(expected_methods):
        abstract = signature(
            getattr(contract, name),
            annotation_format=Format.FORWARDREF,
        )
        concrete = signature(
            getattr(implementation, name),
            annotation_format=Format.FORWARDREF,
        )
        abstract_parameters = [
            (item.name, item.kind) for item in abstract.parameters.values()
        ]
        concrete_parameters = [
            (item.name, item.kind) for item in concrete.parameters.values()
        ]
        test_case.assertEqual(abstract_parameters, concrete_parameters, name)

class TestQueryBuilderBaseContract(TestCase):
    """Verify the shared query language contract and concrete implementation."""

    def testSurfaceMatchesTheSharedQueryImplementation(self) -> None:
        """Match all shared query methods and their parameter signatures.

        Returns
        -------
        None
            Verify the complete base query language contract.
        """
        assert_contract_surface(
            self,
            IQueryBuilderBase,
            QueryBuilderBase,
            BASE_METHODS,
            nominal=False,
        )

    def testContractDeclaresEmptySlots(self) -> None:
        """Prevent the abstract base from introducing an instance dictionary.

        Returns
        -------
        None
            Verify the interface declares its own empty slots.
        """
        self.assertEqual(IQueryBuilderBase.__dict__.get("__slots__"), ())
