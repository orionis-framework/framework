from __future__ import annotations
from dataclasses import dataclass

# Number of segments expected in a qualified reference such as "companies.id".
_REFERENCE_PARTS: int = 2

@dataclass(frozen=True, slots=True)
class ForeignReference:
    """
    Immutable value object describing a foreign key reference.

    Attributes
    ----------
    table : str
        Name of the referenced table.
    column : str
        Name of the referenced column.
    """

    table: str
    column: str

    @classmethod
    def parse(cls, reference: str) -> ForeignReference:
        """
        Build a reference from a ``"table.column"`` qualified string.

        Parameters
        ----------
        reference : str
            Qualified reference in the form ``"table.column"``.

        Returns
        -------
        ForeignReference
            Parsed reference value object.

        Raises
        ------
        ValueError
            If the reference is not a non-empty ``"table.column"`` string.
        """
        # Split into exactly two non-empty segments.
        parts = reference.split(".") if isinstance(reference, str) else []
        if len(parts) != _REFERENCE_PARTS or not parts[0] or not parts[1]:
            error_msg = (
                f"Invalid foreign reference '{reference}'. "
                "Expected the 'table.column' format, e.g. 'companies.id'."
            )
            raise ValueError(error_msg)
        return cls(table=parts[0], column=parts[1])

    def qualified(self) -> str:
        """
        Return the reference in its qualified ``"table.column"`` form.

        Returns
        -------
        str
            Qualified reference string.
        """
        return f"{self.table}.{self.column}"
