from __future__ import annotations
from typing import TYPE_CHECKING, Annotated, get_args, get_origin
import msgspec
from orionis.schemas.compiler import MetaCompiler
from orionis.schemas.meta.validation import ValidationMetadata
from orionis.schemas.metadata import (
    Message,
)
from orionis.schemas.constraints import (
    GreaterThan, GreaterThanOrEqual,
    LessThan, LessThanOrEqual,
    MinLength, MaxLength,
    MultipleOf, Pattern,
    TimezoneAware, TimezoneNaive,
)

if TYPE_CHECKING:
    from collections.abc import Callable

# Mapping: ValidationMetadata subclass -> msgspec.Meta keyword argument name.
_CONSTRAINT_MSGSPEC_KEYS: dict[type, str] = {
    MinLength: "min_length",
    MaxLength: "max_length",
    Pattern: "pattern",
    GreaterThan: "gt",
    GreaterThanOrEqual: "ge",
    LessThan: "lt",
    LessThanOrEqual: "le",
    MultipleOf: "multiple_of",
    TimezoneAware: "tz_aware",
    TimezoneNaive: "tz_naive",
}

# The metaclass for all Schema subclasses.  Intercept class creation to compile
# ValidationMetadata into msgspec.Meta and collect custom metadata for later use.
_StructMeta = type(msgspec.Struct)

