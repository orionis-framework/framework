from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
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

__all__ = [
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
    "GreaterThanOrEqualField",
    "Image",
    "Integer",
    "IpAddress",
    "Json",
    "LessThanOrEqualField",
    "Lowercase",
    "MacAddress",
    "MaxDigits",
    "MimeTypes",
    "Size",
    "StartsWith",
    "StrongPassword",
    "Ulid",
    "Unique",
    "Uppercase",
    "Uuid",
]

_EXPORTS = {
    "Accepted": ("orionis.schemas.rules.accepted", "Accepted"),
    "ActiveUrl": ("orionis.schemas.rules.active_url", "ActiveUrl"),
    "After": ("orionis.schemas.rules.after", "After"),
    "AfterOrEqual": ("orionis.schemas.rules.after_or_equal", "AfterOrEqual"),
    "Alpha": ("orionis.schemas.rules.alpha", "Alpha"),
    "Ascii": ("orionis.schemas.rules.ascii", "Ascii"),
    "Before": ("orionis.schemas.rules.before", "Before"),
    "BeforeOrEqual": ("orionis.schemas.rules.before_or_equal", "BeforeOrEqual"),
    "Between": ("orionis.schemas.rules.between", "Between"),
    "ConfirmPassword": ("orionis.schemas.rules.confirm_password", "ConfirmPassword"),
    "DateFormat": ("orionis.schemas.rules.date_format", "DateFormat"),
    "DecimalPlaces": ("orionis.schemas.rules.decimal_places", "DecimalPlaces"),
    "Different": ("orionis.schemas.rules.different", "Different"),
    "Dimensions": ("orionis.schemas.rules.dimensions", "Dimensions"),
    "DoesntEndWith": ("orionis.schemas.rules.doesnt_end_with", "DoesntEndWith"),
    "DoesntStartWith": ("orionis.schemas.rules.doesnt_start_with", "DoesntStartWith"),
    "Email": ("orionis.schemas.rules.email", "Email"),
    "Encoding": ("orionis.schemas.rules.encoding", "Encoding"),
    "EndsWith": ("orionis.schemas.rules.ends_with", "EndsWith"),
    "File": ("orionis.schemas.rules.file", "File"),
    "GreaterThanOrEqualField": ("orionis.schemas.rules.greater_than_or_equal_field", "GreaterThanOrEqualField"),
    "Image": ("orionis.schemas.rules.image", "Image"),
    "Integer": ("orionis.schemas.rules.integer", "Integer"),
    "IpAddress": ("orionis.schemas.rules.ip_address", "IpAddress"),
    "Json": ("orionis.schemas.rules.json_string", "Json"),
    "LessThanOrEqualField": ("orionis.schemas.rules.less_than_or_equal_field", "LessThanOrEqualField"),
    "Lowercase": ("orionis.schemas.rules.lowercase", "Lowercase"),
    "MacAddress": ("orionis.schemas.rules.mac_address", "MacAddress"),
    "MaxDigits": ("orionis.schemas.rules.max_digits", "MaxDigits"),
    "MimeTypes": ("orionis.schemas.rules.mime_types", "MimeTypes"),
    "Size": ("orionis.schemas.rules.size", "Size"),
    "StartsWith": ("orionis.schemas.rules.starts_with", "StartsWith"),
    "StrongPassword": ("orionis.schemas.rules.strong_password", "StrongPassword"),
    "Ulid": ("orionis.schemas.rules.ulid", "Ulid"),
    "Unique": ("orionis.schemas.rules.unique", "Unique"),
    "Uppercase": ("orionis.schemas.rules.uppercase", "Uppercase"),
    "Uuid": ("orionis.schemas.rules.uuid_string", "Uuid"),
}

def __getattr__(name: str) -> object:
    """Resolve and cache a public schema rule.

    Parameters
    ----------
    name : str
        Name requested from this package.

    Returns
    -------
    object
        Rule class from its defining module.

    Raises
    ------
    AttributeError
        If the requested name is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """List loaded attributes and public schema rules.

    Returns
    -------
    list[str]
        Sorted names visible on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
