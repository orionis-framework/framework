"""Represent a validation failure."""

from dataclasses import dataclass
from orionis.support.entities.base import BaseEntity


@dataclass(slots=True, frozen=True)
class ValidationFailure(BaseEntity):
    """
    Represent a validation failure.

    Attributes
    ----------
    field : str
        Identify the field that failed validation.
    rule : str
        Identify the validation rule that failed.
    message : str
        Describe the validation failure.

    Returns
    -------
    orionis.schemas.entities.failure.ValidationFailure
        Return a new immutable validation failure instance when instantiated.
    """

    # Store validation failure details.
    field: str
    rule: str
    message: str

    def toDict(self) -> dict:
        """
        Return the failure as a plain dictionary.

        Serialize the three string fields directly without the recursive
        conversion performed by ``BaseEntity.toDict``.

        Returns
        -------
        dict
            ``{"field": ..., "rule": ..., "message": ...}``
        """
        return {
            "field": self.field,
            "rule": self.rule,
            "message": self.message,
        }
