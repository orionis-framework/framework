from orionis.schemas.rule import Rule

# Textual representations treated as an explicit acceptance.
_ACCEPTED_TEXT: frozenset[str] = frozenset({"yes", "on", "1", "true"})

class Accepted(Rule):
    """
    Ensure a value expresses an explicit acceptance.

    Accepts ``True``, ``1`` and the strings ``"yes"``, ``"on"``, ``"1"``
    and ``"true"``, which makes it suitable for terms-of-service fields.
    """

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "Value must be accepted."
    __code__ = "accepted"

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as an acceptance flag.

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
        # Booleans are checked first: they are integers in Python.
        if isinstance(value, bool):
            return value

        if isinstance(value, int):
            return value == 1

        if isinstance(value, str):
            return value.lower() in _ACCEPTED_TEXT

        return False
