# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a date comes strictly after a reference moment."""

from orionis.schemas.rules.temporal import resolve_moment, to_datetime
from orionis.schemas.rule import Rule


class After(Rule):
    """
    Ensure a date comes strictly after a reference moment.

    The reference may be a sibling field name, a parsable date string, a
    ``datetime``/``date`` value, or ``None`` to compare against the current
    moment.
    """

    __slots__ = ("_reference",)
    """Declare the instance attribute slots reserved by this class."""

    __message__ = "Value must be a date after the reference moment."
    """Error text for message: ``Value must be a date after the reference moment.``."""
    __code__ = "after"
    """Code identifier: ``after``."""

    def __init__(
        self,
        reference: object = None,
        *,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the reference moment.

        Parameters
        ----------
        reference : object, optional
            Sibling field name, date string or datetime to compare against.
            Defaults to the current moment.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            No return value.
        """
        super().__init__(message=message)
        self._reference: object = reference
        """
        Sibling field name, date string or datetime to compare against. Defaults to
        the current moment.
        """

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the reference moment.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Schema instance used to resolve sibling field references.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        moment = to_datetime(value)

        # Reject malformed text; delegate unrelated types to the type layer.
        if moment is None:
            return not isinstance(value, str)

        reference = resolve_moment(self._reference, instance)
        if reference is None:
            return False

        return moment > reference
