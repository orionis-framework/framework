from __future__ import annotations
from dataclasses import dataclass, field
from orionis.schemas.meta.constraint import ConstraintMetadata
from orionis.schemas.rules.accepted import Accepted
from orionis.schemas.rules.active_url import ActiveUrl
from orionis.schemas.rules.after import After
from orionis.schemas.rules.after_or_equal import AfterOrEqual
from orionis.schemas.rules.alpha import Alpha
from orionis.schemas.rules.ascii import Ascii
from orionis.schemas.rules.before import Before
from orionis.schemas.rules.before_or_equal import BeforeOrEqual
from orionis.schemas.rules.between import Between
from orionis.schemas.rules.confirm_password import ConfirmPassword
from orionis.schemas.rules.date_format import DateFormat
from orionis.schemas.rules.decimal_places import DecimalPlaces
from orionis.schemas.rules.different import Different
from orionis.schemas.rules.dimensions import Dimensions
from orionis.schemas.rules.doesnt_end_with import DoesntEndWith
from orionis.schemas.rules.doesnt_start_with import DoesntStartWith
from orionis.schemas.rules.email import Email
from orionis.schemas.rules.encoding import Encoding
from orionis.schemas.rules.ends_with import EndsWith
from orionis.schemas.rules.file import File
from orionis.schemas.rules.greater_than_or_equal_field import GreaterThanOrEqualField
from orionis.schemas.rules.image import Image
from orionis.schemas.rules.integer import Integer
from orionis.schemas.rules.ip_address import IpAddress
from orionis.schemas.rules.json_string import Json
from orionis.schemas.rules.less_than_or_equal_field import LessThanOrEqualField
from orionis.schemas.rules.lowercase import Lowercase
from orionis.schemas.rules.mac_address import MacAddress
from orionis.schemas.rules.max_digits import MaxDigits
from orionis.schemas.rules.mime_types import MimeTypes
from orionis.schemas.rules.size import Size
from orionis.schemas.rules.starts_with import StartsWith
from orionis.schemas.rules.strong_password import StrongPassword
from orionis.schemas.rules.ulid import Ulid
from orionis.schemas.rules.unique import Unique
from orionis.schemas.rules.uppercase import Uppercase
from orionis.schemas.rules.uuid_string import Uuid

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
    "Accepted",
    "ActiveUrl",
    "After",
    "AfterOrEqual",
    "Alpha",
    "Ascii",
    "Before",
    "BeforeOrEqual",
    "Between",
    "ConfirmPassword",
    "DateFormat",
    "DecimalPlaces",
    "Different",
    "Dimensions",
    "DoesntEndWith",
    "DoesntStartWith",
    "Email",
    "Encoding",
    "EndsWith",
    "File",
    "GreaterThan",
    "GreaterThanOrEqual",
    "GreaterThanOrEqualField",
    "Image",
    "Integer",
    "IpAddress",
    "Json",
    "LessThan",
    "LessThanOrEqual",
    "LessThanOrEqualField",
    "Lowercase",
    "MacAddress",
    "MaxDigits",
    "MaxLength",
    "MimeTypes",
    "MinLength",
    "MultipleOf",
    "Pattern",
    "Size",
    "StartsWith",
    "StrongPassword",
    "TimezoneAware",
    "TimezoneNaive",
    "Ulid",
    "Unique",
    "Uppercase",
    "Uuid",
]
