from orionis.schemas.rule import Rule

# Crockford base32 alphabet, excluding I, L, O and U.
_ALPHABET: frozenset[str] = frozenset("0123456789ABCDEFGHJKMNPQRSTVWXYZ")

# Canonical length of the textual representation.
_LENGTH = 26

# Highest first character keeping the 48-bit timestamp within range.
_MAX_LEADING = "7"

class Ulid(Rule):
    """Ensure a string is a valid lexicographically sortable identifier."""

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "Value must be a valid ULID."
    __code__ = "ulid"

    def enforce(
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

        if len(value) != _LENGTH:
            return False

        # The textual form is case-insensitive, so compare in upper case.
        upper = value.upper()

        if not _ALPHABET.issuperset(upper):
            return False

        # Anything above '7' overflows the 48-bit timestamp component.
        return upper[0] <= _MAX_LEADING
