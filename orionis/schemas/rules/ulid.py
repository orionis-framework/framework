# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a string is a valid lexicographically sortable identifier."""

from orionis.schemas.rule import Rule

# Crockford base32 alphabet, excluding I, L, O and U.
_ALPHABET: frozenset[str] = frozenset("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
"""Crockford base32 alphabet, excluding I, L, O and U."""

# Canonical length of the textual representation.
_LENGTH = 26
"""Canonical length of the textual representation."""

# Highest first character keeping the 48-bit timestamp within range.
_MAX_LEADING = "7"
"""Highest first character keeping the 48-bit timestamp within range."""


class Ulid(Rule):
    """Ensure a string is a valid lexicographically sortable identifier."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __message__ = "Value must be a valid ULID."
    """Error text for message: ``Value must be a valid ULID.``."""
    __code__ = "ulid"
    """Code identifier: ``ulid``."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as a ULID.

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
        # Leave non-string values to the type layer, which already reports them.
        if not isinstance(value, str):
            return True

        if len(value) != _LENGTH or not value.isascii():
            return False

        # The textual form is case-insensitive, so compare in upper case.
        upper = value.upper()

        if not _ALPHABET.issuperset(upper):
            return False

        # Anything above '7' overflows the 48-bit timestamp component.
        return upper[0] <= _MAX_LEADING
