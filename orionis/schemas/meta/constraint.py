from orionis.schemas.meta.validation import ValidationMetadata

class ConstraintMetadata(ValidationMetadata):
    """
    Intermediate marker for validation constraints.

    Constraint metadata participates in value validation at decode time.
    Each concrete subclass exposes a ``message`` keyword-only field
    (default ``None``); when it is set, ``SchemaMeta`` stores it in
    ``__orionis_constraints__`` and it replaces the default error message
    reported for that constraint.
    """

    __slots__ = ()
