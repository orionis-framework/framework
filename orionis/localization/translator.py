from __future__ import annotations
import re
from typing import TYPE_CHECKING
from orionis.localization.contracts.translator import ITranslator
from orionis.localization.exceptions import InvalidLocaleException

if TYPE_CHECKING:
    from orionis.localization.contracts.loader import ITranslationLoader
    from orionis.localization.contracts.repository import ITranslationRepository
    from orionis.localization.types import MissingKeyHandler

# Safe locale codes: alphanumeric groups separated by "-" or "_".
_LOCALE_PATTERN: re.Pattern[str] = re.compile(
    r"^[A-Za-z0-9]+(?:[_-][A-Za-z0-9]+)*$",
)

# Explicit exact condition on a plural segment, e.g. "{0} none".
_EXACT_PATTERN: re.Pattern[str] = re.compile(
    r"^\{([^}]*)\}(.*)$",
    re.DOTALL,
)

# Explicit range condition on a plural segment, e.g. "[2,*] many".
_RANGE_PATTERN: re.Pattern[str] = re.compile(
    r"^\[([^\],]*),([^\]]*)\](.*)$",
    re.DOTALL,
)

class Translator(ITranslator):
    """
    Resolve translation lines for the active locale.

    The translator performs O(1) lookups against the in-memory
    repository, falls back to the configured fallback locale, applies
    style ``:name`` parameter replacement, and selects
    pluralized segments through :meth:`choice`.

    Notes
    -----
    The provider binds a single instance for the whole process and the
    class uses no lock, so :meth:`setLocale`, :meth:`missing`,
    :meth:`reload`, :meth:`forget` and :meth:`flush` are global side
    effects visible to every concurrent task. Pass an explicit
    ``locale`` to :meth:`get`, :meth:`has` or :meth:`choice` to select a
    language for a single call instead.
    """

    __slots__ = ("_fallback", "_loader", "_locale", "_missing", "_repository")

    def __init__(
        self,
        *,
        locale: str,
        fallback: str,
        loader: ITranslationLoader,
        repository: ITranslationRepository,
    ) -> None:
        """
        Initialize the translator with its locales and collaborators.

        Parameters
        ----------
        locale : str
            Active locale code.
        fallback : str
            Locale used when a translation is missing.
        loader : ITranslationLoader
            Loader used to discover the available locales.
        repository : ITranslationRepository
            In-memory cache resolving translation maps per locale.

        Returns
        -------
        None

        Raises
        ------
        InvalidLocaleException
            If either locale code is malformed.
        """
        self._loader = loader
        self._repository = repository
        self._locale = self.__assertLocale(locale)
        self._fallback = self.__assertLocale(fallback)
        self._missing: MissingKeyHandler | None = None

    # ── Translation resolution ───────────────────────────────────────────────

    def get(
        self,
        key: str,
        locale: str | None = None,
        **replace: object,
    ) -> str:
        """
        Retrieve the translation line registered under *key*.

        The lookup order is the requested locale first, then the
        fallback locale, and finally the key itself when no translation
        exists. Placeholders in the ``:name`` form are substituted with
        the values provided in *replace*.

        Parameters
        ----------
        key : str
            Translation key, either a literal source text or a
            dot-notated grouped key such as ``validation.required``.
        locale : str | None, optional
            Locale to translate into, or ``None`` for the active locale.
        **replace : object
            Placeholder values substituted into the resolved line.

        Returns
        -------
        str
            Translated line, or the key itself when missing.

        Raises
        ------
        InvalidLocaleException
            If an explicit locale is malformed.
        """
        target = self.__assertLocale(locale) if locale is not None else self._locale

        # Resolve from the requested locale, then from the fallback.
        line = self._repository.get(target).get(key)
        if line is None and target != self._fallback:
            line = self._repository.get(self._fallback).get(key)

        # Delegate to the missing-key handler or echo the key back.
        if line is None:
            line = self.__resolveMissing(key, target)

        # Interpolate placeholders only when parameters were provided.
        if replace:
            return self.__applyReplacements(line, replace)
        return line

    def has(
        self,
        key: str,
        locale: str | None = None,
        *,
        fallback: bool = True,
    ) -> bool:
        """
        Determine whether a translation exists for *key*.

        Parameters
        ----------
        key : str
            Translation key to check.
        locale : str | None, optional
            Locale to inspect, or ``None`` for the active locale.
        fallback : bool, optional
            Whether the fallback locale is also inspected.

        Returns
        -------
        bool
            True when a translation line is registered for the key.

        Raises
        ------
        InvalidLocaleException
            If an explicit locale is malformed.
        """
        target = self.__assertLocale(locale) if locale is not None else self._locale

        # Check the requested locale before touching the fallback.
        if key in self._repository.get(target):
            return True
        if not fallback or target == self._fallback:
            return False
        return key in self._repository.get(self._fallback)

    def choice(
        self,
        key: str,
        count: int,
        locale: str | None = None,
        **replace: object,
    ) -> str:
        """
        Retrieve a pluralized translation line based on *count*.

        Segments are separated by ``|`` and may declare explicit
        conditions such as ``{0}``, ``{1}`` or ranges ``[2,*]``. When no
        explicit condition matches, the first segment is used for a
        count of one and the second segment otherwise. The ``:count``
        placeholder is always available in the selected segment.

        Parameters
        ----------
        key : str
            Translation key containing the pluralized segments.
        count : int
            Quantity used to select the proper segment. The value is
            used as received: explicit conditions compare it against
            their numeric bounds and the positional rule tests
            ``count == 1``. No coercion or validation is applied, so a
            non-numeric quantity propagates the comparison ``TypeError``
            raised by Python.
        locale : str | None, optional
            Locale to translate into, or ``None`` for the active locale.
        **replace : object
            Placeholder values substituted into the selected segment.

        Returns
        -------
        str
            Pluralized and interpolated translation line.

        Raises
        ------
        InvalidLocaleException
            If an explicit locale is malformed.
        """
        # Resolve the raw line and split it into plural segments.
        segments = self.get(key, locale).split("|")

        # Prefer explicit {n} / [a,b] conditions over positional rules.
        chosen = self.__matchExplicitSegment(segments, count)
        if chosen is None:
            chosen = self.__matchPluralSegment(segments, count)

        # Always expose :count to the selected segment.
        replace.setdefault("count", count)
        return self.__applyReplacements(chosen, replace)

    # ── Locale management ────────────────────────────────────────────────────

    def setLocale(self, locale: str) -> None:
        """
        Change the active locale at runtime.

        Parameters
        ----------
        locale : str
            Locale code to activate.

        Returns
        -------
        None

        Raises
        ------
        InvalidLocaleException
            If the locale is malformed.
        """
        self._locale = self.__assertLocale(locale)

    def getLocale(self) -> str:
        """
        Return the active locale.

        Returns
        -------
        str
            Locale code currently in use.
        """
        return self._locale

    def availableLocales(self) -> tuple[str, ...]:
        """
        Return every locale with at least one translation source.

        Returns
        -------
        tuple[str, ...]
            Sorted locale codes discovered in the language path.
        """
        return self._loader.availableLocales()

    # ── Cache management ─────────────────────────────────────────────────────

    def reload(self, locale: str | None = None) -> None:
        """
        Discard cached translations so they are re-read from disk.

        Parameters
        ----------
        locale : str | None, optional
            Locale to reload, or ``None`` to reload every locale.

        Returns
        -------
        None

        Raises
        ------
        InvalidLocaleException
            If an explicit locale is malformed.
        """
        if locale is None:
            self._repository.flush()
        else:
            self._repository.forget(self.__assertLocale(locale))

    def forget(self, locale: str) -> bool:
        """
        Discard the cached translations for a single locale.

        Parameters
        ----------
        locale : str
            Locale code whose cache entry must be removed.

        Returns
        -------
        bool
            True when an entry was removed, False otherwise.

        Raises
        ------
        InvalidLocaleException
            If the locale is malformed.
        """
        return self._repository.forget(self.__assertLocale(locale))

    def flush(self) -> None:
        """
        Discard every cached translation map.

        Returns
        -------
        None
        """
        self._repository.flush()

    def missing(self, handler: MissingKeyHandler | None) -> None:
        """
        Register a handler invoked when a translation key is missing.

        The handler receives the key and the locale, and may return a
        replacement line. When it returns ``None`` the key itself is
        used as the translation.

        Parameters
        ----------
        handler : MissingKeyHandler | None
            Callable invoked on missing keys, or ``None`` to remove the
            current handler.

        Returns
        -------
        None
        """
        self._missing = handler

    # ── Internal helpers ─────────────────────────────────────────────────────

    def __assertLocale(self, locale: str) -> str:
        """
        Validate a locale code and return it unchanged.

        Parameters
        ----------
        locale : str
            Locale code to validate.

        Returns
        -------
        str
            The validated locale code.

        Raises
        ------
        InvalidLocaleException
            If the locale is empty, malformed, or unsafe for path use.
        """
        # Reject codes that could escape the language path or be empty.
        if not isinstance(locale, str) or _LOCALE_PATTERN.match(locale) is None:
            error_msg = f"Invalid locale code: {locale!r}"
            raise InvalidLocaleException(error_msg)
        return locale

    def __resolveMissing(self, key: str, locale: str) -> str:
        """
        Resolve the line for a missing translation key.

        Parameters
        ----------
        key : str
            Translation key that produced no match.
        locale : str
            Locale in which the key was requested.

        Returns
        -------
        str
            Replacement line provided by the handler, or the key itself.
        """
        # Give the registered handler a chance to supply a line.
        if self._missing is not None:
            resolved = self._missing(key, locale)
            if isinstance(resolved, str):
                return resolved
        return key

    def __applyReplacements(self, line: str, replace: dict[str, object]) -> str:
        """
        Substitute placeholders into a translation line.

        Each parameter replaces its ``:key``, ``:Key``, and ``:KEY``
        variants with the raw, capitalized, and uppercased value
        respectively. Longer parameter names are applied first so they
        are never shadowed by shorter prefixes.

        Parameters
        ----------
        line : str
            Translation line containing the placeholders.
        replace : dict[str, object]
            Mapping of placeholder name to replacement value.

        Returns
        -------
        str
            Line with every placeholder substituted.
        """
        # Apply longer names first to avoid partial-prefix shadowing.
        for name in sorted(replace, key=len, reverse=True):
            value = str(replace[name])
            line = (
                line
                .replace(f":{name.upper()}", value.upper())
                .replace(f":{name.capitalize()}", value.capitalize())
                .replace(f":{name}", value)
            )
        return line

    def __matchExplicitSegment(
        self,
        segments: list[str],
        count: int,
    ) -> str | None:
        """
        Select the plural segment whose explicit condition matches.

        Parameters
        ----------
        segments : list[str]
            Plural segments split from the raw translation line.
        count : int
            Quantity evaluated against each condition.

        Returns
        -------
        str | None
            Matching segment body, or ``None`` when no explicit
            condition applies.
        """
        for segment in segments:
            # Exact conditions use braces, e.g. "{1} one apple".
            exact = _EXACT_PATTERN.match(segment)
            if exact is not None:
                condition = exact.group(1).strip()
                number = self.__asNumber(condition)
                if condition == "*" or (number is not None and number == count):
                    return exact.group(2).strip()
                continue

            # Range conditions use brackets, e.g. "[2,*] many apples".
            ranged = _RANGE_PATTERN.match(segment)
            if ranged is not None:
                lower = ranged.group(1).strip()
                upper = ranged.group(2).strip()
                lower_ok = self.__matchesBound(lower, count, lower_bound=True)
                upper_ok = self.__matchesBound(upper, count, lower_bound=False)
                if lower_ok and upper_ok:
                    return ranged.group(3).strip()

        return None

    def __matchPluralSegment(self, segments: list[str], count: int) -> str:
        """
        Select the plural segment through positional rules.

        Parameters
        ----------
        segments : list[str]
            Plural segments split from the raw translation line.
        count : int
            Quantity used to pick singular or plural form.

        Returns
        -------
        str
            Selected segment stripped of any explicit condition.
        """
        # Strip explicit conditions so positional selection stays clean.
        stripped = [self.__stripCondition(segment) for segment in segments]
        if len(stripped) == 1 or count == 1:
            return stripped[0]
        return stripped[1]

    def __stripCondition(self, segment: str) -> str:
        """
        Remove a leading explicit condition from a plural segment.

        Parameters
        ----------
        segment : str
            Raw plural segment possibly prefixed by a condition.

        Returns
        -------
        str
            Segment body without its condition, trimmed of whitespace.
        """
        exact = _EXACT_PATTERN.match(segment)
        if exact is not None:
            return exact.group(2).strip()
        ranged = _RANGE_PATTERN.match(segment)
        if ranged is not None:
            return ranged.group(3).strip()
        return segment.strip()

    def __asNumber(self, raw: str) -> float | None:
        """
        Parse a plural condition token into a number.

        Parameters
        ----------
        raw : str
            Condition token extracted from a plural segment.

        Returns
        -------
        float | None
            Numeric value, or ``None`` when the token is not numeric.
        """
        try:
            return float(raw)
        except ValueError:
            return None

    def __matchesBound(
        self,
        raw: str,
        count: int,
        *,
        lower_bound: bool,
    ) -> bool:
        """
        Evaluate one bound of an explicit range condition.

        Parameters
        ----------
        raw : str
            Bound token, either a number or the ``*`` wildcard.
        count : int
            Quantity evaluated against the bound.
        lower_bound : bool
            Whether the token is the lower bound of the range.

        Returns
        -------
        bool
            True when the count satisfies the bound.
        """
        if raw == "*":
            return True
        value = self.__asNumber(raw)
        if value is None:
            return False
        return count >= value if lower_bound else count <= value
