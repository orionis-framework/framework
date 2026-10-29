from __future__ import annotations
from typing import TYPE_CHECKING
import msgspec
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.failure_collector import FailureCollector
from orionis.schemas.instance_payload import instance_payload
from orionis.schemas.rules_executor import (
    _build_plan,
    _cache_get,
    _collect_with_plan,
)

if TYPE_CHECKING:
    from orionis.schemas.entities.failure import ValidationFailure
    from orionis.schemas.schema import Schema as SchemaType

# Alias msgspec's convert function to avoid direct dependency on msgspec in the
# rest of the codebase.
_convert = msgspec.convert

# Alias msgspec's ValidationError to avoid direct
# dependency on msgspec in the rest of the codebase.
_ValidationError = msgspec.ValidationError
_Struct = msgspec.Struct

class Schema:

    # Prevent per-instance dictionaries; the class is used statically.
    __slots__ = ()

    @staticmethod
    async def validate(payload: object, schema: type[SchemaType]) -> SchemaType:
        """
        Validate a payload or existing struct and await its schema rules.

        Parameters
        ----------
        payload : object
            Input data or root struct to expand and revalidate.
        schema : type[SchemaType]
            Schema class used for conversion and rule validation.

        Returns
        -------
        SchemaType
            Converted instance satisfying structural constraints and rules.

        Raises
        ------
        ValidationException
            If conversion, constraints or rules reject the payload. Include
            collected failures grouped by field.
        """
        # Struct constructors and mutation do not validate their values.
        # Only existing structs need this expansion; ordinary decoded request
        # mappings retain the single C-level conversion below.
        if type(payload) is not dict and isinstance(payload, _Struct):
            payload = instance_payload(payload)

        # Convert the payload into a schema instance using msgspec. A single
        # C-level call handles the successful path; only when it fails is the
        # payload re-inspected field by field to report every error.
        try:
            instance = _convert(payload, type=schema)

        # Catch msgspec validation errors and re-raise them as framework exceptions.
        except _ValidationError as exc:
            raise ValidationException(
                await FailureCollector.collect(payload, schema, exc),
            ) from exc

        # Use the known schema type directly — avoids a redundant type(instance)
        # call. Skip execution entirely when the plan is empty (the common case
        # for simple schemas with no custom rules).
        plan = _cache_get(schema)
        if plan is None:
            plan = _build_plan(schema)
        if plan:
            failures: list[ValidationFailure] = []
            await _collect_with_plan(plan, instance, "", failures)
            if failures:
                raise ValidationException(failures)

        return instance
