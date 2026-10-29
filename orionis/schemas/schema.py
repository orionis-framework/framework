from __future__ import annotations
from annotationlib import Format, call_annotate_function
import types
from typing import TYPE_CHECKING, Annotated, Union, get_args, get_origin
import msgspec
from orionis.schemas.compiler import MetaCompiler
from orionis.schemas.constraint_plan import _ConstraintMessages, register_messages
from orionis.schemas.meta.validation import ValidationMetadata
from orionis.schemas.rule import Rule
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

def _compile_annotation(
    annotation: object, *, nested: bool = False,
) -> tuple[object, dict[str, str]]:
    """
    Compile constraints throughout an annotation and its nested types.

    Parameters
    ----------
    annotation : object
        Field or element annotation to compile.
    nested : bool, optional
        Whether the annotation belongs to a collection item or union branch.

    Returns
    -------
    tuple[object, dict[str, str]]
        Compiled annotation and messages declared on its outer metadata layer.

    Raises
    ------
    TypeError
        If a collection item or union branch declares an unsupported rule.
    MetadataConflictError
        If constraint declarations are invalid or incompatible.
    """
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Annotated:
        return _compile_annotated(annotation, arguments, nested=nested)

    if not arguments:
        return annotation, {}
    rewritten = tuple(
        _compile_annotation(item, nested=True)[0] for item in arguments
    )
    if all(old is new for old, new in zip(arguments, rewritten, strict=True)):
        return annotation, {}
    if origin is Union or origin is types.UnionType:
        return Union[rewritten], {}  # noqa: UP007
    copy_with = getattr(annotation, "copy_with", None)
    if copy_with is not None:
        return copy_with(rewritten), {}
    return origin[rewritten], {}


def _compile_annotated(
    annotation: object, arguments: tuple, *, nested: bool,
) -> tuple[object, dict[str, str]]:
    """
    Compile an Annotated layer and preserve its local error messages.

    Parameters
    ----------
    annotation : object
        Original Annotated declaration.
    arguments : tuple
        Base type followed by the declaration's metadata items.
    nested : bool
        Whether the declaration belongs to a collection item or union branch.

    Returns
    -------
    tuple[object, dict[str, str]]
        Rebuilt annotation and its messages indexed by validation code.

    Raises
    ------
    TypeError
        If nested metadata contains a rule requiring field-level execution.
    MetadataConflictError
        If constraint declarations are invalid or incompatible.
    """
    base, *metadata = arguments
    compiled_base, _ = _compile_annotation(base, nested=nested)
    validation = []
    custom = []
    messages = {}
    for item in metadata:
        if nested and isinstance(item, Rule):
            error_msg = (
                "Rules inside collection items or union branches are not supported. "
                "Use a child Schema for item rules or an outer Field for field rules."
            )
            raise TypeError(error_msg)
        if isinstance(item, Message):
            messages.setdefault("type", item.text)
        elif isinstance(item, ValidationMetadata):
            validation.append(item)
            key = _CONSTRAINT_MSGSPEC_KEYS.get(type(item))
            if key is not None and item.message is not None:
                messages[key] = item.message
        else:
            custom.append(item)
    if validation:
        compiled = Annotated[
            (compiled_base, MetaCompiler.compile(validation), *custom)
        ]
    elif compiled_base is base:
        compiled = annotation
    else:
        compiled = Annotated[(compiled_base, *metadata)]
    return register_messages(compiled, messages), messages

# The metaclass for all Schema subclasses.  Intercept class creation to compile
# ValidationMetadata into msgspec.Meta and collect custom metadata for later use.
_StructMeta = type(msgspec.Struct)

