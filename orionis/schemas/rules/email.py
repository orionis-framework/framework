import re
from orionis.schemas.rule import Rule

# Constants for email validation
_MAX_LENGTH = 254
_MAX_LOCAL_LENGTH = 64

# Local part: dot-separated atoms of RFC 5322 allowed characters.
_LOCAL_ATOM = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"

# Domain label: alphanumeric edges with optional inner hyphens.
_DOMAIN_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"

_EMAIL_PATTERN = re.compile(
    rf"^{_LOCAL_ATOM}(?:\.{_LOCAL_ATOM})*@{_DOMAIN_LABEL}(?:\.{_DOMAIN_LABEL})+$",
)

class Email(Rule):

    # ruff: noqa: ARG002

    __message__ = "Value must be a valid email address."
    __code__ = "email"

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as an email address.

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

        # Reject addresses exceeding the maximum length allowed by RFC 5321.
        if len(value) > _MAX_LENGTH:
            return False

        if _EMAIL_PATTERN.match(value) is None:
            return False

        # The local part is capped independently of the whole address.
        local_part, _, _ = value.partition("@")
        return len(local_part) <= _MAX_LOCAL_LENGTH
