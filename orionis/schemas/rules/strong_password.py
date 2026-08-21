from orionis.schemas.rule import Rule

# Constants for password validation
_MIN_LENGTH = 8
_UPPER: frozenset[str] = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_LOWER: frozenset[str] = frozenset("abcdefghijklmnopqrstuvwxyz")
_DIGIT: frozenset[str] = frozenset("0123456789")

class StrongPassword(Rule):
    """
    Ensure a string is strong enough to be used as a password.

    The value must be at least 8 characters long and contain an uppercase
    letter, a lowercase letter and a digit.
    """

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = (
        f"Password must be at least {_MIN_LENGTH} characters long, "
        "contain an uppercase letter, a lowercase letter, and a digit."
    )
    __code__ = "strong_password"

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as a strong password.

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
        if not isinstance(value, str):
            return True

        if len(value) < _MIN_LENGTH:
            return False

        # Check for the presence of at least one uppercase letter, one lowercase
        # letter and one digit, short-circuiting on the first character found.
        return (
            not _UPPER.isdisjoint(value)
            and not _LOWER.isdisjoint(value)
            and not _DIGIT.isdisjoint(value)
        )
