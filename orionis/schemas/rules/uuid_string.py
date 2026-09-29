import re
from orionis.schemas.rule import Rule

_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
)

# Versions defined by RFC 9562.
_VERSIONS: frozenset[int] = frozenset({1, 3, 4, 5, 6, 7, 8})

# Nibbles marking the RFC 9562 variant in the third group of the identifier.
_VARIANT_NIBBLES: frozenset[str] = frozenset("89ab")

# Offsets of the version and variant nibbles in the canonical representation.
_VERSION_INDEX = 14
_VARIANT_INDEX = 19

class Uuid(Rule):
    """
    Ensure a string is a valid RFC 9562 universally unique identifier.

    Any version is accepted by default; pass ``version`` to require one
    specific layout.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_version",)

    __message__ = "Value must be a valid UUID."
    __code__ = "uuid"

    def __init__(
        self,
        version: int | None = None,
        *,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the required UUID version.

        Parameters
        ----------
        version : int | None, optional
            Required version among ``1``, ``3``, ``4``, ``5``, ``6``, ``7``
            and ``8``. Use ``None`` to accept any version.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If ``version`` is not one of the versions defined by RFC 9562.
        """
        super().__init__(message=message)
        if version is not None and version not in _VERSIONS:
            error_msg = (
                f"Unsupported UUID version: {version!r}. "
                "Use 1, 3, 4, 5, 6, 7, 8 or None."
            )
            raise ValueError(error_msg)
        self._version: int | None = version

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as a UUID.

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

        if _UUID_PATTERN.match(value) is None:
            return False

        if self._version is None:
            return True

        # A versioned identifier must also carry the RFC 9562 variant bits.
        return (
            value[_VERSION_INDEX] == str(self._version)
            and value[_VARIANT_INDEX].lower() in _VARIANT_NIBBLES
        )
