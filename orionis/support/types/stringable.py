# ruff: noqa: PLC0415, PLR2004, FBT001, DTZ007
# Facades load lazily; positional flags and numeric modes are public contracts.
# Parsed naive dates receive the configured timezone before being returned.
"""Provide chainable operations over a string value."""

from __future__ import annotations
import base64
import fnmatch
import hashlib
import html
import json
import re
import textwrap
import unicodedata
import urllib.parse
import uuid
from collections.abc import Callable, Iterable
from datetime import datetime
from pathlib import Path
from typing import Self
from orionis.support.types._html import _TagStripper

# Word separators shared by camel-case and StudlyCase conversion.
_RE_CAMEL_SEP = re.compile(r"[_\-\s]+")
"""Word separators shared by camel-case and StudlyCase conversion."""
_RE_KEBAB_CAMEL = re.compile(r"([a-z0-9])([A-Z])")
"""Boundary between a lowercase letter or digit and an uppercase letter."""
_RE_KEBAB_SEP = re.compile(r"[_\s]+")
"""Whitespace and underscore runs replaced by kebab-case separators."""
_RE_KEBAB_MULTI = re.compile(r"-+")
"""Repeated dashes collapsed during kebab-case conversion."""
_RE_SQUISH = re.compile(r"\s+")
"""Whitespace runs collapsed by squish."""
_RE_NUMBERS = re.compile(r"\D")
"""Characters excluded by numeric-character extraction."""
_RE_HEADLINE = re.compile(r"\b\w+\b")
"""Word tokens used to construct headline case."""
_RE_UCSPLIT = re.compile(r"[A-Z][a-z]*|[a-z]+|\d+")
"""Uppercase-led words, lowercase words and digit runs for ucsplit."""
_RE_PASCAL_WORDS = re.compile(r"[A-Z][a-z]*|[a-z]+")
"""Word segments used by PascalCase pluralization."""
_ULID_RE = re.compile(r"[0-7][0123456789ABCDEFGHJKMNPQRSTVWXYZ]{25}")
"""Crockford Base32 encoding constrained to the 128-bit ULID range."""
_INTEGER_LIMIT_ERROR = "Limit must be an integer."
"""Validation message shared by non-integer limit arguments."""