class SchemaMeta(_StructMeta):

    # ruff: noqa: C901

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
        **kwargs: object,
    ) -> SchemaMeta:
        """
        Build a new ``Schema`` subclass with compiled metadata.

        Wrap ``__annotate_func__`` (PEP 649) so ``ValidationMetadata`` objects
        become ``msgspec.Meta`` instances, then attach ``__orionis_meta__``
        and ``__orionis_constraints__`` to the finished class.

        Parameters
        ----------
        cls : type
            Provide the metaclass itself.
        name : str
            Define the class name.
        bases : tuple[type, ...]
            Define the direct base classes.
        namespace : dict[str, object]
            Provide the class body namespace.
        **kwargs : object
            Forward metaclass keyword arguments to ``msgspec.Struct``.

        Returns
        -------
        SchemaMeta
            Return the created schema class.
        """
        # Read the lazy annotation callback from the class namespace.
        annotate_func: Callable[[int], dict[str, object]] | None = (
            namespace.get("__annotate_func__")
        )

        # Create a mutable container for per-field constraint messages.
        # It is populated when the wrapped annotate callback is executed.
        constraint_msgs: dict[str, dict[str, str]] = {}

        # Wrap the annotation callback to compile metadata and extract messages.
        if annotate_func is not None:
            namespace["__annotate_func__"] = SchemaMeta._wrap(
                annotate_func, constraint_msgs,
            )

        # Build the final schema class through msgspec.Struct metaclass.
        klass: SchemaMeta = super().__new__(cls, name, bases, namespace, **kwargs)

        # Collect non-msgspec metadata from all annotated fields.
        klass.__orionis_meta__ = SchemaMeta._collect(klass)

        # Persist custom constraint messages indexed by field and constraint key.
        klass.__orionis_constraints__ = constraint_msgs

        # Import lazily to avoid module-level circular dependencies.
        from orionis.schemas.rules_executor import _build_plan  # noqa: PLC0415

        # Prebuild and cache the validation plan at class creation time.
        _build_plan(klass)

        # Return the fully prepared schema class.
        return klass

    @staticmethod
    def _wrap( # NOSONAR
        original_func: Callable[[int], dict[str, object]],
        constraint_msgs: dict[str, dict[str, str]],
    ) -> Callable[[int], dict[str, object]]:
        """
        Return a wrapped annotate callable for the Python 3.14 lazy protocol.

        Call the original annotate function to obtain raw annotations, compile
        ``ValidationMetadata`` items into ``msgspec.Meta``, and extract custom
        error messages into ``constraint_msgs``.

        Capture module-level globals as closure locals so the inner
        ``_annotate`` uses ``LOAD_DEREF`` rather than ``LOAD_GLOBAL``.

        Parameters
        ----------
        original_func : Callable[[int], dict[str, object]]
            Provide the original PEP 649 annotation callback.
        constraint_msgs : dict[str, dict[str, str]]
            Store per-field custom error messages keyed by constraint name.

        Returns
        -------
        Callable[[int], dict[str, object]]
            Return the wrapped annotation callback.
        """
        # Cache compiler class in local scope for faster access.
        _meta_compiler = MetaCompiler

        # Cache validation metadata type for isinstance checks.
        _validation_metadata = ValidationMetadata

        # Cache message metadata type for isinstance checks.
        _message_type = Message

        # Cache map from metadata class to msgspec key.
        _constraint_keys = _CONSTRAINT_MSGSPEC_KEYS

        # Cache typing.get_origin to reduce global lookups.
        _get_origin = get_origin

        # Cache typing.get_args to reduce global lookups.
        _get_args = get_args

        # Cache Annotated marker type for identity checks.
        _annotated_type = Annotated

        def _annotate(fmt: int) -> dict[str, object]:

            # Resolve deferred annotations for the given format.
            annotations: dict[str, object] = original_func(fmt)

            # Prepare output annotations dictionary.
            result: dict[str, object] = {}
            for k, v in annotations.items():

                # Keep non-Annotated entries unchanged.
                if _get_origin(v) is not _annotated_type:

                    # Preserve original annotation.
                    result[k] = v

                    # Skip metadata processing for non-Annotated fields.
                    continue

                # Split Annotated into base type and metadata payload.
                args = _get_args(v)

                # Extract the original field type.
                base_type: object = args[0]

                # Extract all metadata objects.
                metadata: tuple[object, ...] = args[1:]

                # Single-pass classification: avoids iterating `metadata`.
                # Hold optional type-level message metadata.
                type_msg: Message | None = None

                # Collect validation metadata for compilation.
                validation_meta: list[ValidationMetadata] = []

                # Collect non-validation metadata to preserve.
                custom_meta: list[object] = []
                for m in metadata:

                    # Keep only the first Message instance as type message.
                    if isinstance(m, _message_type):
                        # Save the first type message found.
                        if type_msg is None:
                            type_msg = m

                    # Collect validation metadata used to build msgspec.Meta.
                    elif isinstance(m, _validation_metadata):
                        # Queue validation rule metadata.
                        validation_meta.append(m)

                    # Preserve any other metadata untouched.
                    else:
                        # Keep custom metadata for final Annotated.
                        custom_meta.append(m)

                # Collect custom messages keyed by their msgspec constraint name.
                # Direct slot read (m.message) instead of getattr(m, "message", None):
                # all ConstraintMetadata subclasses declare the slot, so the 3-arg
                # getattr fallback machinery is never needed.
                msgs: dict[str, str] = {
                    key: m.message
                    for m in validation_meta
                    if (key := _constraint_keys.get(type(m))) is not None
                    and m.message is not None  # direct slot read; no getattr overhead
                }

                # Register the Message text under the reserved "type" key.
                if type_msg is not None:
                    # Add custom type error message when provided.
                    msgs["type"] = type_msg.text
                if msgs:
                    # Persist field-level custom messages.
                    constraint_msgs[k] = msgs

                # If there are no validation rules, keep the annotation as-is.
                if not validation_meta:
                    # Return original Annotated with unchanged metadata.
                    result[k] = v
                    # Skip compilation for this field.
                    continue

                # Compile validation metadata once.
                compiled: msgspec.Meta = _meta_compiler.compile(validation_meta)
                # Rebuild Annotated with compiled + custom meta.
                result[k] = Annotated[(base_type, compiled, *custom_meta)]

            # Return rewritten annotations dictionary.
            return result

        # Return wrapped callback compatible with lazy annotation protocol.
        return _annotate

    @staticmethod
    def _collect(klass: type) -> dict[str, list[object]]:
        """
        Collect custom non-msgspec metadata from a freshly created struct.

        Iterate over each field of ``klass`` and collect ``Annotated``
        arguments that are not ``msgspec.Meta`` instances into a
        ``field_name -> [custom_items]`` mapping.

        Parameters
        ----------
        klass :
            The newly created ``Schema`` subclass.

        Returns
        -------
        dict[str, list[object]]
            A mapping of field names to their custom metadata objects.
            Fields with no custom metadata are omitted.
        """
        # Initialize the output mapping.
        result: dict[str, list[object]] = {}

        # Cache Meta type to reduce repeated lookups.
        _msgspec_meta = msgspec.Meta

        # Cache get_origin to reduce global lookups.
        _get_origin = get_origin

        # Cache get_args to reduce global lookups.
        _get_args = get_args

        # Iterate through all struct fields.
        for field in msgspec.structs.fields(klass):

            # Process only Annotated field types.
            if _get_origin(field.type) is Annotated:
                custom: list[object] = [
                    item
                    for item in _get_args(field.type)[1:]
                    if not isinstance(item, _msgspec_meta)
                ]

                # Store only fields that contain custom metadata.
                if custom:
                    result[field.name] = custom  # Map field name to its custom items.

        # Return collected custom metadata by field name.
        return result

class Schema(msgspec.Struct, metaclass=SchemaMeta):
    """
    Define the base class for Orionis schema declarations.

    Notes
    -----
    Inherit ``msgspec.Struct`` behavior and the ``SchemaMeta`` metaclass
    pipeline, which compiles validation metadata and stores Orionis custom
    metadata on the resulting class.
    """

    def toDict(self) -> dict[str, object]:
        """
        Convert the schema instance into a dictionary.

        Returns
        -------
        dict[str, object]
            Dictionary containing the schema fields and their values.
        """
        return msgspec.structs.asdict(self)

__all__: list[str] = [
    "Schema",
    "SchemaMeta",
]
