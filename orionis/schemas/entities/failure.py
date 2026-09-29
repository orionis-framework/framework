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
    ValidationFailure
        Return a new immutable validation failure instance when instantiated.
    """

    # Store validation failure details.
    field: str
    rule: str
    message: str

    def toDict(self) -> dict:
        """
        Return the failure as a plain dictionary.

        Overrides ``BaseEntity.toDict`` to bypass the generic ``asdict``
        machinery (deep-copy, lambda, enum serializer) that would cost 5X
        more for a three-string struct.  All fields are plain ``str``, so
        no conversion is needed.

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
