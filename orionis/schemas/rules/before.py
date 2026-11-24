# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a date comes strictly before a reference moment."""

from datetime import UTC
from orionis.schemas.rules.temporal import resolve_moment, to_datetime
from orionis.schemas.rule import Rule


class Before(Rule):
    """
    Ensure a date comes strictly before a reference moment.

    The reference may be a sibling field name, a parsable date string, a
    ``datetime``/``date`` value, or ``None`` to compare against the current
    moment.
    """

    __slots__ = ("_reference",)
    """Declare the instance attribute slots reserved by this class."""

    __message__ = "Value must be a date before the reference moment."
    """Error text for message: ``Value must be a date before the reference moment.``."""
    __code__ = "before"
    """Code identifier: ``before``."""

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
        Check whether a temporal value falls earlier than the reference instant.

        Parameters
        ----------
        field : str
            Name of the field being validated.
        value : object
            Date, datetime, or text. Interpret naive inputs in the application zone.
        instance : object
            Schema instance used to resolve sibling field references.

        Returns
        -------
        bool
            True for an instant earlier than the reference. Other non-string types
            pass through to type validation.
        """
        moment = to_datetime(value)

        # Reject malformed text; delegate unrelated types to the type layer.
        if moment is None:
            return not isinstance(value, str)

        reference = resolve_moment(self._reference, instance)
        if reference is None:
            return False

        return moment.astimezone(UTC) < reference.astimezone(UTC)
