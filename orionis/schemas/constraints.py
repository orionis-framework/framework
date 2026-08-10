from __future__ import annotations
from dataclasses import dataclass, field
from orionis.schemas.meta.constraint import ConstraintMetadata
from orionis.schemas.rules.email import Email
from orionis.schemas.rules.strong_password import StrongPassword

# ---------------------------------------------------------------------------
# Numeric constraints
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GreaterThan(ConstraintMetadata):
    """
    Assert that a numeric value is *strictly* greater than ``value``.

    Parameters
    ----------
    value : int | float
        The exclusive lower bound.
    message : str | None
        Reserved for a future custom validation error message.
    """

    value: int | float
    message: str | None = field(default=None, kw_only=True)

@dataclass(frozen=True, slots=True)
class GreaterThanOrEqual(ConstraintMetadata):
    """
    Assert that a numeric value is greater than or equal to ``value``.

    Parameters
    ----------
    value : int | float
        The inclusive lower bound.
    message : str | None
        Reserved for a future custom validation error message.
    """

    value: int | float
    message: str | None = field(default=None, kw_only=True)

@dataclass(frozen=True, slots=True)
class LessThan(ConstraintMetadata):
    """
    Assert that a numeric value is *strictly* less than ``value``.

    Parameters
    ----------
    value : int | float
        The exclusive upper bound.
    message : str | None
        Reserved for a future custom validation error message.
    """

    value: int | float
    message: str | None = field(default=None, kw_only=True)

@dataclass(frozen=True, slots=True)
class LessThanOrEqual(ConstraintMetadata):
    """
    Assert that a numeric value is less than or equal to ``value``.

    Parameters
    ----------
    value : int | float
        The inclusive upper bound.
    message : str | None
        Reserved for a future custom validation error message.
    """

    value: int | float
    message: str | None = field(default=None, kw_only=True)

@dataclass(frozen=True, slots=True)
class MultipleOf(ConstraintMetadata):
    """
    Assert that a numeric value is a multiple of ``value``.

    Parameters
    ----------
    value : int | float
        The divisor; the field value must be evenly divisible by this.
    message : str | None
        Reserved for a future custom validation error message.
    """

    value: int | float
    message: str | None = field(default=None, kw_only=True)

# ---------------------------------------------------------------------------
# String / collection constraints
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Pattern(ConstraintMetadata):
    """
    Assert that a string value matches the given ``regex`` pattern.

    Parameters
    ----------
    regex : str
        A regular expression that the field value must fully match.
    message : str | None
        Reserved for a future custom validation error message.
    """

    regex: str
    message: str | None = field(default=None, kw_only=True)

@dataclass(frozen=True, slots=True)
class MinLength(ConstraintMetadata):
    """
    Assert that a string or collection has at least ``value`` characters/items.

    Parameters
    ----------
    value : int
        The minimum allowed length (inclusive).
    message : str | None
        Reserved for a future custom validation error message.
    """

    value: int
    message: str | None = field(default=None, kw_only=True)

@dataclass(frozen=True, slots=True)
class MaxLength(ConstraintMetadata):
    """
    Assert that a string or collection has at most ``value`` characters/items.

    Parameters
    ----------
    value : int
        The maximum allowed length (inclusive).
    message : str | None
        Reserved for a future custom validation error message.
    """

    value: int
    message: str | None = field(default=None, kw_only=True)

# ---------------------------------------------------------------------------
# Temporal constraints
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TimezoneAware(ConstraintMetadata):
    """
    Assert timezone-awareness on a ``datetime.datetime`` or ``datetime.time``.

    Requires the annotated value to carry explicit timezone information.

    Parameters
    ----------
    message : str | None
        Reserved for a future custom validation error message.
    """

    message: str | None = field(default=None, kw_only=True)

@dataclass(frozen=True, slots=True)
class TimezoneNaive(ConstraintMetadata):
    """
    Assert timezone-naivety on a ``datetime.datetime`` or ``datetime.time``.

    Requires the annotated value to have *no* timezone information.

    Parameters
    ----------
    message : str | None
        Reserved for a future custom validation error message.
    """

    message: str | None = field(default=None, kw_only=True)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "Email",
    "GreaterThan",
    "GreaterThanOrEqual",
    "LessThan",
    "LessThanOrEqual",
    "MaxLength",
    "MinLength",
    "MultipleOf",
    "Pattern",
    "StrongPassword",
    "TimezoneAware",
    "TimezoneNaive",
]
