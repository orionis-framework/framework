from orionis.schemas.rules.measure import is_file
from orionis.schemas.rule import Rule

class File(Rule):
    """Ensure a value is a successfully uploaded file."""

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "Value must be an uploaded file."
    __code__ = "file"

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as an uploaded file.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Owning object instance. This argument is accepted for
            interface compatibility.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        if not is_file(value):
            return False

        # An empty upload means the transfer never completed.
        size = getattr(value, "size", 0)
        return isinstance(size, int) and size > 0
