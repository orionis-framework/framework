import re
from orionis.schemas.rule import Rule

# Colon, hyphen and Cisco dotted notations for a 48-bit hardware address.
_MAC_PATTERN = re.compile(
    r"^(?:[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}"
    r"|[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5}"
    r"|[0-9A-Fa-f]{4}(?:\.[0-9A-Fa-f]{4}){2})$",
)

class MacAddress(Rule):
    """
    Ensure a string is a valid MAC address.

    Colon-separated, hyphen-separated and Cisco dotted notations are all
    accepted.
    """

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "Value must be a valid MAC address."
    __code__ = "mac_address"

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as a MAC address.

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

        return _MAC_PATTERN.match(value) is not None
