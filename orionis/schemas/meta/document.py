"""Intermediate marker for documentation / JSON Schema metadata."""

from orionis.schemas.meta.validation import ValidationMetadata

class DocumentMetadata(ValidationMetadata):
    """
    Intermediate marker for documentation / JSON Schema metadata.

    Document metadata does not participate in value validation; it
    provides supplementary information used when generating JSON Schema
    or OpenAPI output (title, description, examples, extra properties).
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""
