from __future__ import annotations
from typing import TYPE_CHECKING
import msgspec
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.failure_collector import FailureCollector
from orionis.schemas.rules_executor import (
    _async_cache_get,
    _build_plan,
    _cache_get,
    _collect_with_async_plan,
    _collect_with_plan,
)

if TYPE_CHECKING:
    from orionis.schemas.schema import Schema as SchemaType

# Alias msgspec's convert function to avoid direct dependency on msgspec in the
# rest of the codebase.
_convert = msgspec.convert

# Alias msgspec's ValidationError to avoid direct
# dependency on msgspec in the rest of the codebase.
_ValidationError = msgspec.ValidationError

class Schema:

    # Prevent per-instance dictionaries; the class is used statically.
    __slots__ = ()

    @staticmethod
    def validate(payload: object, schema: type[SchemaType]) -> SchemaType:
        """
        Validate payload against a schema and return a typed instance.

        Parameters
        ----------
        payload : object
            Input data to convert and validate.
        schema : type[Schema]
            Schema class used for conversion and rule validation.

        Returns
        -------
        Schema
            Converted schema instance.

        Raises
        ------
        ValidationException
            If payload conversion fails or schema rules raise validation
            errors. The exception carries every failure found, indexed by
            field name.
        """
        # Convert the payload into a schema instance using msgspec. A single
        # C-level call handles the successful path; only when it fails is the
        # payload re-inspected field by field to report every error.
        try:
            instance = _convert(payload, type=schema)

        # Catch msgspec validation errors and re-raise them as framework exceptions.
        except _ValidationError as exc:
            raise ValidationException(
                FailureCollector.collect(payload, schema, exc),
            ) from exc

        # Use the known schema type directly — avoids a redundant type(instance)
        # call. Skip execution entirely when the plan is empty (the common case
        # for simple schemas with no custom rules).
        plan = _cache_get(schema)
        if plan is None:
            plan = _build_plan(schema)
        if plan:
            failures: list = []
            _collect_with_plan(plan, instance, "", failures)
            if failures:
                raise ValidationException(failures)

        return instance

    @staticmethod
    async def validateAsync(payload: object, schema: type[SchemaType]) -> SchemaType:
        """
        Validate a payload while awaiting rules that require native I/O.

        Parameters
        ----------
        payload : object
            Input data to convert and validate.
        schema : type[Schema]
            Schema class with precompiled conversion and rule metadata.

        Returns
        -------
        Schema
            Converted instance after all applicable rules succeed.

        Raises
        ------
        ValidationException
            If conversion or synchronous or asynchronous rules reject fields.
        """
        plan = _cache_get(schema)
        if plan is None:
            plan = _build_plan(schema)
        async_plan = _async_cache_get(schema)
        try:
            instance = _convert(payload, type=schema)
        except _ValidationError as exc:
            conversion_failures = (
                await FailureCollector.collectAsync(payload, schema, exc)
                if async_plan else FailureCollector.collect(payload, schema, exc)
            )
            raise ValidationException(conversion_failures) from exc
        if plan:
            failures: list = []
            if async_plan:
                await _collect_with_async_plan(async_plan, instance, "", failures)
            else:
                _collect_with_plan(plan, instance, "", failures)
            if failures:
                raise ValidationException(failures)
        return instance