class Stringable(str):
    """Provide chainable operations over a string value."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def after(self: Self, search: str) -> Stringable:
        """
        Return the substring after the first occurrence of a value.

        Parameters
        ----------
        search : str
            Substring to search for in the current string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable containing the substring after the first occurrence
            of the search string, or the original string if not found.
        """
        # Find the index of the first occurrence of the search string
        idx = self.find(search)
        # Return substring after the search string if found, else original string
        return Stringable(self[idx + len(search) :]) if idx != -1 else Stringable(self)

    def afterLast(self: Self, search: str) -> Stringable:
        """
        Return the substring after the last occurrence of a value.

        Parameters
        ----------
        search : str
            Substring to search for within the current string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable containing the substring after the last occurrence of
            the search string, or the original string if not found.
        """
        # Find the index of the last occurrence of the search string
        idx = self.rfind(search)
        # Return substring after the search string if found, else original string
        return Stringable(self[idx + len(search) :]) if idx != -1 else Stringable(self)

    def append(self: Self, *values: str) -> Stringable:
        """
        Append one or more string values to the end of the string.

        Parameters
        ----------
        values : str
            One or more string values to append.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with all provided values appended.
        """
        # Ensure all values are strings before appending
        for value in values:
            if not isinstance(value, str):
                error_msg = "All values to append must be strings."
                raise TypeError(error_msg)
        # Concatenate all provided values to the current string
        return Stringable(self + "".join(values))

    def newLine(self: Self, count: int = 1) -> Stringable:
        """
        Append newline characters to the end of the string.

        Parameters
        ----------
        count : int, optional
            Number of newline characters to append. Default is 1.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with the specified number of newline
            characters appended.
        """
        # Append the specified number of newline characters to the string
        return Stringable(str(self) + "\n" * count)

    def before(self: Self, search: str) -> Stringable:
        """
        Return the substring before the first occurrence of a value.

        Parameters
        ----------
        search : str
            Substring to search for within the current string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance containing the substring before the first
            occurrence of the search string, or the original string if not found.
        """
        # Find the index of the first occurrence of the search string.
        idx = self.find(search)
        # Return substring before the search string if found, else original string.
        return Stringable(self[:idx]) if idx != -1 else Stringable(self)

    def beforeLast(self: Self, search: str) -> Stringable:
        """
        Return the substring before the last occurrence of a value.

        Searches for the last occurrence of the specified substring and returns
        everything before it. If the substring is not found, returns the original
        string unchanged.

        Parameters
        ----------
        search : str
            Substring to search for within the current string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance containing the substring before the last
            occurrence of the search string, or the original string if not found.
        """
        # Find the index of the last occurrence of the search string
        idx = self.rfind(search)
        # Return substring before the search string if found, else original string
        return Stringable(self[:idx]) if idx != -1 else Stringable(self)

    def contains(
        self: Self,
        needles: str | Iterable[str],
        *,
        ignore_case: bool = False,
    ) -> bool:
        """
        Check if the string contains any of the given values.

        Parameters
        ----------
        needles : str | collections.abc.Iterable[str]
            Value or values to search for within the string.
        ignore_case : bool, optional
            If True, perform case-insensitive search. Default is False.

        Returns
        -------
        bool
            True if the string contains any of the needle values, otherwise False.

        Raises
        ------
        TypeError
            If needles is not a string or an iterable of strings.
        """
        # Validate that needles is a string or an iterable of strings
        if not isinstance(needles, str) and not isinstance(needles, Iterable):
            error_msg = "Needles must be a string or an iterable of strings."
            raise TypeError(error_msg)

        # Normalize needles to a list of strings
        if isinstance(needles, str):
            needles = [needles]

        # Prepare string for case-insensitive comparison if needed.
        # Select the comparison for the requested case sensitivity.
        if ignore_case:
            s = self.lower()
            return any(needle.lower() in s for needle in needles)
        return any(needle in self for needle in needles)

    def endsWith(self: Self, needles: str | Iterable[str]) -> bool:
        """
        Determine if the string ends with any of the given substrings.

        Parameters
        ----------
        needles : str | collections.abc.Iterable[str]
            Substring or substrings to check at the end of the string.

        Returns
        -------
        bool
            True if the string ends with any of the needle values, otherwise False.
        """
        # Validate that needles is a string or an iterable of strings
        if not isinstance(needles, str) and not isinstance(needles, Iterable):
            error_msg = "Needles must be a string or an iterable of strings."
            raise TypeError(error_msg)
        # Normalize needles to a list of strings
        if isinstance(needles, str):
            needles = [needles]
        return any(str.endswith(self, needle) for needle in needles)

    def exactly(self: Self, value: str) -> bool:
        """
        Return True if the string exactly matches the given value.

        Parameters
        ----------
        value : str
            Value to compare against the current string.

        Returns
        -------
        bool
            True if the string exactly matches the given value, otherwise False.
        """
        # Ensure the value to compare is a string
        if not isinstance(value, str):
            error_msg = "Value must be a string for exact comparison."
            raise TypeError(error_msg)

        # self is a str subclass; == delegates to str.__eq__ directly.
        return self == value

    def isEmpty(self: Self) -> bool:
        """
        Check if the string is empty.

        Returns
        -------
        bool
            True if the string has zero length, otherwise False.
        """
        # str.__bool__ returns True iff len > 0; no len() call needed.
        return not self

    def isNotEmpty(self: Self) -> bool:
        """
        Return True if the string is not empty.

        Returns
        -------
        bool
            True if the string contains one or more characters, otherwise False.
        """
        return bool(self)

    def lower(self: Self) -> Stringable:
        """
        Convert to lowercase.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with all characters in lowercase.
        """
        # Convert all characters to lowercase using the built-in method
        return Stringable(super().lower())

    def upper(self: Self) -> Stringable:
        """
        Convert all characters to uppercase.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with all characters in uppercase.
        """
        # Convert all characters to uppercase using the built-in method
        return Stringable(super().upper())

    def reverse(self: Self) -> Stringable:
        """
        Reverse the string.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with characters in reverse order.
        """
        # Return the reversed string using slicing
        return Stringable(self[::-1])

    def repeat(self: Self, times: int) -> Stringable:
        """
        Repeat the string a specified number of times.

        Parameters
        ----------
        times : int
            Number of times to repeat the string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with the string repeated the specified
            number of times.
        """
        # Validate that times is a non-negative integer
        if not isinstance(times, int) or times < 0:
            error_msg = "Times must be a non-negative integer."
            raise ValueError(error_msg)
        # Repeat the string using multiplication
        return Stringable(self * times)

    def replace(
        self: Self,
        search: str | Iterable[str],
        replace: str | Iterable[str],
        *,
        case_sensitive: bool = True,
    ) -> Stringable:
        """
        Replace occurrences of substrings with replacements.

        Parameters
        ----------
        search : str | collections.abc.Iterable[str]
            Substring(s) to search for in the string.
        replace : str | collections.abc.Iterable[str]
            Replacement string(s) for each search substring.
        case_sensitive : bool, optional
            If True, perform case-sensitive replacement. Default is True.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with the specified replacements applied.
        """
        # Start with the original string
        s = self

        # Validate that search is a string or an iterable of strings
        if not isinstance(search, str) and not isinstance(search, Iterable):
            error_msg = "Search must be a string or an iterable of strings."
            raise TypeError(error_msg)
        if isinstance(search, str):
            search = [search]

        # Validate that replace is a string or an iterable of strings
        if not isinstance(replace, str) and not isinstance(replace, Iterable):
            error_msg = "Replace must be a string or an iterable of strings."
            raise TypeError(error_msg)
        if isinstance(replace, str):
            replace = [replace]

        # Replace each search substring with the corresponding replacement
        for src, rep in zip(search, replace, strict=True):
            if case_sensitive:
                s = str(s).replace(src, rep)
            else:
                s = re.sub(
                    re.escape(src),
                    lambda _match, rep=rep: rep,
                    str(s),
                    flags=re.IGNORECASE,
                )

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def stripTags(self: Self, allowed_tags: str | None = None) -> Stringable:
        """
        Remove HTML and PHP tags from the string.

        Parameters
        ----------
        allowed_tags : str | None, optional
            Tags to preserve, such as "<p><b>". Default is None. When nonempty,
            recognized HTML entities in text are decoded.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with tags removed. Allowed tag attributes
            and element text are preserved; this operation is not an HTML sanitizer.
        """
        if allowed_tags is not None and not isinstance(allowed_tags, str):
            message = "Allowed tags must be a string or None."
            raise TypeError(message)
        allowed = frozenset(
            re.findall(r"<\s*([a-zA-Z][a-zA-Z0-9:-]*)\s*>", allowed_tags or ""),
        )
        parser = _TagStripper(frozenset(tag.lower() for tag in allowed))
        parser.feed(str(self))
        parser.close()
        return Stringable("".join(parser.parts))

    def toBase64(self: Self) -> Stringable:
        """
        Encode the string as Base64.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance containing the Base64-encoded string.
        """
        # Encode the string to Base64 and decode to string
        return Stringable(base64.b64encode(str(self).encode()).decode())

    def fromBase64(self: Self, *, strict: bool = False) -> Stringable:
        """
        Decode the string from Base64.

        Parameters
        ----------
        strict : bool, optional
            If True, raise an exception on decode errors. Default is False.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with Base64-decoded content. If decoding fails
            and strict is False, returns an empty Stringable.
        """
        # Validate that strict is a boolean
        if not isinstance(strict, bool):
            error_msg = "The 'strict' parameter must be a boolean."
            raise TypeError(error_msg)

        # Attempt to decode the string from Base64
        try:
            return Stringable(base64.b64decode(str(self).encode()).decode())
        except ValueError as exc:
            if strict:
                error_msg = f"Base64 decoding failed: {exc!s}"
                raise RuntimeError(error_msg) from exc

            # Return empty string if decoding fails and strict is False
            return Stringable("")

    def md5(self: Self) -> str:
        """
        Compute the MD5 hash of the string.

        Returns
        -------
        str
            Hexadecimal string representing the MD5 hash of the input string.
        """
        # Compute the MD5 hash using hashlib and return as a hex string
        return hashlib.md5(str(self).encode(), usedforsecurity=False).hexdigest()

    def sha1(self: Self) -> str:
        """
        Compute the SHA1 hash of the string.

        Returns
        -------
        str
            Hexadecimal string representing the SHA1 hash of the input string.
        """
        # Compute the SHA1 hash using hashlib and return as a hex string
        return hashlib.sha1(str(self).encode(), usedforsecurity=False).hexdigest()

    def sha256(self: Self) -> str:
        """
        Generate a SHA256 hash of the string.

        Returns
        -------
        str
            Hexadecimal string representing the SHA256 hash of the input string.
        """
        # Compute the SHA256 hash using hashlib and return as a hex string
        return hashlib.sha256(str(self).encode()).hexdigest()

    def length(self: Self) -> int:
        """
        Return the number of characters in the string.

        Returns
        -------
        int
            Number of characters in the string.
        """
        # Return the length of the string
        return len(self)

    def value(self: Self) -> str:
        """
        Return the string value.

        Returns
        -------
        str
            String representation of the current instance.
        """
        # Return the string representation of this object
        return str(self)

    def toInteger(self: Self, base: int = 10) -> int:
        """
        Convert the string to an integer.

        Parameters
        ----------
        base : int, optional
            The base for conversion. Default is 10.

        Returns
        -------
        int
            Integer representation of the string.

        Raises
        ------
        ValueError
            If the string cannot be converted to an integer.
        """
        # Attempt to convert the string to an integer using the specified base
        try:
            return int(self, base)
        except ValueError as exc:
            error_msg = f"Cannot convert string to integer: {exc!s}"
            raise ValueError(error_msg) from exc

    def toFloat(self: Self) -> float:
        """
        Convert the string to a float.

        Returns
        -------
        float
            Float representation of the string.

        Raises
        ------
        ValueError
            If the string cannot be converted to a float.
        """
        # Attempt to convert the string to a float
        try:
            return float(self)
        except ValueError as exc:
            error_msg = f"Cannot convert string to float: {exc!s}"
            raise ValueError(error_msg) from exc

    def toBoolean(self: Self) -> bool:
        """
        Convert to a boolean value.

        The string is considered True if it matches common truthy values such as
        "1", "true", "on", or "yes" (case-insensitive).

        Returns
        -------
        bool
            True if the string represents a truthy value, otherwise False.
        """
        # Check for common truthy values after stripping and lowering the string
        return str(self).strip().lower() in ("1", "true", "on", "yes")

    def __getitem__(self: Self, key: int | slice) -> Stringable:
        """
        Return a substring or character by index or slice.

        Parameters
        ----------
        key : int or slice
            Index or slice to retrieve.

        Returns
        -------
        orionis.support.types.Stringable
            Stringable instance for the selected item(s).
        """
        # Return a Stringable for the selected item(s)
        return Stringable(super().__getitem__(key))

    def __str__(self: Self) -> str:
        """
        Return the string representation of the object.

        Returns
        -------
        str
            String representation of the object.
        """
        # Use the parent class's __str__ method for string representation
        return super().__str__()

    def isAlnum(self: Self) -> bool:
        """
        Check if all characters are alphanumeric.

        Returns
        -------
        bool
            True if all characters in the string are alphanumeric, otherwise False.
        """
        return str.isalnum(self)

    def isAlpha(self: Self) -> bool:
        """
        Check if all characters in the string are alphabetic.

        Returns
        -------
        bool
            True if all characters are alphabetic, otherwise False.
        """
        return str.isalpha(self)

    def isDecimal(self: Self) -> bool:
        """
        Check if all characters in the string are decimal characters.

        Returns
        -------
        bool
            True if all characters are decimal, otherwise False.
        """
        return str.isdecimal(self)

    def isDigit(self: Self) -> bool:
        """
        Check if all characters are digits.

        Returns
        -------
        bool
            True if all characters in the string are digits, otherwise False.
        """
        return str.isdigit(self)

    def isIdentifier(self: Self) -> bool:
        """
        Check if the string is a valid Python identifier.

        Returns
        -------
        bool
            True if the string is a valid identifier, otherwise False.
        """
        return str.isidentifier(self)

    def isLower(self: Self) -> bool:
        """
        Check if all cased characters in the string are lowercase.

        Returns
        -------
        bool
            True if all cased characters are lowercase, otherwise False.
        """
        return str.islower(self)

    def isNumeric(self: Self) -> bool:
        """
        Check if all characters in the string are numeric.

        Returns
        -------
        bool
            True if all characters are numeric, otherwise False.
        """
        return str.isnumeric(self)

    def isPrintable(self: Self) -> bool:
        """
        Return True if all characters in the string are printable.

        Returns
        -------
        bool
            True if all characters are printable, otherwise False.
        """
        return str.isprintable(self)

    def isSpace(self: Self) -> bool:
        """
        Determine if the string contains only whitespace characters.

        Returns
        -------
        bool
            True if the string contains only whitespace characters, otherwise False.
        """
        return str.isspace(self)

    def isTitle(self: Self) -> bool:
        """
        Check if the string is titlecased.

        Returns
        -------
        bool
            True if the string is titlecased, otherwise False.
        """
        return str.istitle(self)

    def isUpper(self: Self) -> bool:
        """
        Check if all cased characters in the string are uppercase.

        Returns
        -------
        bool
            True if all cased characters are uppercase, otherwise False.
        """
        return str.isupper(self)

    def lStrip(self: Self, chars: str | None = None) -> Stringable:
        """
        Remove leading characters from the string.

        Parameters
        ----------
        chars : str | None, optional
            Characters to remove from the beginning. If None, whitespace is removed.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with leading characters removed.
        """
        if chars is not None and not isinstance(chars, str):
            error_msg = "Chars must be a string or None."
            raise TypeError(error_msg)
        # Remove leading characters using Python's built-in lstrip
        return Stringable(str(self).lstrip(chars))

    def rStrip(self: Self, chars: str | None = None) -> Stringable:
        """
        Remove trailing characters from the string.

        Parameters
        ----------
        chars : str | None, optional
            Characters to remove from the end. If None, removes whitespace.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with trailing characters removed.
        """
        # Validate that chars is either a string or None
        if chars is not None and not isinstance(chars, str):
            error_msg = "Chars must be a string or None."
            raise TypeError(error_msg)
        # Remove trailing characters using rstrip
        return Stringable(str(self).rstrip(chars))

    def swapCase(self: Self) -> Stringable:
        """
        Swap the case of each character in the string.

        Converts uppercase characters to lowercase and lowercase characters to
        uppercase, leaving other characters unchanged.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with all character cases swapped.
        """
        # Use built-in swapcase to invert the case of all characters
        return Stringable(str(self).swapcase())

    def zFill(self: Self, width: int) -> Stringable:
        """
        Pad the string with leading zeros to a given width.

        Parameters
        ----------
        width : int
            Total width of the resulting string.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance padded with leading zeros.
        """
        if not isinstance(width, int) or width < 0:
            error_msg = "Width must be a non-negative integer."
            raise ValueError(error_msg)
        # Pad with zeros, preserving sign if present
        return Stringable(str(self).zfill(width))

    def ascii(self: Self) -> Stringable:
        """
        Transliterate to ASCII using Unicode normalization.

        Uses Unicode normalization to remove accents and non-ASCII characters.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance containing only ASCII characters.
        """
        # Normalize Unicode and discard non-ASCII code points.
        normalized = unicodedata.normalize("NFKD", self)
        ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
        return Stringable(ascii_str)

    def camel(self: Self) -> Stringable:
        """
        Convert the string to camel case.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance in camelCase.
        """
        # Split the string by common separators and normalize to words
        words = _RE_CAMEL_SEP.sub(" ", str(self)).split()
        if not words:
            return Stringable("")
        # Lowercase the first word, capitalize the rest, and join
        camel_str = words[0].lower() + "".join(word.capitalize() for word in words[1:])
        return Stringable(camel_str)

    def kebab(self: Self) -> Stringable:
        """
        Convert the string to kebab case.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance in kebab-case.
        """
        # Insert dash between lowercase/number and uppercase letters
        s = _RE_KEBAB_CAMEL.sub(r"\1-\2", str(self))
        # Replace spaces and underscores with dash, collapse multiple dashes
        s = _RE_KEBAB_SEP.sub("-", s)
        s = _RE_KEBAB_MULTI.sub("-", s)
        return Stringable(s.lower().strip("-"))

    def snake(self: Self, delimiter: str = "_") -> Stringable:
        """
        Convert the string to snake_case using the specified delimiter.

        Parameters
        ----------
        delimiter : str, optional
            Delimiter to use for separation, by default "_".

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance in snake_case.
        """
        # Insert delimiter between lowercase/number and uppercase letters
        s = re.sub(
            r"([a-z0-9])([A-Z])",
            lambda match: match[1] + delimiter + match[2],
            str(self),
        )
        # Replace spaces and dashes with the delimiter
        s = re.sub(r"[\s\-]+", lambda _match: delimiter, s)
        # Collapse multiple delimiters into one
        if not delimiter:
            return Stringable(s.lower())
        s = re.sub(rf"(?:{re.escape(delimiter)})+", lambda _match: delimiter, s)
        return Stringable(s.lower().strip(delimiter))

    def studly(self: Self) -> Stringable:
        """
        Convert to StudlyCase (PascalCase).

        Replaces underscores, hyphens, and spaces with spaces, splits into words,
        capitalizes each word, and joins them without separators.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance in StudlyCase.
        """
        # Replace separators with spaces, split into words, capitalize, and join
        words = _RE_CAMEL_SEP.sub(" ", str(self)).split()
        studly_str = "".join(word.capitalize() for word in words)
        return Stringable(studly_str)

    def pascal(self: Self) -> Stringable:
        """
        Convert the string to PascalCase.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance in PascalCase.
        """
        # Use studly() to convert to PascalCase (StudlyCase)
        return self.studly()

    def slug(
        self: Self,
        separator: str = "-",
        dictionary: dict[str, str] | None = None,
    ) -> Stringable:
        """
        Generate a URL-friendly slug from the string.

        Parameters
        ----------
        separator : str, optional
            Separator to use in the slug. Default is "-".
        dictionary : dict[str, str] | None, optional
            Dictionary for character replacements. Default is {"@": "at"}.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance containing the URL-friendly slug.
        """
        if not isinstance(separator, str):
            error_msg = "Separator must be a string."
            raise TypeError(error_msg)

        if dictionary is not None and not isinstance(dictionary, dict):
            error_msg = "Dictionary must be a dict or None."
            raise TypeError(error_msg)

        # Set default dictionary if not provided
        if dictionary is None:
            dictionary = {"@": "at"}

        s = str(self)

        # Replace characters using the dictionary
        for key, value in dictionary.items():
            s = s.replace(key, value)

        # Convert to ASCII for URL safety
        s = self.__class__(s).ascii().value()

        # Remove non-alphanumeric characters except spaces and separators
        s = re.sub(r"[^\w\s-]", "", s)

        # Replace spaces and underscores with the separator
        s = re.sub(r"[\s_]+", lambda _match: separator, s)

        # Collapse multiple separators into one
        if not separator:
            return Stringable(s.lower())
        s = re.sub(rf"(?:{re.escape(separator)})+", lambda _match: separator, s)

        # Return the slug in lowercase, stripped of leading/trailing separators
        return Stringable(s.lower().strip(separator))

    def title(self: Self) -> Stringable:
        """
        Convert the string to title case.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with each word capitalized.
        """
        # Capitalize the first letter of each word using the built-in title method
        return Stringable(str(self).title())

    def headline(self: Self) -> Stringable:
        """
        Convert to headline case.

        Splits the string into words and capitalizes the first letter of each
        word.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with each word capitalized.
        """
        # Split the string into words using word boundaries.
        words = _RE_HEADLINE.findall(str(self))
        # Capitalize the first letter of each word and join them with spaces.
        headline_str = " ".join(word.capitalize() for word in words)
        return Stringable(headline_str)

    def apa(self: Self) -> Stringable:
        """
        Convert to APA-style title case.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance in APA title case.
        """
        # Set of words not capitalized in APA style except at start or end
        lowercase_words = {
            "a",
            "an",
            "and",
            "as",
            "at",
            "but",
            "by",
            "for",
            "if",
            "in",
            "nor",
            "of",
            "on",
            "or",
            "so",
            "the",
            "to",
            "up",
            "yet",
        }
        words = str(self).split()
        apa_words = []
        for i, word in enumerate(words):
            # Capitalize first, last, words >= 4 chars, or not in lowercase_words
            if (
                i == 0
                or i == len(words) - 1
                or len(word) >= 4
                or word.lower() not in lowercase_words
            ):
                apa_words.append(word.capitalize())
            else:
                apa_words.append(word.lower())
        return Stringable(" ".join(apa_words))

    def ucfirst(self: Self) -> Stringable:
        """
        Capitalize the first character of the string.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with the first character in uppercase.
        """
        # Return self if string is empty, else capitalize first character
        if not self:
            return Stringable(self)
        return Stringable(self[0].upper() + self[1:])

    def lcfirst(self: Self) -> Stringable:
        """
        Convert the first character of the string to lowercase.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with the first character in lowercase.
        """
        # Return self if string is empty, else lowercase first character
        if not self:
            return Stringable(self)
        return Stringable(self[0].lower() + self[1:])

    def isAscii(self: Self) -> bool:
        """
        Check if the string contains only 7-bit ASCII characters.

        Returns
        -------
        bool
            True if the string is ASCII, otherwise False.
        """
        return str.isascii(self)

    def isJson(self: Self) -> bool:
        """
        Check if the string is valid JSON.

        Returns
        -------
        bool
            True if the string is valid JSON, otherwise False.
        """
        try:
            # Try to parse the string as JSON
            json.loads(str(self))
            return True
        except json.JSONDecodeError, TypeError:
            return False

    def isUrl(self: Self, protocols: list[str] | None = None) -> bool:
        """
        Determine if the string is a valid URL.

        Parameters
        ----------
        protocols : list[str] | None, optional
            List of allowed protocols. Defaults to ["http", "https"].

        Returns
        -------
        bool
            True if the string is a valid URL with an allowed protocol,
            otherwise False.
        """
        # Validate that protocols is a list of strings or None
        if protocols is not None and not isinstance(protocols, list):
            error_msg = "Protocols must be a list of strings or None."
            raise TypeError(error_msg)

        # Use default protocols if none provided
        if protocols is None:
            protocols = ["http", "https"]

        try:
            # scheme and netloc are non-empty strings when present
            result = urllib.parse.urlparse(str(self))
            return bool(result.scheme and result.netloc and result.scheme in protocols)
        except ValueError, AttributeError:
            return False

    def isUuid(self: Self, version: int | str | None = None) -> bool:
        """
        Determine if the string is a valid UUID.

        Parameters
        ----------
        version : int | str | None, optional
            UUID version to validate (1-8), or "max" for any version up to 8.
            If None, any valid UUID version is accepted.

        Returns
        -------
        bool
            True if the string is a valid UUID (and version, if specified),
            otherwise False.
        """
        # Validate the version parameter type
        if version is not None and not (
            isinstance(version, int) or (isinstance(version, str) and version == "max")
        ):
            error_msg = "Version must be an integer (1-8), 'max', or None."
            raise TypeError(error_msg)

        try:
            # Attempt to create a UUID object from the string
            uuid_obj = uuid.UUID(str(self))
            if version is not None:
                if version == "max":
                    # Accept any version up to 8
                    return uuid_obj.version <= 8
                return uuid_obj.version == int(version)
            return True
        except ValueError, TypeError:
            # Return False if the string is not a valid UUID
            return False

    def isUlid(self: Self) -> bool:
        """
        Check if the string is a valid ULID.

        Returns
        -------
        bool
            True if the string is a valid ULID, otherwise False.
        """
        # Validate the full 26-character Crockford Base32 identifier.
        return str.isascii(self) and _ULID_RE.fullmatch(self.upper()) is not None

    def chopStart(self: Self, needle: str | list[str]) -> Stringable:
        """
        Remove the given string(s) from the start if present.

        Parameters
        ----------
        needle : str | list[str]
            String or list of strings to remove from the start.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable with the needle removed from the start if present.
        """
        # Get the string representation
        s = str(self)

        # Normalize needle to a list for consistent processing
        if not isinstance(needle, str) and not isinstance(needle, Iterable):
            error_msg = "Needle must be a string or an iterable of strings."
            raise TypeError(error_msg)
        needles = [needle] if isinstance(needle, str) else list(needle)

        # Remove the first matching needle from the start
        for n in needles:
            if s.startswith(n):
                s = s[len(n) :]
                break

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def chopEnd(self: Self, needle: str | list[str]) -> Stringable:
        """
        Remove the given string(s) from the end if present.

        Parameters
        ----------
        needle : str | list[str]
            String or list of strings to remove from the end.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable with the needle removed from the end if present.
        """
        s = str(self)
        # Normalize needle to a list for consistent processing
        if not isinstance(needle, str) and not isinstance(needle, Iterable):
            error_msg = "Needle must be a string or an iterable of strings."
            raise TypeError(error_msg)
        needles = [needle] if isinstance(needle, str) else list(needle)
        # Remove the first matching needle from the end
        for n in needles:
            if s.endswith(n):
                s = s.removesuffix(n)
                break
        return Stringable(s)

    def deduplicate(self: Self, character: str = " ") -> Stringable:
        """
        Replace consecutive occurrences of a character with a single instance.

        Parameters
        ----------
        character : str, optional
            Single character string to deduplicate. Default is a space.

        Returns
        -------
        orionis.support.types.Stringable
            Stringable with consecutive characters replaced by a single instance.
        """
        if not isinstance(character, str) or len(character) != 1:
            error_msg = "Character must be a single character string."
            raise ValueError(error_msg)
        # Replace consecutive occurrences of the character with a single instance
        pattern = re.escape(character) + "+"
        return Stringable(re.sub(pattern, lambda _match: character, str(self)))

    def mask(
        self: Self,
        character: str,
        index: int,
        length: int | None = None,
    ) -> Stringable:
        """
        Mask a portion of the string with a repeated character.

        Parameters
        ----------
        character : str
            Character to use for masking.
        index : int
            Starting index for masking.
        length : int | None, optional
            Number of characters to mask. If None, mask to end of string.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable with the specified portion masked.
        """
        # Validate character is a single character string
        if not isinstance(character, str) or len(character) != 1:
            error_msg = "Character must be a single character string."
            raise ValueError(error_msg)

        # Validate index is an integer
        if not isinstance(index, int):
            error_msg = "Index must be an integer."
            raise TypeError(error_msg)

        # Validate length is an integer or None
        if length is not None and not isinstance(length, int):
            error_msg = "'Length' must be an integer or None."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Adjust negative index to count from end of string
        if index < 0:
            index = max(0, len(s) + index)

        # Determine length to mask
        if length is None:
            length = len(s) - index
        elif length < 0:
            length = max(0, len(s) + length - index)
        end_index = min(len(s), index + length)
        mask_str = character * (end_index - index)

        # Return string with masked portion
        return Stringable(s[:index] + mask_str + s[end_index:])

    def limit(
        self: Self,
        limit: int = 100,
        end: str = "...",
        *,
        preserve_words: bool = False,
    ) -> Stringable:
        """
        Limit the string to a maximum number of characters.

        Parameters
        ----------
        limit : int, default=100
            Maximum number of characters allowed.
        end : str, default="``...``"
            String to append if truncation occurs.
        preserve_words : bool, default=False
            If True, do not cut off words in the middle.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance limited to the specified number of characters.
            If truncation occurs, the ``end`` string is appended.
        """
        # Validate input parameters
        if not isinstance(limit, int) or limit < 0:
            error_msg = "Limit must be a non-negative integer."
            raise ValueError(error_msg)
        if not isinstance(end, str):
            error_msg = "End must be a string."
            raise TypeError(error_msg)
        if not isinstance(preserve_words, bool):
            error_msg = "Preserve_words must be a boolean."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Return original string if within limit
        if len(s) <= limit:
            return Stringable(s)
        if preserve_words:
            # Find last space before limit to avoid breaking words
            truncated = s[:limit]
            last_space = truncated.rfind(" ")
            if last_space > 0:
                truncated = truncated[:last_space]
        else:
            truncated = s[:limit]

        # Return the truncated string with the end appended
        return Stringable(truncated + end)

    def padBoth(self: Self, length: int, pad: str = " ") -> Stringable:
        """
        Pad both sides of the string to a specified total length.

        Parameters
        ----------
        length : int
            Total desired length of the resulting string.
        pad : str, optional
            String to use for padding. Default is a single space.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with padding added to both sides.
        """
        # Validate input parameters
        if not isinstance(pad, str) or len(pad) == 0:
            error_msg = "'Pad' must be a non-empty string."
            raise ValueError(error_msg)
        if not isinstance(length, int) or length < 0:
            error_msg = "'Length' must be a non-negative integer."
            raise ValueError(error_msg)

        # Get the string representation
        s = str(self)

        # Return original string if already at or above desired length
        if len(s) >= length:
            return Stringable(s)

        # Calculate padding needed on each side
        total_padding = length - len(s)
        left_padding = total_padding // 2
        right_padding = total_padding - left_padding

        # Build left and right padding strings
        left_pad = (pad * ((left_padding // len(pad)) + 1))[:left_padding]
        right_pad = (pad * ((right_padding // len(pad)) + 1))[:right_padding]
        return Stringable(left_pad + s + right_pad)

    def padLeft(self: Self, length: int, pad: str = " ") -> Stringable:
        """
        Pad the left side of the string to a specified total length.

        Parameters
        ----------
        length : int
            Total desired length of the resulting string.
        pad : str, optional
            String to use for padding, by default a single space.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with left padding added.
        """
        # Validate input parameters
        if not isinstance(pad, str) or len(pad) == 0:
            error_msg = "Pad must be a non-empty string."
            raise ValueError(error_msg)
        if not isinstance(length, int) or length < 0:
            error_msg = "Length must be a non-negative integer."
            raise ValueError(error_msg)

        # Get the string representation
        s = str(self)

        # Return original string if already at or above desired length
        if len(s) >= length:
            return Stringable(s)

        # Calculate and apply left padding
        padding_needed = length - len(s)
        left_pad = (pad * ((padding_needed // len(pad)) + 1))[:padding_needed]
        return Stringable(left_pad + s)

    def padRight(self: Self, length: int, pad: str = " ") -> Stringable:
        """
        Pad the right side of the string to a specified total length.

        Parameters
        ----------
        length : int
            The total desired length of the resulting string.
        pad : str, optional
            The string to use for padding, by default a single space.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with right padding added.
        """
        # Validate input parameters
        if not isinstance(pad, str) or len(pad) == 0:
            error_msg = "Pad must be a non-empty string."
            raise ValueError(error_msg)
        if not isinstance(length, int) or length < 0:
            error_msg = "Length must be a non-negative integer."
            raise ValueError(error_msg)

        # Get the string representation
        s = str(self)

        # Return original string if already at or above desired length
        if len(s) >= length:
            return Stringable(s)

        # Calculate and apply right padding
        padding_needed = length - len(s)
        right_pad = (pad * ((padding_needed // len(pad)) + 1))[:padding_needed]
        return Stringable(s + right_pad)

    def trim(self: Self, characters: str | None = None) -> Stringable:
        """
        Trim characters from both ends of the string.

        Parameters
        ----------
        characters : str | None, optional
            Characters to trim from both ends. If None, trims whitespace.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with specified characters trimmed.
        """
        # Validate that characters is a string or None
        if characters is not None and not isinstance(characters, str):
            error_msg = "'Characters' must be a string or None."
            raise TypeError(error_msg)
        # Strip specified characters (or whitespace) from both ends of the string
        return Stringable(str(self).strip(characters))

    def ltrim(self: Self, characters: str | None = None) -> Stringable:
        """
        Remove leading characters from the string.

        Parameters
        ----------
        characters : str | None, optional
            Characters to remove from the start. If None, whitespace is removed.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with leading characters removed.
        """
        # Validate that characters is a string or None
        if characters is not None and not isinstance(characters, str):
            error_msg = "'Characters' must be a string or None."
            raise TypeError(error_msg)
        # Remove leading characters using lstrip
        return Stringable(str(self).lstrip(characters))

    def rtrim(self: Self, characters: str | None = None) -> Stringable:
        """
        Remove trailing characters from the string.

        Parameters
        ----------
        characters : str | None, optional
            Characters to trim from the end. If None, trims whitespace.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with trailing characters removed.
        """
        # Validate that characters is a string or None
        if characters is not None and not isinstance(characters, str):
            error_msg = "Characters must be a string or None."
            raise TypeError(error_msg)
        # Remove trailing characters using rstrip
        return Stringable(str(self).rstrip(characters))

    def charAt(self: Self, index: int) -> str | bool:
        """
        Return the character at a given index.

        Parameters
        ----------
        index : int
            Index of the character to retrieve.

        Returns
        -------
        str or bool
            The character at the specified index, or False if out of bounds.
        """
        if not isinstance(index, int):
            error_msg = "Index must be an integer."
            raise TypeError(error_msg)
        try:
            # Return character at index, or False if index is invalid
            return str(self)[index]
        except IndexError:
            return False

    def position(
        self: Self,
        needle: str,
        offset: int = 0,
        encoding: str | None = None,
    ) -> int | bool:
        """
        Find the position of the first occurrence of a substring.

        Parameters
        ----------
        needle : str
            Substring to search for.
        offset : int, optional
            Starting index for the search. Default is 0.
        encoding : str | None, optional
            String encoding for compatibility. Default is None.

        Returns
        -------
        int or bool
            Index of the first occurrence of the substring, or False if not found.
        """
        # Validate input types for needle, offset, and encoding
        if not isinstance(needle, str):
            error_msg = "'Needle' must be a string."
            raise TypeError(error_msg)
        if not isinstance(offset, int):
            error_msg = "'Offset' must be an integer."
            raise TypeError(error_msg)
        if encoding is not None and not isinstance(encoding, str):
            error_msg = "Encoding must be a string or None."
            raise TypeError(error_msg)

        # Use str.find to locate the substring, return False if not found
        pos = str(self).find(needle, offset)
        return pos if pos != -1 else False

    def match(self: Self, pattern: str) -> Stringable:
        """
        Return the first substring matching the given regular expression pattern.

        Parameters
        ----------
        pattern : str
            Regular expression pattern to search for.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable containing the first match, or an empty Stringable
            if no match is found.
        """
        # Validate that pattern is a string
        if not isinstance(pattern, str):
            error_msg = "Pattern must be a string."
            raise TypeError(error_msg)

        # Search for the first match of the pattern in the string
        match = re.search(pattern, str(self))
        return Stringable(match.group(0) if match else "")

    def matchAll(self: Self, pattern: str) -> list[str]:
        """
        Find all substrings matching the given regular expression pattern.

        Parameters
        ----------
        pattern : str
            Regular expression pattern to search for.

        Returns
        -------
        list[str]
            List of all matching substrings found in the string.
        """
        # Validate that pattern is a string
        if not isinstance(pattern, str):
            error_msg = "Pattern must be a string."
            raise TypeError(error_msg)

        # Find all non-overlapping matches of the pattern in the string
        return re.findall(pattern, str(self))

    def isMatch(self: Self, pattern: str | list[str]) -> bool:
        """
        Determine if the string matches any regular expression pattern.

        Parameters
        ----------
        pattern : str | list[str]
            Regular expression pattern(s) to match.

        Returns
        -------
        bool
            True if the string matches any pattern, otherwise False.
        """
        # Validate pattern type
        if not isinstance(pattern, str) and not isinstance(pattern, Iterable):
            error_msg = "Pattern must be a string or an iterable of strings."
            raise TypeError(error_msg)

        # Normalize pattern to a list for consistent processing
        pattern = [pattern] if isinstance(pattern, str) else list(pattern)

        # Validate that each pattern in the list is a string
        for p in pattern:
            if not isinstance(p, str):
                error_msg = "Each pattern must be a string."
                raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Return True if any pattern matches the string
        return any(re.search(p, s) is not None for p in pattern)

    def test(self: Self, pattern: str) -> bool:
        """
        Test whether the string matches a regular expression pattern.

        Parameters
        ----------
        pattern : str
            Regular expression pattern to match.

        Returns
        -------
        bool
            True if the string matches the pattern, otherwise False.
        """
        # Search the string for the supplied regular expression.
        return re.search(pattern, self) is not None

    def numbers(self: Self) -> Stringable:
        """
        Remove all non-numeric characters from the string.

        Parameters
        ----------
        self : orionis.support.types.Stringable
            The current string instance.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable containing only numeric characters.
        """
        # Remove all non-digit characters using regular expression.
        return Stringable(_RE_NUMBERS.sub("", str(self)))

    def excerpt(
        self: Self,
        phrase: str = "",
        options: dict | None = None,
    ) -> str | None:
        """
        Extract an excerpt containing the first occurrence of a phrase.

        Parameters
        ----------
        phrase : str, optional
            Phrase to search for in the string. Default is "".
        options : dict | None, optional
            Options for excerpt extraction. Supported keys:
            "radius": int, number of characters around the phrase (default 100).
            "omission": str, string to indicate omitted text (default "...").

        Returns
        -------
        str | None
            Excerpt containing the phrase and surrounding context, or None if not found.
        """
        # Validate that phrase is a string
        if not isinstance(phrase, str):
            error_msg = "Phrase must be a string."
            raise TypeError(error_msg)

        # Set default options if not provided
        if options is None:
            options = {}

        # Validate options is a dictionary
        if not isinstance(options, dict):
            error_msg = "Options must be a dictionary or None."
            raise TypeError(error_msg)

        # Get radius and omission from options with defaults
        radius = options.get("radius", 100)
        omission = options.get("omission", "...")

        s = str(self)
        # If no phrase, return the first radius*2 characters with omission if needed
        if not phrase:
            return s[: radius * 2] + (omission if len(s) > radius * 2 else "")

        # Find the position of the phrase (case-insensitive)
        pos = s.lower().find(phrase.lower())
        if pos == -1:
            return None

        # Calculate excerpt boundaries
        start = max(0, pos - radius)
        end = min(len(s), pos + len(phrase) + radius)
        excerpt = s[start:end]

        # Add omission at the start or end if excerpt is truncated
        if start > 0:
            excerpt = omission + excerpt
        if end < len(s):
            excerpt = excerpt + omission

        return excerpt

    def basename(self: Self, suffix: str = "") -> Stringable:
        """
        Return the trailing name component of the path.

        Parameters
        ----------
        suffix : str, optional
            Suffix to remove from the basename. Default is "".

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance containing the basename with the suffix
            removed if present.
        """
        base = Path(str(self)).name
        return Stringable(base.removesuffix(suffix))

    def dirname(self: Self, levels: int = 1) -> Stringable:
        """
        Return the parent directory path.

        Parameters
        ----------
        levels : int, optional
            Number of directory levels to ascend. Defaults to 1.

        Returns
        -------
        orionis.support.types.Stringable
            Stringable instance containing the parent directory path.
        """
        # Use pathlib.Path for robust path handling
        path_obj = Path(str(self))
        for _ in range(levels):
            path_obj = path_obj.parent
        return Stringable(str(path_obj))

    def between(self: Self, from_str: str, to_str: str) -> Stringable:
        """
        Return substring between two delimiters.

        Parameters
        ----------
        from_str : str
            Starting delimiter.
        to_str : str
            Ending delimiter.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable containing text between delimiters, or empty if not found.
        """
        # Validate input types for delimiters
        if not isinstance(from_str, str) or not isinstance(to_str, str):
            error_msg = "Delimiters must be strings."
            raise TypeError(error_msg)

        # Get the string representation and find the positions of the delimiters
        s = str(self)

        # Find the start delimiter
        start = s.find(from_str)
        if start == -1:
            return Stringable("")
        start += len(from_str)

        # Find the end delimiter after the start
        end = s.find(to_str, start)
        if end == -1:
            return Stringable("")

        # Return the substring between the delimiters as a new Stringable instance
        return Stringable(s[start:end])

    def betweenFirst(self: Self, from_str: str, to_str: str) -> Stringable:
        """
        Return the substring between the first pair of delimiters.

        Parameters
        ----------
        from_str : str
            Starting delimiter.
        to_str : str
            Ending delimiter.

        Returns
        -------
        orionis.support.types.Stringable
            Stringable containing text between the first pair of delimiters,
            or an empty Stringable if not found.
        """
        return Stringable.between(self, from_str, to_str)

    def finish(self: Self, cap: str) -> Stringable:
        """
        Ensure the string ends with the given value.

        Parameters
        ----------
        cap : str
            String to append as a cap if not already present.

        Returns
        -------
        orionis.support.types.Stringable
            Stringable instance ending with the specified cap.
        """
        # Validate that cap is a string
        if not isinstance(cap, str):
            error_msg = "Cap must be a string."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Append cap if not already present at the end
        if not s.endswith(cap):
            s += cap

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def start(self: Self, prefix: str) -> Stringable:
        """
        Ensure the string starts with the given prefix.

        Parameters
        ----------
        prefix : str
            The prefix to ensure at the start of the string.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance starting with the specified prefix.
        """
        # Validate that prefix is a string
        if not isinstance(prefix, str):
            error_msg = "Prefix must be a string."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Prepend prefix if not already present at the start
        if not s.startswith(prefix):
            s = prefix + s

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def explode(self: Self, delimiter: str, limit: int = -1) -> list[str]:
        """
        Split the string into a list using a delimiter.

        Parameters
        ----------
        delimiter : str
            The delimiter to split the string on.
        limit : int
            The maximum number of elements to return. If -1, no limit is applied.

        Returns
        -------
        list of str
            List of substrings after splitting by the delimiter.
        """
        # Validate delimiter type
        if not isinstance(delimiter, str):
            error_msg = "Delimiter must be a string."
            raise TypeError(error_msg)

        # Validate limit type and value
        if not isinstance(limit, int) or limit < -1:
            error_msg = "Limit must be an integer greater than or equal to -1."
            raise ValueError(error_msg)

        # Split the string by the delimiter, respecting the limit if provided
        if limit == -1:
            return str(self).split(delimiter)
        return str(self).split(delimiter, limit - 1)

    def split(
        self: Self,
        pattern: str | int | None = None,
        limit: int = -1,
        flags: int = 0,
    ) -> list[str]:
        """
        Split the string by whitespace, a regular expression, or chunk length.

        Parameters
        ----------
        pattern : str or int or None, optional
            Regular expression or positive chunk length. Omit or pass ``None``
            to use native whitespace splitting.
        limit : int, optional
            Maximum whitespace or regex splits. Default is -1 (no limit).
            Chunk splitting retains every chunk independently of this option.
        flags : int, optional
            Regular expression flags. Default is 0.

        Returns
        -------
        list of str
            List of string segments after splitting.

        Raises
        ------
        TypeError
            If the pattern, limit, or flags have unsupported types.
        ValueError
            If a chunk length is not positive or the limit is below -1.
        """
        # Validate pattern type
        if isinstance(pattern, bool) or (
            pattern is not None and not isinstance(pattern, (str, int))
        ):
            error_msg = "Pattern must be a string, positive integer, or None."
            raise TypeError(error_msg)

        # Validate limit value
        if isinstance(limit, bool) or not isinstance(limit, int):
            error_msg = _INTEGER_LIMIT_ERROR
            raise TypeError(error_msg)
        if limit < -1:
            error_msg = "Limit must be an integer greater than or equal to -1."
            raise ValueError(error_msg)

        # Validate flags type
        if not isinstance(flags, int):
            error_msg = "Flags must be an integer."
            raise TypeError(error_msg)

        if pattern is None:
            return str.split(self, None, limit)

        # Split by chunk length if pattern is int
        if isinstance(pattern, int):
            if pattern < 1:
                error_msg = "Chunk length must be a positive integer."
                raise ValueError(error_msg)
            s = str(self)
            return [s[i : i + pattern] for i in range(0, len(s), pattern)]

        # Split by regex pattern
        maxsplit = 0 if limit == -1 else limit
        segments = re.split(pattern, str(self), maxsplit=maxsplit, flags=flags)
        return segments or []

    def ucsplit(self: Self) -> list[str]:
        """
        Split the string by uppercase characters.

        Parameters
        ----------
        self : orionis.support.types.Stringable
            The current string instance.

        Returns
        -------
        list of str
            List of words split by uppercase characters, or the original string
            in a list if no split occurs.
        """
        # Use regex to split on uppercase letters, keeping them with the word.
        parts = _RE_UCSPLIT.findall(str(self))
        return parts or [str(self)]

    def squish(self: Self) -> Stringable:
        """
        Normalize whitespace in the string.

        Replace consecutive whitespace characters with a single space and trim
        leading and trailing whitespace.

        Returns
        -------
        orionis.support.types.Stringable
            Stringable instance with normalized whitespace.
        """
        # Replace multiple whitespace characters with a single space, then trim.
        return Stringable(_RE_SQUISH.sub(" ", str(self)).strip())

    def words(self: Self, words: int = 100, end: str = "...") -> Stringable:
        """
        Limit the string to a maximum number of words.

        Parameters
        ----------
        words : int, optional
            Maximum number of words to include. Default is 100.
        end : str, optional
            String to append if truncation occurs. Default is '...'.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance containing at most the specified number of
            words, with the end string appended if truncation occurs.
        """
        # Validate words parameter
        if not isinstance(words, int) or words < 0:
            error_msg = "Words must be a non-negative integer."
            raise ValueError(error_msg)

        # Validate end parameter
        if not isinstance(end, str):
            error_msg = "End must be a string."
            raise TypeError(error_msg)

        # Split the string into words and check if truncation is needed
        word_list = str(self).split()
        if len(word_list) <= words:
            return Stringable(str(self))
        truncated = " ".join(word_list[:words])
        return Stringable(truncated + end)

    def wordCount(self: Self, characters: str | None = None) -> int:
        """
        Count words in the string.

        Parameters
        ----------
        characters : str | None, optional
            Additional characters to treat as word separators. Default is None.

        Returns
        -------
        int
            Number of words in the string.
        """
        # Validate type of characters argument
        if not isinstance(characters, str) and characters is not None:
            error_msg = "Characters must be a string or None."
            raise TypeError(error_msg)

        # Trim the string to remove leading/trailing whitespace
        s = str(self).strip()

        # Return 0 if the string is empty after trimming
        if not s:
            return 0

        # Replace additional separator characters with spaces if provided
        if characters:
            for char in characters:
                s = s.replace(char, " ")

        # Split by whitespace and count non-empty segments.
        # str.split() with no args already strips and splits on any whitespace,
        # producing no empty segments — the list comprehension is unnecessary.
        return len(s.split())

    def wordWrap(
        self: Self,
        characters: int = 75,
        break_str: str = "\n",
        *,
        cut_long_words: bool = False,
    ) -> Stringable:
        """
        Wrap text to a specified line width.

        Parameters
        ----------
        characters : int, optional
            Maximum line width. Default is 75.
        break_str : str, optional
            String to insert at line breaks.
        cut_long_words : bool, optional
            If True, break long words. Default is False.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with wrapped text.
        """
        # Use textwrap to wrap the string according to the specified options.
        if cut_long_words:
            wrapped = textwrap.fill(
                str(self),
                width=characters,
                break_long_words=True,
                break_on_hyphens=True,
                expand_tabs=False,
            )
        else:
            wrapped = textwrap.fill(
                str(self),
                width=characters,
                break_long_words=False,
                break_on_hyphens=True,
                expand_tabs=False,
            )

        # Replace default line breaks with the specified break string.
        return Stringable(wrapped.replace("\n", break_str))

    def wrap(self: Self, before: str, after: str | None = None) -> Stringable:
        """
        Wrap the string with a prefix and suffix.

        Parameters
        ----------
        before : str
            Prefix to prepend to the string.
        after : str | None, optional
            Suffix to append to the string. If None, uses ``before``.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with the string wrapped by prefix and suffix.
        """
        # Validate input types for prefix and suffix
        if not isinstance(before, str):
            error_msg = "Before must be a string."
            raise TypeError(error_msg)

        # Validate that after is a string or None
        if after is not None and not isinstance(after, str):
            error_msg = "After must be a string or None."
            raise TypeError(error_msg)

        # Use `before` as both prefix and suffix if `after` is not provided
        if after is None:
            after = before

        # Return the wrapped string as a new Stringable instance
        return Stringable(before + str(self) + after)

    def unwrap(self: Self, before: str, after: str | None = None) -> Stringable:
        """
        Remove the specified prefix and suffix from the string.

        Parameters
        ----------
        before : str
            Prefix string to remove from the start.
        after : str | None, optional
            Suffix string to remove from the end. If None, uses ``before``.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with the specified prefix and suffix removed.
        """
        # Validate input types for prefix and suffix
        if not isinstance(before, str):
            error_msg = "Before must be a string."
            raise TypeError(error_msg)

        # Validate that after is a string or None
        if after is not None and not isinstance(after, str):
            error_msg = "After must be a string or None."
            raise TypeError(error_msg)

        # Use the same string for suffix if not provided
        if after is None:
            after = before

        # Get the string representation
        s = str(self)

        # Remove prefix and suffix if present
        s = s.removeprefix(before)
        s = s.removesuffix(after)

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def replaceArray(
        self: Self,
        search: str,
        replace: list[str],
    ) -> Stringable:
        """
        Replace a substring sequentially with elements from a list.

        Parameters
        ----------
        search : str
            Substring to search for and replace.
        replace : list[str]
            List of replacement strings to use sequentially.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with sequential replacements applied.
        """
        # Validate that replace is a list of strings
        if not isinstance(replace, list):
            error_msg = "Replace must be a list of strings."
            raise TypeError(error_msg)

        # Validate that each item in replace is a string
        for item in replace:
            if not isinstance(item, str):
                error_msg = "Each item in replace must be a string."
                raise TypeError(error_msg)

        if not isinstance(search, str):
            message = "Search must be a string."
            raise TypeError(message)
        replacements = iter(replace)
        return Stringable(
            re.sub(
                re.escape(search),
                lambda match: next(replacements, match[0]),
                str(self),
            ),
        )

    def replaceFirst(self: Self, search: str, replace: str) -> Stringable:
        """
        Replace the first occurrence of a substring with a replacement.

        Parameters
        ----------
        search : str
            Substring to search for in the string.
        replace : str
            Replacement string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with the first occurrence replaced.
        """
        # Validate input types for search and replace
        if not isinstance(search, str) or not isinstance(replace, str):
            error_msg = "'Search' and 'replace' must be strings."
            raise TypeError(error_msg)

        # Replace only the first occurrence of the search substring
        return Stringable(str(self).replace(search, replace, 1))

    def replaceLast(self: Self, search: str, replace: str) -> Stringable:
        """
        Replace the last occurrence of a substring with a replacement.

        Parameters
        ----------
        search : str
            Substring to search for in the string.
        replace : str
            Replacement string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with the last occurrence replaced.
        """
        # Validate input types for search and replace
        if not isinstance(search, str) or not isinstance(replace, str):
            error_msg = "'Search' and 'replace' must be strings."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Find the last occurrence of the search substring
        idx = s.rfind(search)

        # Replace the last occurrence if found
        if idx != -1:
            s = s[:idx] + replace + s[idx + len(search) :]

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def replaceStart(self: Self, search: str, replace: str) -> Stringable:
        """
        Replace the first occurrence of a value at the start of the string.

        Parameters
        ----------
        search : str
            String to search for at the start.
        replace : str
            Replacement string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable with the start replaced if the search string is found.
        """
        # Validate input types for search and replace
        if not isinstance(search, str) or not isinstance(replace, str):
            error_msg = "Search and replace must be strings."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Replace the start if it matches the search string
        if s.startswith(search):
            s = replace + s[len(search) :]

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def replaceEnd(self: Self, search: str, replace: str) -> Stringable:
        """
        Replace the last occurrence of a value at the end of the string.

        Parameters
        ----------
        search : str
            String to search for at the end.
        replace : str
            Replacement string.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with the end replaced if the search string is
            found, otherwise returns the original string.
        """
        # Validate input types for search and replace
        if not isinstance(search, str) or not isinstance(replace, str):
            error_msg = "Search and replace must be strings."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Replace the end if it matches the search string
        if s.endswith(search):
            s = s.removesuffix(search) + replace

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def replaceMatches(
        self: Self,
        pattern: str | list[str],
        replace: str | Callable,
        limit: int = -1,
    ) -> Stringable:
        """
        Replace pattern matches in the string using regular expressions.

        Parameters
        ----------
        pattern : str | list[str]
            Regular expression pattern(s) to search for.
        replace : str | collections.abc.Callable
            Replacement string or callback function.
        limit : int, optional
            Maximum replacements per pattern. Zero leaves the string unchanged;
            -1 applies no limit. Values below -1 are invalid.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with pattern matches replaced.
        """
        # Validate pattern argument type
        if not isinstance(pattern, str) and not isinstance(pattern, list):
            error_msg = "Pattern must be a string or a list of strings."
            raise TypeError(error_msg)
        if isinstance(pattern, list) and any(
            not isinstance(pat, str) for pat in pattern
        ):
            error_msg = "Each pattern must be a string."
            raise TypeError(error_msg)

        # Validate replace argument type
        if not (isinstance(replace, str) or callable(replace)):
            error_msg = "Replace must be a string or a callable."
            raise TypeError(error_msg)
        # Validate limit argument type
        if not isinstance(limit, int):
            error_msg = _INTEGER_LIMIT_ERROR
            raise TypeError(error_msg)
        if limit < -1:
            error_msg = "Limit must be greater than or equal to -1."
            raise ValueError(error_msg)
        if limit == 0:
            return Stringable(self)

        # Get the string representation
        s = str(self)

        # Normalize pattern to a list for consistent processing
        patterns = [pattern] if isinstance(pattern, str) else pattern

        # Apply each pattern replacement up to the specified limit
        count = 0 if limit == -1 else limit
        for pat in patterns:
            s = re.sub(pat, replace, s, count=count)

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def remove(
        self: Self,
        search: str | list[str],
        *,
        case_sensitive: bool = True,
    ) -> Stringable:
        """
        Remove all occurrences of specified substrings from the string.

        Parameters
        ----------
        search : str | list[str]
            Substring(s) to remove from the string.
        case_sensitive : bool, default True
            If True, removal is case sensitive.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with specified substrings removed.
        """
        # Validate search argument type
        if not isinstance(search, str) and not isinstance(search, list):
            error_msg = "Search must be a string or a list of strings."
            raise TypeError(error_msg)
        if isinstance(search, list):
            for needle in search:
                if not isinstance(needle, str):
                    error_msg = "Each item in search must be a string."
                    raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Normalize search to a list for consistent processing
        needles = [search] if isinstance(search, str) else search

        # Remove each occurrence of the search string(s)
        for needle in needles:
            if case_sensitive:
                s = s.replace(needle, "")
            else:
                s = re.sub(re.escape(needle), "", s, flags=re.IGNORECASE)

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def plural(
        self: Self,
        count: object = 2,
        *,
        prepend_count: bool = False,
    ) -> Stringable:
        """
        Apply regular English plural suffix heuristics to a word.

        Parameters
        ----------
        count : int, float or object with __len__, optional
            Count to determine if plural is needed, by default 2
        prepend_count : bool, optional
            Whether to prepend the count, by default False

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable with plural form
        """
        # Validate prepend_count type
        if not isinstance(prepend_count, bool):
            error_msg = "prepend_count must be a boolean."
            raise TypeError(error_msg)

        # Validate count type
        if not (isinstance(count, (int, float)) or hasattr(count, "__len__")):
            error_msg = "count must be an integer, float, or a collection."
            raise TypeError(error_msg)

        # Get lowercase version for comparison
        s = str(self)
        actual_count = len(count) if hasattr(count, "__len__") else count
        result = s if actual_count == 1 else _pluralize_word(s)

        # Prepend count if requested
        if prepend_count:
            result = f"{actual_count} {result}"

        return Stringable(result)

    def pluralStudly(self: Self, count: object = 2) -> Stringable:
        """
        Pluralize the last word of an English, studly caps case string.

        Parameters
        ----------
        count : int, float or object with __len__, optional
            Count to determine if plural is needed, by default 2

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable with pluralized last word in StudlyCase
        """
        s = str(self)
        # Find the last word boundary using regex pattern
        parts = _RE_PASCAL_WORDS.findall(s)
        if parts:
            # Pluralize the last word and convert back to StudlyCase
            last_word = parts[-1]
            pluralized_last = Stringable(last_word).plural(count).studly().value()
            parts[-1] = pluralized_last
            return Stringable("".join(parts))

        # Fall back to pluralizing the entire string and converting to StudlyCase
        return self.plural(count).studly()

    def pluralPascal(self: Self, count: object = 2) -> Stringable:
        """
        Pluralize the last word of an English Pascal case string.

        Parameters
        ----------
        count : int, float or object with __len__, optional
            Count to determine if plural is needed. Default is 2.

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable with pluralized last word in PascalCase.
        """
        # Get string representation
        s = str(self)
        if len(s) == 0:
            return Stringable(s)

        # Split by uppercase letters to identify words
        words = _RE_PASCAL_WORDS.findall(s)
        if not words:
            return Stringable(s)

        # Determine if pluralization is needed
        if isinstance(count, (list, tuple)):
            need_plural = len(count) != 1
        else:
            need_plural = count != 1

        # Pluralize the last word if needed
        if need_plural:
            last_word = words[-1]
            pluralized = Stringable(last_word).plural(count)
            words[-1] = pluralized.studly().value()

        # Return the reconstructed string
        return Stringable("".join(words))

    def singular(self: Self) -> Stringable:
        """
        Apply regular English singular suffix heuristics to a word.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable with singular form of the word.
        """
        # Get lowercase version for comparison and original for case preservation
        word = str(self).lower()
        s = str(self)

        # Apply simple English singularization rules
        if word.endswith("ies") and len(word) > 3:
            result = s[:-3] + "y"
        elif word.endswith(("ives", "ves", "es")):
            if word.endswith("ives"):
                result = s[:-4] + "fe"
            elif word.endswith("ves"):
                result = s[:-3] + "f"
            else:
                result = s[:-2]
        elif word.endswith("s") and not word.endswith("ss"):
            result = s[:-1]
        else:
            result = s

        return Stringable(result)

    def parseCallback(self: Self, default: str | None = None) -> list[str | None]:
        """
        Parse a Class@method style callback into class and method.

        Parameters
        ----------
        default : str | None, optional
            Default method name if not specified. Default is None.

        Returns
        -------
        list[str | None]
            List containing [class_name, method_name].
        """
        # Validate that default is a string or None
        if default is not None and not isinstance(default, str):
            error_msg = "Default must be a string or None."
            raise TypeError(error_msg)

        # Get the string representation of the callback
        callback_str = str(self)

        # Split on '@' if present, otherwise return class and default method
        if "@" in callback_str:
            parts = callback_str.split("@", 1)
            return [parts[0], parts[1]]
        return [callback_str, default]

    def when(
        self: Self,
        condition: bool | Callable,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute the given callback if condition is true.

        Parameters
        ----------
        condition : bool or callable
            The condition to evaluate.
        callback : callable
            The callback to execute if condition is true.
        default : callable or None, optional
            The callback to execute if condition is false. Default is None.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or self.
        """
        # Validate that condition is a boolean or callable
        if not isinstance(condition, bool) and not callable(condition):
            error_msg = "Condition must be a boolean or a callable."
            raise TypeError(error_msg)

        # Validate that callback is callable
        if not callable(callback):
            error_msg = "Callback must be a callable."
            raise TypeError(error_msg)

        # Validate that default is callable or None
        if default is not None and not callable(default):
            error_msg = "Default must be a callable or None."
            raise TypeError(error_msg)

        # Evaluate condition if it's callable, otherwise use as-is
        condition_result = condition(self) if callable(condition) else condition

        # Execute callback if condition is true
        if condition_result:
            result = callback(self)
            return Stringable(result) if not isinstance(result, Stringable) else result

        # Execute default callback if condition is false and default is provided
        if default:
            result = default(self)
            return Stringable(result) if not isinstance(result, Stringable) else result

        # Return self if no callbacks were executed
        return self

    def whenContains(
        self: Self,
        needles: str | list[str],
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if the string contains a given substring.

        Parameters
        ----------
        needles : str | list[str]
            Substring(s) to search for in the string.
        callback : collections.abc.Callable
            Function to execute if the condition is True.
        default : collections.abc.Callable | None, optional
            Function to execute if the condition is False.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Use the when method to conditionally execute the callback.
        return self.when(self.contains(needles), callback, default)

    def whenContainsAll(
        self: Self,
        needles: list[str],
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if the string contains all specified substrings.

        Parameters
        ----------
        needles : list[str]
            Substrings to search for in the string.
        callback : collections.abc.Callable
            Function to execute if all substrings are found.
        default : collections.abc.Callable | None, optional
            Function to execute if not all substrings are found.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Check if all needles are present in the string
        contains_all = all(needle in str(self) for needle in needles)
        return self.when(contains_all, callback, default)

    def whenEmpty(
        self: Self,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if the string is empty.

        Parameters
        ----------
        callback : collections.abc.Callable
            Function to execute if the string is empty.
        default : collections.abc.Callable | None, optional
            Function to execute if the string is not empty.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Use the when method to conditionally execute the callback if empty.
        return self.when(self.isEmpty(), callback, default)

    def whenNotEmpty(
        self: Self,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute the callback if the string is not empty.

        Parameters
        ----------
        callback : collections.abc.Callable
            Function to execute if the string is not empty.
        default : collections.abc.Callable | None, optional
            Function to execute if the string is empty.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Call the callback if the string is not empty, else call default.
        return self.when(self.isNotEmpty(), callback, default)

    def whenEndsWith(
        self: Self,
        needles: str | list[str],
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute the callback if the string ends with the given substring(s).

        Parameters
        ----------
        needles : str or list[str]
            Substring(s) to check at the end of the string.
        callback : collections.abc.Callable
            Function to execute if the condition is True.
        default : collections.abc.Callable | None, optional
            Function to execute if the condition is False.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Use the when method to conditionally execute the callback if endsWith is True.
        return self.when(self.endsWith(needles), callback, default)

    def whenDoesntEndWith(
        self: Self,
        needles: str | list[str],
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if the string does not end with the given substring(s).

        Parameters
        ----------
        needles : str | list[str]
            Substring(s) to check at the end of the string.
        callback : collections.abc.Callable
            Function to execute if the condition is True.
        default : collections.abc.Callable | None, optional
            Function to execute if the condition is False.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Call the callback if the string does not end with any needle,
        # else call default.
        return self.when(not self.endsWith(needles), callback, default)

    def whenExactly(
        self: Self,
        value: str,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if the string exactly matches the given value.

        Parameters
        ----------
        value : str
            Value to compare for an exact match.
        callback : collections.abc.Callable
            Function to execute if the string matches exactly.
        default : collections.abc.Callable | None, optional
            Function to execute if the string does not match exactly.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Use the when method to conditionally execute the callback if exactly is True.
        return self.when(self.exactly(value), callback, default)

    def whenNotExactly(
        self: Self,
        value: str,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if string does not exactly match the given value.

        Parameters
        ----------
        value : str
            Value to compare for an exact match.
        callback : collections.abc.Callable
            Function to execute if the string does not match exactly.
        default : collections.abc.Callable | None, optional
            Function to execute if the string matches exactly.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Call the callback if the string does not match exactly, else call default.
        return self.when(not self.exactly(value), callback, default)

    def whenStartsWith(
        self: Self,
        needles: str | list[str],
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if the string starts with a given substring.

        Parameters
        ----------
        needles : str or list[str]
            Substring(s) to check at the start of the string.
        callback : collections.abc.Callable
            Function to execute if the condition is True.
        default : collections.abc.Callable | None, optional
            Function to execute if the condition is False.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Normalize needles to a list for consistent processing
        if not isinstance(needles, list):
            needles = [needles]

        # Validate that all items in needles are strings
        for needle in needles:
            if not isinstance(needle, str):
                error_msg = "Each needle must be a string."
                raise TypeError(error_msg)

        # Check if the string starts with any of the provided needles
        starts_with = any(str(self).startswith(needle) for needle in needles)
        return self.when(starts_with, callback, default)

    def whenDoesntStartWith(
        self: Self,
        needles: str | list[str],
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if the string does not start with the given substring(s).

        Parameters
        ----------
        needles : str or list[str]
            Substring(s) to check at the start of the string.
        callback : collections.abc.Callable
            Function to execute if the condition is True.
        default : collections.abc.Callable | None, optional
            Function to execute if the condition is False.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Normalize needles to a list for consistent processing
        if not isinstance(needles, list):
            needles = [needles]

        # Validate that all items in needles are strings
        for needle in needles:
            if not isinstance(needle, str):
                error_msg = "Each needle must be a string."
                raise TypeError(error_msg)

        # Check if the string does not start with any of the provided needles
        starts_with = any(str(self).startswith(needle) for needle in needles)
        return self.when(not starts_with, callback, default)

    def whenTest(
        self: Self,
        pattern: str,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute callback if the string matches the given regular expression.

        Parameters
        ----------
        pattern : str
            Regular expression pattern to match.
        callback : collections.abc.Callable
            Function to execute if the pattern matches.
        default : collections.abc.Callable | None, optional
            Function to execute if the pattern does not match. Default is None.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Use the when method to conditionally execute the callback if test is True.
        return self.when(self.test(pattern), callback, default)

    def convertCase(self: Self, mode: int | None = None) -> Stringable:
        """
        Convert string case using specified mode.

        Parameters
        ----------
        mode : int | None, optional
            Case conversion mode:
            0 or None - casefold (default)
            1 - uppercase
            2 - lowercase
            3 - titlecase

        Returns
        -------
        orionis.support.types.Stringable
            New Stringable instance with converted case.
        """
        # Validate that mode is an integer or None
        if mode is not None and not isinstance(mode, int):
            error_msg = "Mode must be an integer or None."
            raise TypeError(error_msg)

        # Get string representation for case conversion
        s = str(self)

        # Apply case conversion based on mode parameter
        if mode is None or mode == 0:
            # Use casefold for case-insensitive comparisons
            return Stringable(s.casefold())
        if mode == 1:
            # Convert to uppercase
            return Stringable(s.upper())
        if mode == 2:
            # Convert to lowercase
            return Stringable(s.lower())
        if mode == 3:
            # Convert to title case
            return Stringable(s.title())

        # Default to casefold for any other mode value
        return Stringable(s.casefold())

    def transliterate(
        self: Self,
        unknown: str = "?",
        *,
        strict: bool = False,
    ) -> Stringable:
        """
        Transliterate a string to its closest ASCII representation.

        Parameters
        ----------
        unknown : str, optional
            Character to use for unknown characters. Default is "?".
        strict : bool, optional
            Whether to be strict about transliteration. Default is False.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable with transliterated text.
        """
        # Validate that unknown is a single character string
        if not isinstance(unknown, str) or len(unknown) != 1:
            error_msg = "Unknown must be a single character string."
            raise TypeError(error_msg)

        # Validate that strict is a boolean
        if not isinstance(strict, bool):
            error_msg = "Strict must be a boolean."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Normalize and encode to ASCII at C level.
        normalized = unicodedata.normalize("NFKD", s)

        if strict:
            # Keep ASCII characters; replace others with unknown character.
            ascii_chars = [char if ord(char) < 128 else unknown for char in normalized]
            return Stringable("".join(ascii_chars))

        # Lenient: filter non-ASCII at C level via encode/decode
        ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
        return Stringable(ascii_str)

    def hash(self: Self, algorithm: str) -> Stringable:
        """
        Hash the string using the specified algorithm.

        Parameters
        ----------
        algorithm : str
            Hash algorithm name (md5, sha1, sha256, etc.)

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance containing the hexadecimal hash.

        Raises
        ------
        ValueError
            If the specified algorithm is not supported.
        """
        # Validate that the algorithm is supported by hashlib
        if algorithm not in hashlib.algorithms_available:
            error_msg = f"Unsupported hash algorithm: {algorithm}"
            raise ValueError(error_msg)

        # Create hash object and compute hash of the string
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(str(self).encode("utf-8"))
        return Stringable(hash_obj.hexdigest())

    def pipe(self: Self, callback: Callable) -> Stringable:
        """
        Pass the string through the given callback and return the result.

        Parameters
        ----------
        callback : collections.abc.Callable
            The callback function to apply to the string.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance containing the result of the callback.

        Raises
        ------
        TypeError
            If the callback is not callable.
        """
        # Validate that the callback is callable
        if not callable(callback):
            error_msg = "Callback must be callable."
            raise TypeError(error_msg)

        # Execute the callback with the current string
        result = callback(self)

        # Return result as Stringable if not already one
        return Stringable(result) if not isinstance(result, Stringable) else result

    def take(self: Self, limit: int) -> Stringable:
        """
        Take a specified number of characters from the start or end.

        Parameters
        ----------
        limit : int
            Number of characters to take. Negative values take from the end.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable containing the taken characters.
        """
        # Validate that limit is an integer
        if not isinstance(limit, int):
            error_msg = _INTEGER_LIMIT_ERROR
            raise TypeError(error_msg)

        # Take from end if limit is negative, else from start
        if limit < 0:
            return Stringable(str(self)[limit:])

        # Take from start if limit is positive
        return Stringable(str(self)[:limit])

    def swap(self: Self, map_dict: dict[str, str]) -> Stringable:
        """
        Swap multiple keywords in a string with other keywords.

        Parameters
        ----------
        map_dict : typing.Dict[str, str]
            Dictionary mapping old values to new values.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with swapped values.

        Raises
        ------
        TypeError
            If map_dict is not a dictionary or contains non-string keys/values.
        """
        # Validate that map_dict is a dictionary
        if not isinstance(map_dict, dict):
            error_msg = "map_dict must be a dictionary."
            raise TypeError(error_msg)

        # Validate that all keys and values are strings
        if not all(
            isinstance(k, str) and isinstance(v, str) for k, v in map_dict.items()
        ):
            error_msg = "All keys and values in map_dict must be strings."
            raise TypeError(error_msg)

        # Apply all replacements to the string
        s = str(self)
        for old, new in map_dict.items():
            s = s.replace(old, new)

        # Return the modified string as a new Stringable instance
        return Stringable(s)

    def substrCount(
        self: Self,
        needle: str,
        offset: int = 0,
        length: int | None = None,
    ) -> int:
        """
        Count the number of substring occurrences in the string.

        Parameters
        ----------
        needle : str
            The substring to count occurrences of.
        offset : int, optional
            Starting position to begin the search. Default is 0.
        length : int | None, optional
            Maximum length to search within. If None, searches to end.
            Default is None.

        Returns
        -------
        int
            Number of non-overlapping occurrences of the needle substring.

        Raises
        ------
        TypeError
            If needle is not a string, offset is not an integer, or length
            is not an integer or None.
        """
        # Validate that needle is a string
        if not isinstance(needle, str):
            error_msg = "Needle must be a string."
            raise TypeError(error_msg)

        # Validate that offset is an integer
        if not isinstance(offset, int):
            error_msg = "Offset must be an integer."
            raise TypeError(error_msg)

        # Validate that length is an integer or None
        if length is not None and not isinstance(length, int):
            error_msg = "Length must be an integer or None."
            raise TypeError(error_msg)

        # Get the string representation
        s = str(self)

        # Extract substring based on offset and optional length
        start = max(0, len(s) + offset) if offset < 0 else offset
        s = s[start : start + length] if length is not None else s[start:]

        # Count non-overlapping occurrences of needle in the substring
        return s.count(needle)

    def substrReplace(
        self: Self,
        replace: str | list[str],
        offset: int | list[int] = 0,
        length: int | list[int] | None = None,
    ) -> Stringable:
        """
        Replace text within a portion of a string.

        Parameters
        ----------
        replace : str | list[str]
            Replacement string(s)
        offset : int | list[int], optional
            Starting position(s), by default 0
        length : int | list[int] | None, optional
            Length(s) to replace. None, zero or an omitted entry inserts text
            without removing existing characters.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable with replaced text

        Raises
        ------
        TypeError
            If replace is not a string or list of strings.
        TypeError
            If offset is not an integer or list of integers.
        TypeError
            If length is not an integer, list of integers, or None.
        ValueError
            If any length value is negative.
        ValueError
            If lists have incompatible lengths.
        """
        replacements = _replacement_values(replace, str, "Replace")
        offsets = _replacement_values(offset, int, "Offset")
        lengths = None if length is None else _replacement_values(length, int, "Length")
        if lengths is not None and any(value < 0 for value in lengths):
            message = "Length cannot be negative."
            raise ValueError(message)
        for name, values in (("Offset", offsets), ("Length", lengths)):
            if values is not None and len(values) > len(replacements):
                message = f"{name} list cannot exceed replace list length."
                raise ValueError(message)
        result = str(self)
        for index, replacement in enumerate(replacements):
            position = offsets[min(index, len(offsets) - 1)]
            size = lengths[index] if lengths is not None and index < len(lengths) else 0
            result = _replace_portion(result, replacement, position, size)
        return Stringable(result)

    def scan(self: Self, format_str: str) -> list[str]:
        """
        Parse input from a string according to a format pattern.

        Extracts values from the string using a simplified sscanf-like format
        string with %s (strings), %d (digits), and %f (floats) placeholders.

        Parameters
        ----------
        format_str : str
            Format string with placeholders (%s, %d, %f).

        Returns
        -------
        list[str]
            List of parsed string values, or empty list if no matches found.

        Raises
        ------
        TypeError
            If format_str is not a string.
        """
        # Validate that format_str is a string
        if not isinstance(format_str, str):
            error_msg = "Format string must be a string."
            raise TypeError(error_msg)

        placeholders = {
            "%s": r"(\S+)",
            "%d": r"([+-]?\d+)",
            "%f": r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
        }
        pattern = "".join(
            placeholders.get(part, re.escape(part))
            for part in re.split(r"(%[sdf])", format_str)
        )
        match = re.search(pattern, str(self))
        return list(match.groups()) if match else []

    def prepend(self: Self, *values: str) -> Stringable:
        """
        Prepend values to the beginning of the string.

        Parameters
        ----------
        *values : str
            One or more string values to prepend to the current string.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance with all provided values prepended.

        Raises
        ------
        TypeError
            If any value is not a string.
        """
        # Validate that all arguments are strings before prepending
        for arg in values:
            if not isinstance(arg, str):
                error_msg = "All values to prepend must be strings."
                raise TypeError(error_msg)

        # Concatenate all values before the current string
        return Stringable("".join(values) + str(self))

    def substr(self: Self, start: int, length: int | None = None) -> Stringable:
        """
        Return the portion of the string specified by start and length parameters.

        Parameters
        ----------
        start : int
            Starting position for substring extraction.
        length : int | None, optional
            Length of substring to extract. If None, extracts to end of string.
            Default is None.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance containing the extracted substring.

        Raises
        ------
        TypeError
            If start is not an integer or length is not an integer or None.
        """
        # Validate that start is an integer
        if not isinstance(start, int):
            error_msg = "Start must be an integer."
            raise TypeError(error_msg)

        # Validate that length is an integer or None
        if length is not None and not isinstance(length, int):
            error_msg = "Length must be an integer or None."
            raise TypeError(error_msg)

        # Extract substring based on start and optional length
        s = str(self)
        if length is None:
            return Stringable(s[start:])
        if start < 0:
            start = max(0, len(s) + start)
        return Stringable(s[start : start + length])

    def doesntContain(
        self: Self,
        needles: str | list[str],
        *,
        ignore_case: bool = False,
    ) -> bool:
        """
        Determine if the string doesn't contain any given substring.

        Parameters
        ----------
        needles : str | list[str]
            The substring(s) to search for within the string.
        ignore_case : bool, optional
            If True, perform case-insensitive search. Default is False.

        Returns
        -------
        bool
            True if the string doesn't contain any of the needle values,
            otherwise False.

        Raises
        ------
        TypeError
            If needles is not a string or list of strings, or if ignore_case
            is not a boolean.
        """
        # Validate that needles is a string or a list
        if not isinstance(needles, str) and not isinstance(needles, list):
            error_msg = "'Needles' must be a string or a list of strings."
            raise TypeError(error_msg)

        # Normalize needles to a list for consistent processing
        if isinstance(needles, str):
            needles = [needles]

        # Validate that all items in needles are strings
        for needle in needles:
            if not isinstance(needle, str):
                error_msg = "All 'needles' must be Strings."
                raise TypeError(error_msg)

        # Validate that ignore_case is a boolean
        if not isinstance(ignore_case, bool):
            error_msg = "Ignore_case must be a boolean."
            raise TypeError(error_msg)

        # Return the negation of the contains method result
        return not self.contains(needles, ignore_case=ignore_case)

    def doesntStartWith(self: Self, needles: str | list[str]) -> bool:
        """
        Determine if the string doesn't start with any given substring.

        Parameters
        ----------
        needles : str | list[str]
            The substring(s) to check at the start of the string.

        Returns
        -------
        bool
            True if the string doesn't start with any needle, False otherwise.

        Raises
        ------
        TypeError
            If needles is not a string or list of strings.
        """
        # Validate that needles is a string or a list
        if not isinstance(needles, str) and not isinstance(needles, list):
            error_msg = "'Needles' must be a string or a list of strings."
            raise TypeError(error_msg)

        # Normalize needles to a list for consistent processing
        if isinstance(needles, str):
            needles = [needles]

        # Validate that all items in needles are strings
        for needle in needles:
            if not isinstance(needle, str):
                error_msg = "All 'needles' must be strings."
                raise TypeError(error_msg)

        # Check if the string does not start with any of the provided needles
        return not any(str(self).startswith(needle) for needle in needles)

    def doesntEndWith(self: Self, needles: str | list[str]) -> bool:
        """
        Determine if string doesn't end with any given substring.

        Parameters
        ----------
        needles : str | list[str]
            The substring(s) to check.

        Returns
        -------
        bool
            True if string doesn't end with any needle, False otherwise.

        Raises
        ------
        TypeError
            If needles is not a string or list of strings.
        """
        # Validate that needles is a string or a list
        if not isinstance(needles, str) and not isinstance(needles, list):
            error_msg = "Needles must be a string or a list of strings."
            raise TypeError(error_msg)

        # Normalize needles to a list for consistent processing
        if isinstance(needles, str):
            needles = [needles]

        # Validate that all items in needles are strings
        for needle in needles:
            if not isinstance(needle, str):
                error_msg = "All 'needles' must be strings."
                raise TypeError(error_msg)

        # Check if the string does not end with any of the provided needles
        return not self.endsWith(needles)

    def startsWith(self: Self, needles: str | list[str]) -> bool:
        """
        Determine if the string starts with any of the given substrings.

        Parameters
        ----------
        needles : str | list[str]
            The substring(s) to check at the start of the string.

        Returns
        -------
        bool
            True if the string starts with any of the needle values, otherwise
            False.
        """
        # Validate that needles is a string or a list
        if not isinstance(needles, str) and not isinstance(needles, list):
            error_msg = "Needles must be a string or a list of strings."
            raise TypeError(error_msg)

        # Normalize needles to a list for consistent processing
        if isinstance(needles, str):
            needles = [needles]

        # Validate that all items in needles are strings
        for needle in needles:
            if not isinstance(needle, str):
                error_msg = "All needles must be strings."
                raise TypeError(error_msg)

        # Check if the string starts with any of the provided needles
        return any(str(self).startswith(needle) for needle in needles)

    def jsonSerialize(self: Self) -> str:
        """
        Convert the object to a string when JSON encoded.

        Return plain text for callers that use an explicit serialization hook.
        The standard JSON encoder already supports this str subclass directly.

        Returns
        -------
        str
            The string representation for JSON serialization.
        """
        return str(self)

    def offsetExists(self: Self, offset: int) -> bool:
        """
        Determine if the given offset exists in the string.

        Parameters
        ----------
        offset : int
            Offset to check for existence.

        Returns
        -------
        bool
            True if the offset exists, False otherwise.
        """
        # Check if offset is an integer and within bounds of the string.
        if not isinstance(offset, int):
            return False
        try:
            str(self)[offset]
            return True
        except IndexError:
            return False

    def offsetGet(self: Self, offset: int) -> str:
        """
        Get the character at the specified offset.

        Parameters
        ----------
        offset : int
            Index of the character to retrieve.

        Returns
        -------
        str
            Character at the given offset.

        Raises
        ------
        TypeError
            If offset is not an integer.
        IndexError
            If offset is out of bounds.
        """
        # Validate that offset is an integer
        if not isinstance(offset, int):
            error_msg = "Offset must be an integer."
            raise TypeError(error_msg)

        # Return the character at the specified offset
        return str(self)[offset]

    def isPattern(
        self: Self,
        pattern: str | list[str],
        *,
        ignore_case: bool = False,
    ) -> bool:
        """
        Check if the string matches any of the given patterns.

        Parameters
        ----------
        pattern : str | list[str]
            Pattern(s) to match, supports wildcards '*' and '?'.
        ignore_case : bool, optional
            If True, perform case-insensitive matching. Default is False.

        Returns
        -------
        bool
            True if the string matches any pattern, otherwise False.

        Raises
        ------
        TypeError
            If pattern is not a string or list of strings.
        TypeError
            If ignore_case is not a boolean.
        ValueError
            If the pattern list is empty.
        """
        # Validate ignore_case parameter type
        if not isinstance(ignore_case, bool):
            error_msg = "ignore_case must be a boolean."
            raise TypeError(error_msg)

        # Validate pattern parameter type
        if not isinstance(pattern, (str, list)):
            error_msg = "Pattern must be a string or a list of strings."
            raise TypeError(error_msg)

        # Normalize pattern to list for consistent processing
        patterns = [pattern] if isinstance(pattern, str) else pattern

        # Validate that patterns list is not empty
        if not patterns:
            error_msg = "Pattern list cannot be empty."
            raise ValueError(error_msg)

        # Validate that all patterns are strings
        for i, p in enumerate(patterns):
            if not isinstance(p, str):
                error_msg = (
                    f"Pattern at index {i} must be a string, got {type(p).__name__}."
                )
                raise TypeError(error_msg)

        # Get string representation
        s = str(self)

        # Apply case-insensitive matching if requested
        if ignore_case:
            s = s.lower()
            patterns = [p.lower() for p in patterns]

        # Check if string matches any of the patterns
        return any(fnmatch.fnmatchcase(s, p) for p in patterns)

    def containsAll(
        self: Self,
        needles: list[str],
        *,
        ignore_case: bool = False,
    ) -> bool:
        """
        Check if the string contains all specified substrings.

        Parameters
        ----------
        needles : list[str]
            List of substrings to search for.
        ignore_case : bool
            If True, perform case-insensitive search. Default is False.

        Returns
        -------
        bool
            True if all needles are found in the string, otherwise False.
        """
        # Validate needles is a list
        if not isinstance(needles, list):
            error_msg = "Needles must be provided as a list of strings."
            raise TypeError(error_msg)

        # Validate all items in needles are strings
        if not all(isinstance(needle, str) for needle in needles):
            error_msg = "All needles must be strings."
            raise TypeError(error_msg)

        # If needles list is empty, raise an error
        if len(needles) == 0:
            error_msg = "Needles list cannot be empty."
            raise ValueError(error_msg)

        # If only one needle, use contains method
        if len(needles) == 1:
            return self.contains(needles[0], ignore_case=ignore_case)

        # Validate ignore_case is a boolean
        if not isinstance(ignore_case, bool):
            error_msg = "ignore_case must be a boolean."
            raise TypeError(error_msg)

        # Normalize case if requested
        s = str(self)
        if ignore_case:
            s = s.lower()
            needles = [needle.lower() for needle in needles]

        # Return True only if all needles are present
        return all(needle in s for needle in needles)

    def whenIs(
        self: Self,
        pattern: str | list[str],
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute the callback if the string matches the given pattern.

        Parameters
        ----------
        pattern : str or list of str
            Pattern(s) to match against.
        callback : collections.abc.Callable
            Function to execute if the string matches the pattern.
        default : collections.abc.Callable or None, optional
            Function to execute if the string does not match the pattern.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Call the callback if the string matches the pattern, else call default.
        return self.when(self.isPattern(pattern), callback, default)

    def whenIsAscii(
        self: Self,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute the callback if the string is 7-bit ASCII.

        Parameters
        ----------
        callback : collections.abc.Callable
            Function to execute if the string is ASCII.
        default : collections.abc.Callable | None, optional
            Function to execute if the string is not ASCII.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Call the callback if the string is ASCII, else call default.
        return self.when(self.isAscii(), callback, default)

    def whenIsUuid(
        self: Self,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute the callback if the string is a valid UUID.

        Parameters
        ----------
        callback : collections.abc.Callable
            Function to execute if the string is a valid UUID.
        default : collections.abc.Callable | None, optional
            Function to execute if the string is not a valid UUID.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Call the callback if the string is a valid UUID, else call default.
        return self.when(self.isUuid(), callback, default)

    def whenIsUlid(
        self: Self,
        callback: Callable,
        default: Callable | None = None,
    ) -> Stringable:
        """
        Execute the callback if the string is a valid ULID.

        Parameters
        ----------
        callback : collections.abc.Callable
            Function to execute if the string is a valid ULID.
        default : collections.abc.Callable | None, optional
            Function to execute if the string is not a valid ULID.

        Returns
        -------
        orionis.support.types.Stringable
            Result of callback execution or the original Stringable instance.
        """
        # Call the callback if the string is a valid ULID, else call default.
        return self.when(self.isUlid(), callback, default)

    def toDate(self: Self, format_str: str | None = "%Y-%m-%d") -> datetime:
        """
        Convert string to a datetime object.

        Parameters
        ----------
        format_str : str or None, optional
            Format string for parsing. Defaults to "%Y-%m-%d". None uses ISO syntax.

        Returns
        -------
        datetime.datetime
            Parsed datetime with its explicit offset preserved. Naive input uses
            the application's configured timezone.

        Raises
        ------
        ValueError
            If the input does not match the format or ISO syntax.
        """
        # Import necessary modules
        from orionis.support.facades.datetime import DateTime

        # Get the string representation
        s = str(self)

        # If format_str is None, use fromisoformat
        try:
            parsed = (
                datetime.fromisoformat(s)
                if format_str is None
                else datetime.strptime(s, format_str)
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=DateTime.getZoneInfo())
            return parsed
        except ValueError as err:
            error_msg = f"String '{s}' does not match format '{format_str}'"
            raise ValueError(error_msg) from err

    def encrypt(self: Self) -> str:
        """
        Encrypt the string using the Crypt facade.

        Uses the application's configured encryption service.

        Returns
        -------
        str
            The payload returned by the configured encryption service.
        """
        # Use the Crypt facade to encrypt the string.
        from orionis.support.facades.encrypter import Crypt

        return Crypt.encrypt(self.value())

    def decrypt(self: Self) -> str:
        """
        Decrypt the string using the Crypt facade.

        Uses the application's configured encryption service.

        Returns
        -------
        str
            The plaintext returned by the configured encryption service.
        """
        # Use the Crypt facade to decrypt the string.
        from orionis.support.facades.encrypter import Crypt

        return Crypt.decrypt(self.value())

    def toHtmlString(self: Self) -> Stringable:
        """
        Escape HTML entities in the string.

        Escapes special HTML characters in the string to ensure safe HTML output.

        Returns
        -------
        orionis.support.types.Stringable
            A new Stringable instance containing the HTML-escaped string.
        """
        # Escape HTML entities for safe HTML output
        return Stringable(html.escape(str(self)))

    def tap(self: Self, callback: Callable[[Stringable], object]) -> Stringable:
        """
        Call the callback with the string and return the string.

        Parameters
        ----------
        callback : collections.abc.Callable[[Stringable], object]
            Function to execute with the string.

        Returns
        -------
        orionis.support.types.Stringable
            The same Stringable instance.
        """
        # Call the callback with self, do not modify the string.
        callback(self)
        return self


def _pluralize_word(word: str) -> str:
    """
    Apply the supported regular English plural suffix rules.

    Parameters
    ----------
    word : str
        Word whose original case is preserved.

    Returns
    -------
    str
        Word with a regular plural suffix.
    """
    lower = word.lower()
    if lower.endswith(("s", "sh", "ch", "x", "z")):
        return word + "es"
    if lower.endswith("y") and len(word) > 1 and lower[-2] not in "aeiou":
        return word[:-1] + "ies"
    if lower.endswith("f"):
        return word[:-1] + "ves"
    if lower.endswith("fe"):
        return word[:-2] + "ves"
    return word + "s"


def _replacement_values[T](value: T | list[T], kind: type[T], name: str) -> list[T]:
    """
    Validate and normalize one replacement parameter.

    Parameters
    ----------
    value : ``T`` or list[``T``]
        Scalar value or explicit sequence of values.
    kind : type[``T``]
        Required type of each value.
    name : str
        Public parameter label used in errors.

    Returns
    -------
    list[``T``]
        Nonempty sequence whose values have the required type.

    Raises
    ------
    TypeError
        If the scalar or a sequence member has an incompatible type.
    ValueError
        If an explicit list is empty.
    """
    if isinstance(value, kind):
        return [value]
    if not isinstance(value, list) or any(not isinstance(item, kind) for item in value):
        message = (
            f"{name} must be a {kind.__name__} or a list of {kind.__name__} values."
        )
        raise TypeError(message)
    if not value:
        message = f"{name} list cannot be empty."
        raise ValueError(message)
    return value


def _replace_portion(
    value: str,
    replacement: str,
    offset: int,
    length: int,
) -> str:
    """
    Replace one bounded portion of the current string.

    Parameters
    ----------
    value : str
        Current string after preceding replacements.
    replacement : str
        Literal text to insert.
    offset : int
        Position counted from the start, or from the end when negative.
    length : int
        Nonnegative number of characters to remove; zero inserts text.

    Returns
    -------
    str
        String with the selected portion replaced.

    Raises
    ------
    ValueError
        If the offset is outside the string boundaries.
    """
    if abs(offset) > len(value):
        message = f"Offset {offset} is out of bounds for string of length {len(value)}."
        raise ValueError(message)
    start = len(value) + offset if offset < 0 else offset
    end = min(start + length, len(value))
    return value[:start] + replacement + value[end:]
