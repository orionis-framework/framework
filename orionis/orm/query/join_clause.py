from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.orm.query.expressions import JoinCondition

if TYPE_CHECKING:
    from typing import Self

class JoinClause:
    """
    Accumulator of ON conditions for a join declared with a callback.

    Handed to the callback form of the join helpers so several ON
    conditions can be combined, mirroring the fluent join syntax of
    query builders.
    """

    __slots__ = ("_conditions",)

    def __init__(self) -> None:
        """
        Initialize an empty set of ON conditions.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._conditions: list[JoinCondition] = []

    def on(self, first: str, operator: str, second: str) -> Self:
        """
        Add an AND-combined column comparison to the ON clause.

        Parameters
        ----------
        first : str
            Left-hand column reference, optionally qualified.
        operator : str
            Comparison operator relating both sides.
        second : str
            Right-hand column reference, optionally qualified.

        Returns
        -------
        JoinClause
            The same clause, enabling fluent chaining.
        """
        self._conditions.append(
            JoinCondition(first=first, operator=operator, second=second),
        )
        return self

    def orOn(self, first: str, operator: str, second: str) -> Self:
        """
        Add an OR-combined column comparison to the ON clause.

        Parameters
        ----------
        first : str
            Left-hand column reference, optionally qualified.
        operator : str
            Comparison operator relating both sides.
        second : str
            Right-hand column reference, optionally qualified.

        Returns
        -------
        JoinClause
            The same clause, enabling fluent chaining.
        """
        self._conditions.append(
            JoinCondition(
                first=first, operator=operator, second=second, boolean="or",
            ),
        )
        return self

    def conditions(self) -> list[JoinCondition]:
        """
        Return the ON conditions collected so far.

        Returns
        -------
        list of JoinCondition
            Conditions in declaration order.
        """
        return self._conditions
