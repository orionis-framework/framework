import ipaddress
from orionis.schemas.rule import Rule

# IP versions the rule is able to enforce.
_VERSIONS: frozenset[int] = frozenset({4, 6})

class IpAddress(Rule):
    """
    Ensure a string is a valid IP address.

    Version 4 is enforced by default. Pass ``version=6`` to require IPv6, or
    ``version=None`` to accept either family.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_version",)

    __message__ = "Value must be a valid IP address."
    __code__ = "ip"

    def __init__(
        self,
        version: int | None = 4,
        *,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the required IP version.

        Parameters
        ----------
        version : int | None, optional
            Required IP version, either ``4`` or ``6``. Use ``None`` to
            accept both families.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If ``version`` is neither ``4``, ``6`` nor ``None``.
        """
        super().__init__(message=message)
        if version is not None and version not in _VERSIONS:
            error_msg = f"Unsupported IP version: {version!r}. Use 4, 6 or None."
            raise ValueError(error_msg)
        self._version: int | None = version

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as an IP address.

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

        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return False

        return self._version is None or address.version == self._version
