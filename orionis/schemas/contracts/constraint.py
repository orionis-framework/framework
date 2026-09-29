from __future__ import annotations
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.schemas.entities.failure import ValidationFailure

class IRule(ABC):

    __slots__ = ()

    @abstractmethod
    def __init__(self, *, message: str | None = None) -> None:
        """
        Initialize the rule with an optional custom failure message.

        Parameters
        ----------
        message : str | None, optional
            Custom message used for validation failures. If ``None``, default
            messages are used.
        """

    @abstractmethod
    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Evaluate whether the current value satisfies this rule.

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
    def validate(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> ValidationFailure | None:
        """
        Validate the provided value and return a failure or ``None``.

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
        ValidationFailure | None
            A failure describing the constraint violation, or ``None`` when
            the value is valid.
        """
