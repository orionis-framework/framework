from __future__ import annotations
from typing import TYPE_CHECKING
import msgspec
from orionis.schemas.metadata import (
    Description,
    Examples,
    Extra,
    ExtraJsonSchema,
    Title,
)
from orionis.schemas.constraints import (
    GreaterThan,
    GreaterThanOrEqual,
    LessThan,
    LessThanOrEqual,
    MaxLength,
    MinLength,
    MultipleOf,
    Pattern,
    TimezoneAware,
    TimezoneNaive,
)

if TYPE_CHECKING:
    from orionis.schemas.meta.validation import ValidationMetadata

class MetadataConflictError(ValueError):
    """
    Signal incompatible or invalid metadata annotations detected by ``MetaCompiler``.

    Four conflict categories are recognized:

    * **Duplicate types** — the same concrete metadata class appears more than
      once in the annotation list (e.g., two ``MinLength`` instances).
    * **Ambiguous bounds** — both an exclusive and an inclusive variant of the
      same bound are present (e.g., ``GreaterThan`` + ``GreaterThanOrEqual``).
    * **Logically impossible ranges** — the combined constraints produce an
      empty valid set (e.g., ``MinLength(100)`` with ``MaxLength(10)``, or
      ``TimezoneAware`` with ``TimezoneNaive``).
    * **Invalid values** — a constraint carries a value that is semantically
      illegal (e.g., ``MultipleOf(0)``, ``MinLength(-1)``, ``MaxLength(-5)``).
    """

