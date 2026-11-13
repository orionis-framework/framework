# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a value expresses an explicit acceptance."""

from orionis.schemas.rule import Rule

# Textual representations treated as an explicit acceptance.
_ACCEPTED_TEXT: frozenset[str] = frozenset({"yes", "on", "1", "true"})
"""Textual representations treated as an explicit acceptance."""


class Accepted(Rule):
    """
    Ensure a value expresses an explicit acceptance.

    Accepts ``True``, ``1`` and the strings ``"yes"``, ``"on"``, ``"1"``
    and ``"true"``, which makes it suitable for terms-of-service fields.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __message__ = "Value must be accepted."
    """Error text for message: ``Value must be accepted.``."""
    __code__ = "accepted"
    """Code identifier: ``accepted``."""

    async def enforce(
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
