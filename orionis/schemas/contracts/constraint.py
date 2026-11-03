"""Define the contract for rule implementations."""

from __future__ import annotations
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.schemas.entities.failure import ValidationFailure

class IRule(ABC):
    """Define the contract for rule implementations."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def __init__(self, *, message: str | None = None) -> None:
        """
        Initialize the rule with an optional custom failure message.

        Parameters
        ----------
        message : str | None, optional
            Custom message used for validation failures. If ``None``, default
            messages are used.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """

    @abstractmethod
    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Asynchronously evaluate whether the current value satisfies this rule.

        Parameters
        ----------
        field : str
            Field name associated with ``value``.
        value : object
            Current field value to validate.
        instance : object
            Schema instance that owns the field value.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """

    @abstractmethod
    async def validate(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> ValidationFailure | None:
        """
        Await validation and return a failure or ``None``.

        Parameters
        ----------
        field : str
            Name of the field being validated.
        value : object
            Current field value to validate.
        instance : object
            Object instance that owns the field.

        Returns
        -------
        orionis.schemas.entities.failure.ValidationFailure | None
            A failure describing the constraint violation, or ``None`` when
            the value is valid.
        """