class SchemaMeta(_StructMeta):

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
        **kwargs: object,
    ) -> SchemaMeta:
        """
        Build a Schema subclass with compiled metadata and rule plans.

        Compile lazy annotations, merge inherited messages and index errors
        by encoded field name before preparing the validation plan.

        Parameters
        ----------
        cls : type
            Metaclass constructing the schema.
        name : str
            Name of the schema class.
        bases : tuple[type, ...]
            Direct base classes.
        namespace : dict[str, object]
            Class body namespace.
        **kwargs : object
            Options forwarded to the ``msgspec.Struct`` metaclass.

        Returns
        -------
        SchemaMeta
            Prepared schema class.

        Raises
        ------
        TypeError
            If field metadata contains an unsupported rule declaration.
        MetadataConflictError
            If constraint declarations are invalid or incompatible.
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
        inherited_messages = {}
        for base in reversed(bases):
            inherited_messages.update(getattr(base, "__orionis_field_messages__", {}))
        inherited_messages.update(constraint_msgs)
        klass.__orionis_field_messages__ = inherited_messages
        klass.__orionis_constraints__ = {
            field.encode_name: inherited_messages[field.name]
            for field in msgspec.structs.fields(klass)
            if inherited_messages.get(field.name)
        }

        # Import lazily to avoid module-level circular dependencies.
        from orionis.schemas.rules_executor import _build_plan  # noqa: PLC0415

        # Prebuild and cache the validation plan at class creation time.
        _build_plan(klass)

        # Return the fully prepared schema class.
        return klass

    @staticmethod
    def _wrap(
        original_func: Callable[[int], dict[str, object]],
        constraint_msgs: dict[str, dict[str, str]],
    ) -> Callable[[int], dict[str, object]]:
        """
        Wrap lazy annotation resolution with recursive metadata compilation.

        Parameters
        ----------
        original_func : Callable[[int], dict[str, object]]
            Original PEP 649 annotation callback.
        constraint_msgs : dict[str, dict[str, str]]
            Mapping populated with each field's local validation messages.

        Returns
        -------
        Callable[[int], dict[str, object]]
            Callback that compiles metadata while preserving string requests.
        """
        def _annotate(fmt: int) -> dict[str, object]:
            """
            Resolve annotations and compile metadata for the requested format.

            Parameters
            ----------
            fmt : int
                Annotation evaluation format requested by the caller.

            Returns
            -------
            dict[str, object]
                Compiled field annotations, or original string annotations.

            Raises
            ------
            TypeError
                If nested metadata contains an unsupported rule declaration.
            MetadataConflictError
                If constraint declarations are invalid or incompatible.
            """
            annotations = call_annotate_function(original_func, fmt)
            if fmt == Format.STRING:
                return annotations
            result = {}
            for name, annotation in annotations.items():
                compiled, messages = _compile_annotation(annotation)
                result[name] = compiled
                # Empty overrides also clear messages inherited from a base.
                constraint_msgs[name] = messages
            return result

        return _annotate

    @staticmethod
    def _collect(klass: type) -> dict[str, list[object]]:
        """
        Collect application metadata from a newly created schema class.

        Exclude native constraint metadata and internal message markers.

        Parameters
        ----------
        klass : type
            Schema class whose field metadata is inspected.

        Returns
        -------
        dict[str, list[object]]
            Field names mapped to their application metadata items, omitting
            fields with no such items.
        """
        # Initialize the output mapping.
        result: dict[str, list[object]] = {}

        # Bind the metadata annotation type.
        _msgspec_meta = (msgspec.Meta, _ConstraintMessages)

        # Bind the generic type origin helper.
        _get_origin = get_origin

        # Bind the generic type argument helper.
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
        Recursively convert the schema instance into a dictionary.

        Convert nested ``msgspec.Struct`` instances, including those inside
        dictionary values, lists, and tuples. Preserve field names, container
        types, and all other values without modifying the source.

        Returns
        -------
        dict[str, object]
            Dictionary containing recursively converted schema field values.
        """
        def _convert(value: object) -> object:
            """Recursively convert structs and their supported containers."""
            if isinstance(value, msgspec.Struct):
                value = msgspec.structs.asdict(value)
            if isinstance(value, dict):
                return {key: _convert(item) for key, item in value.items()}
            if isinstance(value, list):
                return [_convert(item) for item in value]
            if isinstance(value, tuple):
                return tuple(_convert(item) for item in value)
            return value

        return {
            name: _convert(value)
            for name, value in msgspec.structs.asdict(self).items()
        }

__all__: list[str] = [
    "Schema",
    "SchemaMeta",
]
