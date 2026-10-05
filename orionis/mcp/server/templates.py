import inspect
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import unquote
from uri_template import URITemplate

if TYPE_CHECKING:
    from orionis.mcp.server.primitives import Resource

_VARNAME = r"(?:\w|%[0-9A-Fa-f]{2})++(?:\.(?:\w|%[0-9A-Fa-f]{2})++)*+"
_MODIFIER = r"(?::[1-9]\d{0,3}|\*)?"
_EXPRESSION = re.compile(
    rf"[+#./;?&]?{_VARNAME}{_MODIFIER}(?:,{_VARNAME}{_MODIFIER})*+",
    re.ASCII,
)
_SIMPLE = re.compile(_VARNAME, re.ASCII)
_PART = re.compile(r"\{([^{}]*)\}")
_INVALID_LITERAL = re.compile(
    r'[\x00-\x20\x7f"<>\\^`{}]|%(?![0-9A-Fa-f]{2})|[\ud800-\udfff]',
)
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_ESCAPE = re.compile(r"%[0-9a-fA-F]{2}")

def _uppercase_escape(match: re.Match[str]) -> str:
    """
    Normalize the hexadecimal digits of one percent escape.

    Parameters
    ----------
    match : re.Match[str]
        Matched percent escape.

    Returns
    -------
    str
        Escape with uppercase hexadecimal digits.
    """
    return match[0].upper()

def _decode_captures(
    captures: tuple[str, ...], groups: tuple[str, ...],
) -> dict[str, object] | None:
    """
    Decode URI variables while checking repeated variable consistency.

    Parameters
    ----------
    captures : tuple[str, ...]
        Variable names in capture order.
    groups : tuple[str, ...]
        Values captured by the compiled inverse pattern.

    Returns
    -------
    dict[str, object] | None
        Decoded variables, or None when repeated variables disagree.
    """
    values: dict[str, object] = {}
    for name, value in zip(captures, groups, strict=True):
        decoded = unquote(value, encoding="utf-8", errors="strict")
        if name in values and values[name] != decoded:
            return None
        values[name] = decoded
    return values

def validate_uri(uri: str) -> None:
    """
    Require an absolute URI without malformed escapes or literal controls.

    Parameters
    ----------
    uri : str
        Value supplied for ``uri``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if (
        not isinstance(uri, str)
        or not _SCHEME.match(uri)
        or _INVALID_LITERAL.search(uri)
    ):
        message = "MCP resource URIs must be valid absolute URIs."
        raise ValueError(message)

def _validate_template(template: str) -> None:
    """
    Accept RFC 6570 syntax while excluding the dependency's draft extensions.

    Parameters
    ----------
    template : str
        Value supplied for ``template``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    position = 0
    for match in _PART.finditer(template):
        if _INVALID_LITERAL.search(
            template[position : match.start()],
        ) or not _EXPRESSION.fullmatch(match[1]):
            message = f"Invalid RFC 6570 URI template {template!r}."
            raise ValueError(message)
        position = match.end()
    if _INVALID_LITERAL.search(template[position:]) or not _SCHEME.match(template):
        message = f"Invalid absolute RFC 6570 URI template {template!r}."
        raise ValueError(message)

def _simple_pattern(template: str) -> tuple[re.Pattern[str], tuple[str, ...]] | None:
    """
    Compile safe simple-string inverses; other expressions need a match hook.

    Parameters
    ----------
    template : str
        Value supplied for ``template``.

    Returns
    -------
    tuple[re.Pattern[str], tuple[str, ...]] | None
        Result of the operation described above.
    """
    pieces: list[str] = []
    names: list[str] = []
    position = 0
    for match in _PART.finditer(template):
        literal = template[position : match.start()]
        if not _SIMPLE.fullmatch(match[1]) or (
            names and not any(separator in literal for separator in "/?#&;")
        ):
            return None
        pieces.extend((re.escape(literal), r"([^/?#&;]*)"))
        names.append(match[1])
        position = match.end()
    pieces.append(re.escape(template[position:]))
    return re.compile("".join(pieces)), tuple(names)

@dataclass(frozen=True, slots=True)
class UriMatcher:
    """Compile expansion once and verify every inverse result by expansion."""

    template: str
    variable_names: tuple[str, ...]
    expander: URITemplate
    pattern: re.Pattern[str] | None
    captures: tuple[str, ...]
    custom: Callable[[str], Mapping[str, object] | None] | None

    @classmethod
    def compile(cls, definition: type[Resource]) -> UriMatcher:
        """
        Require an explicit inverse for RFC operators with ambiguous matching.

        Parameters
        ----------
        definition : type[Resource]
            Class declaration whose metadata is being inspected.

        Returns
        -------
        UriMatcher
            Result of the operation described above.
        """
        template = definition.uri_template
        _validate_template(template)
        expander = URITemplate(template)
        custom = None
        if hasattr(definition, "match"):
            descriptor = inspect.getattr_static(definition, "match")
            if not isinstance(descriptor, (classmethod, staticmethod)):
                message = "Resource.match must be a staticmethod or classmethod."
                raise TypeError(message)
            custom = descriptor.__get__(None, definition)
            if (
                inspect.iscoroutinefunction(custom)
                or len(inspect.signature(custom).parameters) != 1
            ):
                message = "Resource.match must synchronously accept exactly one URI."
                raise TypeError(message)
        simple = _simple_pattern(template)
        if custom is None and simple is None:
            message = (
                "This RFC 6570 template needs an explicit Resource.match(uri) inverse."
            )
            raise ValueError(message)
        pattern, captures = simple if simple is not None else (None, ())
        return cls(
            template,
            tuple(expander.variable_names),
            expander,
            pattern,
            captures,
            custom,
        )

    def match(self, uri: str) -> dict[str, object] | None:
        """
        Return validated URI variables without loading any resource or file.

        Parameters
        ----------
        uri : str
            Value supplied for ``uri``.

        Returns
        -------
        dict[str, object] | None
            Validated URI variables without loading any resource or file.
        """
        validate_uri(uri)
        if self.custom is not None:
            values = self.custom(uri)
            if values is None:
                return None
            if not isinstance(values, Mapping) or not set(
                self.variable_names,
            ).issuperset(values):
                message = "Resource.match must return only declared URI variables."
                raise ValueError(message)
            values = dict(values)
        else:
            pattern = self.pattern
            if pattern is None:
                message = "A compiled URI matcher has no inverse implementation."
                raise RuntimeError(message)
            match = pattern.fullmatch(uri)
            if match is None:
                return None
            values = _decode_captures(self.captures, match.groups())
            if values is None:
                return None
        expanded = self.expander.expand(**values)
        if _ESCAPE.sub(_uppercase_escape, expanded) != _ESCAPE.sub(
            _uppercase_escape, uri,
        ):
            return None
        return values
