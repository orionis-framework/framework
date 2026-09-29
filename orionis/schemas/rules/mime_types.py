from orionis.schemas.rules.measure import is_file
from orionis.schemas.rule import Rule

class MimeTypes(Rule):
    """
    Ensure an uploaded file declares one of the accepted MIME types.

    Wildcard subtypes such as ``"image/*"`` match every subtype of the given
    top-level type.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_exact", "_prefixes")

    __message__ = "File must match one of the accepted MIME types."
    __code__ = "mimetypes"

    def __init__(self, *mime_types: str, message: str | None = None) -> None:
        """
        Initialize the rule with the accepted MIME types.

        Parameters
        ----------
        *mime_types : str
            MIME types the file may declare, optionally using a wildcard
            subtype. At least one is required.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If no MIME type is supplied.
        """
        super().__init__(message=message)
        if not mime_types:
            error_msg = "MimeTypes requires at least one MIME type."
            raise ValueError(error_msg)

        # Split wildcards from exact types once, so matching stays O(1).
        exact: set[str] = set()
        prefixes: list[str] = []
        for mime_type in mime_types:
            normalized = mime_type.split(";", 1)[0].strip().lower()
            if normalized.endswith("/*"):
                prefixes.append(normalized[:-1])
            else:
                exact.add(normalized)

        self._exact: frozenset[str] = frozenset(exact)
        self._prefixes: tuple[str, ...] = tuple(prefixes)

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate an uploaded file against the accepted MIME types.

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
        if not is_file(value):
            return False

        content_type = getattr(value, "content_type", None)
        if not isinstance(content_type, str):
            return False

        # Strip any charset or boundary parameter before comparing.
        declared = content_type.split(";", 1)[0].strip().lower()

        return declared in self._exact or declared.startswith(self._prefixes)
