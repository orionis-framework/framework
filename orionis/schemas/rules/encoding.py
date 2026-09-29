from orionis.schemas.rules.measure import read_content
from orionis.schemas.rule import Rule

# Codec aliases that are always available through the standard library.
_DEFAULT_ENCODING = "utf-8"

class Encoding(Rule):
    """
    Ensure a value can be represented in a given character encoding.

    Strings are re-encoded and uploaded files are decoded, so the rule
    covers both textual fields and text uploads.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_encoding",)

    __message__ = "Value must match the required character encoding."
    __code__ = "encoding"

    def __init__(
        self,
        encoding: str = _DEFAULT_ENCODING,
        *,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the required character encoding.

        Parameters
        ----------
        encoding : str, optional
            Codec name the value must be representable in.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If ``encoding`` does not name a known codec.
        """
        super().__init__(message=message)
        try:
            "".encode(encoding)
        except LookupError as exc:
            error_msg = f"Unknown character encoding: {encoding!r}."
            raise ValueError(error_msg) from exc
        self._encoding: str = encoding

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the required encoding.

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
        content = read_content(value)

        # Textual fields are checked by re-encoding them into the codec.
        if content is None:
            if not isinstance(value, str):
                return True
            try:
                value.encode(self._encoding)
            except UnicodeEncodeError:
                return False
            return True

        try:
            content.decode(self._encoding)
        except UnicodeDecodeError:
            return False

        return True