class MetaCompiler:
    """
    Compile Orionis metadata annotations into a field constraint descriptor.

    Act as the single integration point between Orionis' public metadata API
    and the underlying serialization layer. Schema consumers (validation,
    JSON Schema generation, OpenAPI export) should use this compiler so that
    the serialization layer remains an implementation detail invisible to
    application code.
    """

    __slots__ = ()

    @staticmethod
    def compile(metadata: list[ValidationMetadata]) -> msgspec.Meta:
        """
        Compile metadata annotations into a field constraint descriptor.

        Parameters
        ----------
        metadata : list[ValidationMetadata]
            The list of field-level metadata annotations to compile.
            Order does not matter; each concrete type may appear at most once.

        Returns
        -------
        msgspec.Meta
            A field constraint descriptor configured with all provided
            constraints and documentation properties.

        Raises
        ------
        MetadataConflictError
            If any duplicate or logically conflicting metadata is detected
            before the descriptor is constructed.
        """
        seen = MetaCompiler._index(metadata)
        MetaCompiler._validateConflicts(seen)
        return MetaCompiler._build(seen)

    @staticmethod
    def _index(
        metadata: list[ValidationMetadata],
    ) -> dict[type[ValidationMetadata], ValidationMetadata]:
        """
        Build a ``type → instance`` mapping and reject duplicate types.

        Parameters
        ----------
        metadata : list[ValidationMetadata]
            Raw annotation list from the caller.

        Returns
        -------
        dict[type[ValidationMetadata], ValidationMetadata]
            Mapping from each concrete metadata type to its single instance.

        Raises
        ------
        MetadataConflictError
            If the same concrete type appears more than once.
        """
        if not metadata:
            return {}
        seen: dict[type[ValidationMetadata], ValidationMetadata] = {}
        for meta in metadata:
            t = type(meta)
            if t in seen:
                msg = (
                    f"Duplicate metadata annotation: '{t.__name__}'"
                    " appears more than once. "
                    "Each metadata type may be used at most once per field."
                )
                raise MetadataConflictError(msg)
            seen[t] = meta
        return seen

    @staticmethod
    def _validateConflicts( # NOSONAR
        seen: dict[type[ValidationMetadata], ValidationMetadata],
    ) -> None:
        """
        Validate the indexed metadata for all semantic conflicts in a single pass.

        Checks are applied in order: ambiguous bounds, impossible numeric ranges,
        impossible length ranges, mutually exclusive timezone flags, and invalid
        individual values.  All checks are inlined to eliminate five separate
        staticmethod call overheads and to consolidate shared ``seen.get()``
        calls (MinLength and MaxLength are looked up once instead of twice).

        Parameters
        ----------
        seen : dict[type[ValidationMetadata], ValidationMetadata]
            The indexed metadata mapping produced by ``_index``.

        Raises
        ------
        MetadataConflictError
            On any detected conflict.
        """
        # Ambiguous bounds
        if GreaterThan in seen and GreaterThanOrEqual in seen:
            msg = (
                "Cannot combine 'GreaterThan' and 'GreaterThanOrEqual'"
                " on the same field. "
                "Use one exclusive lower bound or one inclusive lower bound, not both."
            )
            raise MetadataConflictError(msg)
        if LessThan in seen and LessThanOrEqual in seen:
            msg = (
                "Cannot combine 'LessThan' and 'LessThanOrEqual'"
                " on the same field. "
                "Use one exclusive upper bound or one inclusive upper bound, not both."
            )
            raise MetadataConflictError(msg)

        # Numeric range
        lower_gt = seen.get(GreaterThan)
        lower_ge = seen.get(GreaterThanOrEqual)
        upper_lt = seen.get(LessThan)
        upper_le = seen.get(LessThanOrEqual)
        lower = lower_gt or lower_ge
        upper = upper_lt or upper_le
        if lower is not None and upper is not None:
            lower_val = lower.value
            upper_val = upper.value
            inclusive = lower_ge is not None and upper_le is not None
            invalid = lower_val > upper_val if inclusive else lower_val >= upper_val
            if invalid:
                msg = (
                    f"Impossible numeric range: {type(lower).__name__}({lower_val})"
                    f" combined with {type(upper).__name__}({upper_val})"
                    " produces an empty set of valid values."
                )
                raise MetadataConflictError(msg)

        # Length range + value checks (single lookup per type)
        min_len = seen.get(MinLength)
        max_len = seen.get(MaxLength)
        if (
            min_len is not None
            and max_len is not None
            and min_len.value > max_len.value
        ):
            msg = (
                f"Impossible length range: MinLength({min_len.value})"
                f" is greater than MaxLength({max_len.value}). "
                "The minimum length must not exceed the maximum."
            )
            raise MetadataConflictError(msg)

        # Timezone
        if TimezoneAware in seen and TimezoneNaive in seen:
            msg = (
                "Cannot combine 'TimezoneAware' and 'TimezoneNaive'"
                " on the same field. "
                "A datetime field cannot simultaneously require and"
                " forbid timezone information."
            )
            raise MetadataConflictError(msg)

        # Individual value validity
        mul = seen.get(MultipleOf)
        if mul is not None and mul.value <= 0:
            msg = (
                f"Invalid 'MultipleOf' value: {mul.value!r}."
                " The divisor must be strictly positive (> 0)."
            )
            raise MetadataConflictError(msg)
        if min_len is not None and min_len.value < 0:
            msg = (
                f"Invalid 'MinLength' value: {min_len.value!r}."
                " The minimum length must be non-negative (>= 0)."
            )
            raise MetadataConflictError(msg)
        if max_len is not None and max_len.value < 0:
            msg = (
                f"Invalid 'MaxLength' value: {max_len.value!r}."
                " The maximum length must be non-negative (>= 0)."
            )
            raise MetadataConflictError(msg)

    @staticmethod
    def _build(
        seen: dict[type[ValidationMetadata], ValidationMetadata],
    ) -> msgspec.Meta:
        """
        Construct the field constraint descriptor from the validated metadata index.

        Built in a single pass over *seen* to avoid allocating intermediate
        dictionaries.  All fourteen ``msgspec.Meta`` parameters are populated
        here in one go, each guarded by an O(1) dict look-up.

        Parameters
        ----------
        seen : dict[type[ValidationMetadata], ValidationMetadata]
            The conflict-free metadata index produced by ``_index``.

        Returns
        -------
        msgspec.Meta
            The fully configured field constraint descriptor.
        """
        # Localize the dict.get method to reduce attribute look-up
        # overhead in this hot path.
        _s = seen.get
        gt_m    = _s(GreaterThan)
        ge_m    = _s(GreaterThanOrEqual)
        lt_m    = _s(LessThan)
        le_m    = _s(LessThanOrEqual)
        mul_m   = _s(MultipleOf)
        pat_m   = _s(Pattern)
        minl_m  = _s(MinLength)
        maxl_m  = _s(MaxLength)
        title_m = _s(Title)
        desc_m  = _s(Description)
        ex_m    = _s(Examples)
        exj_m   = _s(ExtraJsonSchema)
        ext_m   = _s(Extra)

        # Resolve the timezone flag from the two mutually exclusive markers.
        tz: bool | None = None
        if TimezoneAware in seen:
            tz = True
        elif TimezoneNaive in seen:
            tz = False

        return msgspec.Meta(
            gt           = gt_m.value        if gt_m    is not None else None,
            ge           = ge_m.value        if ge_m    is not None else None,
            lt           = lt_m.value        if lt_m    is not None else None,
            le           = le_m.value        if le_m    is not None else None,
            multiple_of  = mul_m.value       if mul_m   is not None else None,
            pattern      = pat_m.regex       if pat_m   is not None else None,
            min_length   = minl_m.value      if minl_m  is not None else None,
            max_length   = maxl_m.value      if maxl_m  is not None else None,
            tz           = tz,
            title        = title_m.value     if title_m is not None else None,
            description  = desc_m.value      if desc_m  is not None else None,
            examples     = list(ex_m.values) if ex_m    is not None else None,
            extra_json_schema = dict(exj_m.data) if exj_m is not None else None,
            extra        = dict(ext_m.data)  if ext_m   is not None else None,
        )

# Expose only the public API of this module via __all__
# to prevent accidental imports of internal helper functions.
__all__: list[str] = [
    "MetaCompiler",
    "MetadataConflictError",
]
