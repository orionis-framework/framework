import unicodedata
from orionis.schemas.rule import Rule

# Unicode general category prefixes accepted as alphabetic content.
_LETTER_CATEGORIES: frozenset[str] = frozenset({"L", "M"})

class Alpha(Rule):
    """
    Ensure a string contains only alphabetic characters.

    By default every Unicode letter and combining mark is accepted. Set
    ``ascii_only`` to restrict the value to the ``a-z`` and ``A-Z`` ranges.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_ascii_only",)

    __message__ = "Value must contain only alphabetic characters."
    __code__ = "alpha"

    def __init__(
        self,
        *,
        ascii_only: bool = False,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the accepted character range.

        Parameters
        ----------
        ascii_only : bool, optional
            Whether to restrict the value to ASCII letters.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.
        """
        super().__init__(message=message)
        self._ascii_only: bool = ascii_only

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as alphabetic content.

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

        if not value:
            return False

        if self._ascii_only:
            return value.isascii() and value.isalpha()

        # ``str.isalpha`` excludes combining marks, so categories are read.
        category = unicodedata.category
        return all(category(char)[0] in _LETTER_CATEGORIES for char in value)
