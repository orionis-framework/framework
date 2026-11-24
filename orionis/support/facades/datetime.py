# ruff: noqa: PLR0913
# Preserve the component arguments of Pendulum's date and duration constructors.
"""Provide a high-level interface for date and time operations."""

from __future__ import annotations
import pendulum
import re
from dateutil.parser import parse as parse_flexible
from pendulum.formatting import Formatter
from pendulum.parsing import parse as parse_components
from pendulum.parsing.exceptions import ParserError
from datetime import UTC, date, datetime as stdlib_datetime, time
from typing import TYPE_CHECKING, ClassVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable


_FORMATTER = Formatter()
"""Parse date and time components from explicit Pendulum formats."""
_FORMAT_LITERALS = re.compile(r"\[[^\]]*\]|\\.")
"""Match bracketed literals and escaped characters in Pendulum formats."""


class DateTime:
    """
    Provide a high-level interface for date and time operations.

    All methods are class-level, using a configurable default timezone
    and locale backed by ``pendulum`` for immutable datetime arithmetic.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    # Default timezone and locale
    _timezone: str = "UTC"
    """Default timezone and locale."""
    _refresh_timezone: ClassVar[Callable[[], None] | None] = None
    """
    Refresh the default timezone from the active application.

    The application installs this callback when it loads its configuration.
    """
    _locale: str = "en"
    """Locale identifier: ``en``."""
    _zoneinfo_cache: ClassVar[dict[str, ZoneInfo]] = {}
    """Previously resolved time-zone objects indexed by zone name."""

    @classmethod
    def _loadConfig(
        cls,
        timezone_name: str | None = None,
        locale: str | None = None,
    ) -> None:
        """
        Load configuration for timezone and locale.

        Parameters
        ----------
        timezone_name : str | None, optional
            Name of the timezone (e.g., 'America/Mexico_City'). If None, uses
            the default.
        locale : str | None, optional
            Language code (e.g., 'es', 'en', 'fr'). If None, uses the default.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Set timezone if provided
        if timezone_name is not None:
            cls._setTimezone(timezone_name)
        # Set locale if provided
        if locale is not None:
            cls._setLocale(locale)

    @classmethod
    def _setTimezone(cls, timezone_name: str) -> None:
        """
        Set the default IANA timezone and cache its zone information.

        Parameters
        ----------
        timezone_name : str
            IANA timezone name.

        Returns
        -------
        None
            Store the validated timezone for subsequent calls.

        Raises
        ------
        ValueError
            If the name does not identify an available timezone.
        """
        try:
            zone = ZoneInfo(timezone_name)
        except (ValueError, ZoneInfoNotFoundError) as e:
            error_msg = f"Invalid timezone '{timezone_name}': {e}"
            raise ValueError(error_msg) from e
        cls._timezone = timezone_name
        cls._zoneinfo_cache = {timezone_name: zone}

    @classmethod
    def _setLocale(cls, locale: str) -> None:
        """
        Set the default locale for date and time formatting.

        Parameters
        ----------
        locale : str
            Language code (e.g., 'es', 'en', 'fr').

        Returns
        -------
        None
            This method does not return a value.
        """
        # Set the locale for pendulum and store it in the class variable
        pendulum.set_locale(locale)
        cls._locale = locale

    @classmethod
    def getTimezone(cls) -> str:
        """
        Read the timezone from the active application configuration.

        Returns
        -------
        str
            Configured IANA timezone name, initially UTC.
        """
        if cls._refresh_timezone is not None:
            cls._refresh_timezone()
        return cls._timezone

    @classmethod
    def getLocale(cls) -> str:
        """
        Return the configured locale.

        Returns
        -------
        str
            The currently configured locale code.
        """
        return cls._locale

    @classmethod
    def getZoneInfo(cls) -> ZoneInfo:
        """
        Resolve the configured timezone as a standard-library zone.

        Returns
        -------
        zoneinfo.ZoneInfo
            Cached zone for the current application setting.
        """
        _tz = cls.getTimezone()
        cached = cls._zoneinfo_cache.get(_tz)
        if cached is None:
            cached = ZoneInfo(_tz)
            cls._zoneinfo_cache[_tz] = cached
        return cached

    @classmethod
    def now(cls, tz: str | None = None) -> pendulum.DateTime:
        """
        Return the current time in the selected timezone.

        Parameters
        ----------
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Current timezone-aware datetime.
        """
        return pendulum.now(tz if tz is not None else cls.getTimezone())

    @classmethod
    def today(cls, tz: str | None = None) -> pendulum.DateTime:
        """
        Return midnight today in the selected timezone.

        Parameters
        ----------
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Start of the current local date.
        """
        return pendulum.today(tz if tz is not None else cls.getTimezone())

    @classmethod
    def tomorrow(cls, tz: str | None = None) -> pendulum.DateTime:
        """
        Return midnight tomorrow in the selected timezone.

        Parameters
        ----------
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Start of the next local date.
        """
        return pendulum.tomorrow(tz if tz is not None else cls.getTimezone())

    @classmethod
    def yesterday(cls, tz: str | None = None) -> pendulum.DateTime:
        """
        Return midnight yesterday in the selected timezone.

        Parameters
        ----------
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Start of the previous local date.
        """
        return pendulum.yesterday(tz if tz is not None else cls.getTimezone())

    @classmethod
    def parse(
        cls,
        date_string: str,
        tz: str | None = None,
        *,
        strict: bool = True,
    ) -> pendulum.DateTime:
        """
        Parse a date or time in the selected timezone.

        Parameters
        ----------
        date_string : str
            Date or time text, optionally with a UTC offset, or the keyword ``now``.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.
        strict : bool, optional
            Allow only Pendulum syntax by default. Set to False for flexible dates.

        Returns
        -------
        ``pendulum.DateTime``
            Local datetime. A time without a date uses today in the selected zone.

        Raises
        ------
        ValueError
            If the text cannot be parsed with the selected mode.
        TypeError
            If the text describes a duration or interval instead of a date or time.
        """
        timezone = tz if tz is not None else cls.getTimezone()
        if date_string == "now":
            return cls.now(timezone)
        try:
            # Keep offsets on time-only ISO inputs until a calendar date is known.
            parsed = parse_components(date_string, exact=True)
        except ParserError:
            if strict:
                raise
            midnight = stdlib_datetime.combine(cls.now(timezone).date(), time.min)
            parsed = parse_flexible(date_string, default=midnight, yearfirst=True)

        if isinstance(parsed, time):
            parsed = stdlib_datetime.combine(cls.now(timezone).date(), parsed)
        elif isinstance(parsed, date) and not isinstance(parsed, stdlib_datetime):
            parsed = stdlib_datetime.combine(parsed, time.min)
        return cls.fromDatetime(parsed, timezone)

    @classmethod
    def fromFormat(
        cls,
        date_string: str,
        fmt: str,
        tz: str | None = None,
        locale: str | None = None,
    ) -> pendulum.DateTime:
        """
        Parse formatted text and express the result in the selected timezone.

        Parameters
        ----------
        date_string : str
            Text matching the supplied format.
        fmt : str
            Pendulum format tokens.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.
        locale : str or None, optional
            Language for localized tokens. Defaults to the configured locale.

        Returns
        -------
        ``pendulum.DateTime``
            Local datetime representing the instant encoded by an offset or Unix time.

        Raises
        ------
        ValueError
            If the text does not match the format or its components are invalid.
        """
        timezone = tz if tz is not None else cls.getTimezone()
        parts = _FORMATTER.parse(
            date_string, fmt, cls.now(timezone),
            locale=locale if locale is not None else cls._locale,
        )
        # Pendulum expands Unix timestamps into UTC components without a tz.
        tokens = _FORMAT_LITERALS.sub("", fmt)
        if "X" in tokens or "x" in tokens:
            parts["tz"] = "UTC"
        elif parts["tz"] is None:
            parts["tz"] = timezone
        return pendulum.datetime(**parts, fold=0).in_timezone(timezone)

    @classmethod
    def local(
        cls,
        year: int,
        month: int = 1,
        day: int = 1,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
    ) -> pendulum.DateTime:
        """
        Create a datetime object in the local system timezone.

        Parameters
        ----------
        year : int
            Year component.
        month : int, optional
            Month component, by default 1.
        day : int, optional
            Day component, by default 1.
        hour : int, optional
            Hour component, by default 0.
        minute : int, optional
            Minute component, by default 0.
        second : int, optional
            Second component, by default 0.
        microsecond : int, optional
            Microsecond component, by default 0.

        Returns
        -------
        ``pendulum.DateTime``
            Datetime object expressed in the local system timezone.
        """
        return pendulum.local(
            year,
            month,
            day,
            hour,
            minute,
            second,
            microsecond,
        )

    @classmethod
    def naive(
        cls,
        year: int,
        month: int = 1,
        day: int = 1,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
    ) -> pendulum.DateTime:
        """
        Create a timezone-naive datetime from calendar components.

        Parameters
        ----------
        year : int
            Calendar year.
        month : int, optional
            Month from 1 to 12.
        day : int, optional
            Day of the month.
        hour : int, optional
            Hour from 0 to 23.
        minute : int, optional
            Minute from 0 to 59.
        second : int, optional
            Second from 0 to 59.
        microsecond : int, optional
            Fractional second in microseconds.

        Returns
        -------
        ``pendulum.DateTime``
            Wall time with the fold flag set to the first occurrence.
        """
        return pendulum.naive(
            year,
            month,
            day,
            hour,
            minute,
            second,
            microsecond,
            fold=0,
        )

    @classmethod
    def fromTimestamp(
        cls,
        timestamp: float,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Express a Unix timestamp in the selected timezone.

        Parameters
        ----------
        timestamp : float
            Seconds since the Unix epoch.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Timezone-aware datetime representing the supplied instant.
        """
        _tz = tz if tz is not None else cls.getTimezone()
        return pendulum.from_timestamp(timestamp, tz=_tz)

    @classmethod
    def fromDatetime(
        cls,
        dt: stdlib_datetime | pendulum.DateTime,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Interpret a naive datetime locally or convert an aware instant.

        Parameters
        ----------
        dt : datetime.datetime
            Datetime to convert. Naive inputs retain their fold flag.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Timezone-aware datetime in the selected zone.

        Raises
        ------
        TypeError
            If the input is not a datetime.
        """
        timezone = tz if tz is not None else cls.getTimezone()

        if not isinstance(dt, stdlib_datetime):
            error_msg = f"Unsupported type: {type(dt)}"
            raise TypeError(error_msg)
        if dt.utcoffset() is None:
            return pendulum.DateTime.instance(dt.replace(tzinfo=None), tz=timezone)
        if isinstance(dt, pendulum.DateTime) and dt.timezone_name == timezone:
            return dt
        return pendulum.instance(dt.astimezone(UTC)).in_timezone(timezone)

    @classmethod
    def datetime(
        cls,
        year: int,
        month: int = 1,
        day: int = 1,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Create a datetime from wall-clock components in the selected zone.

        Parameters
        ----------
        year : int
            Calendar year.
        month : int, optional
            Month from 1 to 12.
        day : int, optional
            Day of the month.
        hour : int, optional
            Hour from 0 to 23.
        minute : int, optional
            Minute from 0 to 59.
        second : int, optional
            Second from 0 to 59.
        microsecond : int, optional
            Fractional second in microseconds.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Timezone-aware datetime using the first occurrence of a repeated hour.
        """
        return pendulum.datetime(
            year,
            month,
            day,
            hour,
            minute,
            second,
            microsecond,
            tz=tz if tz is not None else cls.getTimezone(),
            fold=0,
        )

    @classmethod
    def duration(
        cls,
        *,
        days: float = 0,
        seconds: float = 0,
        microseconds: float = 0,
        milliseconds: float = 0,
        minutes: float = 0,
        hours: float = 0,
        weeks: float = 0,
        years: float = 0,
        months: float = 0,
    ) -> pendulum.Duration:
        """
        Create a Duration instance representing a span of time.

        Parameters
        ----------
        days : float, optional
            Number of days, by default 0.
        seconds : float, optional
            Number of seconds, by default 0.
        microseconds : float, optional
            Number of microseconds, by default 0.
        milliseconds : float, optional
            Number of milliseconds, by default 0.
        minutes : float, optional
            Number of minutes, by default 0.
        hours : float, optional
            Number of hours, by default 0.
        weeks : float, optional
            Number of weeks, by default 0.
        years : float, optional
            Number of years, by default 0.
        months : float, optional
            Number of months, by default 0.

        Returns
        -------
        ``pendulum.Duration``
            The resulting Duration instance.
        """
        return pendulum.duration(
            days=days,
            seconds=seconds,
            microseconds=microseconds,
            milliseconds=milliseconds,
            minutes=minutes,
            hours=hours,
            weeks=weeks,
            years=years,
            months=months,
        )

    @classmethod
    def interval(
        cls,
        start: pendulum.DateTime,
        end: pendulum.DateTime,
        *,
        absolute: bool = False,
    ) -> pendulum.Interval:
        """
        Create an Interval instance between two datetimes.

        Parameters
        ----------
        start : ``pendulum.DateTime``
            The start of the interval.
        end : ``pendulum.DateTime``
            The end of the interval.
        absolute : bool, optional
            Whether to force a positive interval regardless of the order
            of ``start`` and ``end``, by default False.

        Returns
        -------
        ``pendulum.Interval``
            The resulting Interval instance.
        """
        return pendulum.interval(start, end, absolute=absolute)

    @classmethod
    def startOf(
        cls,
        unit: str,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the calendar unit in the selected timezone.

        Parameters
        ----------
        unit : str
            Pendulum calendar unit, such as day, week, month, or year.
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local start of the calendar unit containing the instant.
        """
        local = cls.now(tz) if dt is None else cls.fromDatetime(dt, tz)
        return local.start_of(unit)

    @classmethod
    def endOf(
        cls,
        unit: str,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the calendar unit in the selected timezone.

        Parameters
        ----------
        unit : str
            Pendulum calendar unit, such as day, week, month, or year.
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local end of the calendar unit containing the instant.
        """
        local = cls.now(tz) if dt is None else cls.fromDatetime(dt, tz)
        return local.end_of(unit)

    @classmethod
    def startOfDay(
        cls,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the day in the selected timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local start of the day containing the instant.
        """
        return cls.startOf("day", dt, tz)

    @classmethod
    def endOfDay(
        cls,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the day in the selected timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local end of the day containing the instant.
        """
        return cls.endOf("day", dt, tz)

    @classmethod
    def convertToLocal(
        cls,
        dt: str | stdlib_datetime | pendulum.DateTime,
    ) -> pendulum.DateTime:
        """
        Convert text or a datetime to the application timezone.

        Parameters
        ----------
        dt : str or datetime.datetime
            Input to parse or convert. A naive value represents local wall time.

        Returns
        -------
        ``pendulum.DateTime``
            Datetime expressed in the application timezone.

        Raises
        ------
        ValueError
            If the text is invalid.
        TypeError
            If the input does not represent a date or time.
        """
        if isinstance(dt, str):
            return cls.parse(dt)
        return cls.fromDatetime(dt)

    @classmethod
    def formatLocal(
        cls,
        dt: str | stdlib_datetime | pendulum.DateTime | None = None,
        format_string: str = "YYYY-MM-DD HH:mm:ss",
    ) -> str:
        """
        Format a date in the configured timezone and locale.

        Parameters
        ----------
        dt : str | datetime.datetime | ``pendulum.DateTime`` | None, optional
            Date to format. If None, uses now().
        format_string : str, optional
            Output format string.

        Returns
        -------
        str
            The formatted date string.
        """
        local = cls.now() if dt is None else cls.convertToLocal(dt)
        return local.format(format_string, locale=cls._locale)

    @classmethod
    def startOfWeek(
        cls,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the week in the selected timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local start of the week containing the instant.
        """
        return cls.startOf("week", dt, tz)

    @classmethod
    def endOfWeek(
        cls,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the week in the selected timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local end of the week containing the instant.
        """
        return cls.endOf("week", dt, tz)

    @classmethod
    def startOfMonth(
        cls,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the month in the selected timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local start of the month containing the instant.
        """
        return cls.startOf("month", dt, tz)

    @classmethod
    def endOfMonth(
        cls,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the month in the selected timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local end of the month containing the instant.
        """
        return cls.endOf("month", dt, tz)

    @classmethod
    def startOfYear(
        cls,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the year in the selected timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local start of the year containing the instant.
        """
        return cls.startOf("year", dt, tz)

    @classmethod
    def endOfYear(
        cls,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the year in the selected timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to locate on the selected calendar. Defaults to the current time.
        tz : str or None, optional
            IANA timezone name. Defaults to the application timezone.

        Returns
        -------
        ``pendulum.DateTime``
            Local end of the year containing the instant.
        """
        return cls.endOf("year", dt, tz)

    @classmethod
    def addDays(cls, dt: pendulum.DateTime, days: int) -> pendulum.DateTime:
        """
        Add days to a given date.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original date.
        days : int
            Number of days to add.

        Returns
        -------
        ``pendulum.DateTime``
            The resulting date after adding the specified days.
        """
        # Add the specified number of days to the date
        return dt.add(days=days)

    @classmethod
    def addHours(cls, dt: pendulum.DateTime, hours: int) -> pendulum.DateTime:
        """
        Add hours to a given datetime.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        hours : int
            Number of hours to add.

        Returns
        -------
        ``pendulum.DateTime``
            The resulting datetime after adding the specified hours.
        """
        # Add the specified number of hours to the datetime
        return dt.add(hours=hours)

    @classmethod
    def addMinutes(
        cls,
        dt: pendulum.DateTime,
        minutes: int,
    ) -> pendulum.DateTime:
        """
        Add minutes to a given datetime.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        minutes : int
            Number of minutes to add.

        Returns
        -------
        ``pendulum.DateTime``
            The resulting datetime after adding the specified minutes.
        """
        # Add the specified number of minutes to the datetime
        return dt.add(minutes=minutes)

    @classmethod
    def diffInDays(
        cls,
        dt1: pendulum.DateTime,
        dt2: pendulum.DateTime,
    ) -> int:
        """
        Calculate the difference in days between two dates.

        Parameters
        ----------
        dt1 : ``pendulum.DateTime``
            The first date.
        dt2 : ``pendulum.DateTime``
            The second date.

        Returns
        -------
        int
            The difference in days between the two dates.
        """
        # Return the number of complete elapsed days.
        return abs(int((dt2.timestamp() - dt1.timestamp()) / 86400))

    @classmethod
    def diffInHours(
        cls,
        dt1: pendulum.DateTime,
        dt2: pendulum.DateTime,
    ) -> int:
        """
        Compute the difference in hours between two dates.

        Parameters
        ----------
        dt1 : ``pendulum.DateTime``
            The first datetime.
        dt2 : ``pendulum.DateTime``
            The second datetime.

        Returns
        -------
        int
            The difference in hours between the two dates.
        """
        # Return the number of complete elapsed hours.
        return abs(int((dt2.timestamp() - dt1.timestamp()) / 3600))

    @classmethod
    def isWeekend(
        cls,
        dt: pendulum.DateTime | None = None,
    ) -> bool:
        """
        Check whether the local calendar date falls on a weekend.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to check. Defaults to the current time.

        Returns
        -------
        bool
            True for Saturday or Sunday in the application timezone.
        """
        local = cls.now() if dt is None else cls.convertToLocal(dt)
        return local.day_of_week in (pendulum.SATURDAY, pendulum.SUNDAY)

    @classmethod
    def isToday(cls, dt: pendulum.DateTime) -> bool:
        """
        Check whether an instant falls on today in the application timezone.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            Datetime to compare.

        Returns
        -------
        bool
            True when both local calendar dates match.
        """
        # Read the current date in the configured timezone.
        today = pendulum.today(cls.getTimezone())
        dt = cls.convertToLocal(dt)
        return dt.year == today.year and dt.month == today.month and dt.day == today.day

    @classmethod
    def isFuture(cls, dt: pendulum.DateTime) -> bool:
        """
        Check whether a datetime falls after the current instant.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            Datetime to compare.

        Returns
        -------
        bool
            True when the datetime is strictly after the current time.
        """
        return cls.fromDatetime(dt).astimezone(UTC) > cls.now("UTC")

    @classmethod
    def isPast(cls, dt: pendulum.DateTime) -> bool:
        """
        Check whether a datetime falls before the current instant.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            Datetime to compare.

        Returns
        -------
        bool
            True when the datetime is strictly before the current time.
        """
        return cls.fromDatetime(dt).astimezone(UTC) < cls.now("UTC")

    @classmethod
    def isLeapYear(cls, dt: pendulum.DateTime | None = None) -> bool:
        """
        Check whether the local calendar year is a leap year.

        Parameters
        ----------
        dt : ``pendulum.DateTime`` or None, optional
            Instant to check. Defaults to the current time.

        Returns
        -------
        bool
            True when the year in the application timezone is a leap year.
        """
        local = cls.now() if dt is None else cls.convertToLocal(dt)
        return local.is_leap_year()

    @classmethod
    def isBirthday(
        cls,
        dt: pendulum.DateTime,
        other: pendulum.DateTime | None = None,
    ) -> bool:
        """
        Compare month and day on the application calendar.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            Birth date to compare.
        other : ``pendulum.DateTime`` or None, optional
            Reference datetime. Defaults to the current time.

        Returns
        -------
        bool
            True when the local month and day match.
        """
        reference = cls.now() if other is None else cls.convertToLocal(other)
        return cls.convertToLocal(dt).is_birthday(reference)

    @classmethod
    def closest(
        cls,
        dt: pendulum.DateTime,
        *others: pendulum.DateTime,
    ) -> pendulum.DateTime:
        """
        Return the datetime closest to the given one among the candidates.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The reference datetime.
        *others : ``pendulum.DateTime``
            Candidate datetimes to compare against the reference.

        Returns
        -------
        ``pendulum.DateTime``
            The candidate closest to ``dt``.
        """
        return dt.closest(*others)

    @classmethod
    def farthest(
        cls,
        dt: pendulum.DateTime,
        *others: pendulum.DateTime,
    ) -> pendulum.DateTime:
        """
        Return the datetime farthest from the given one among the candidates.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The reference datetime.
        *others : ``pendulum.DateTime``
            Candidate datetimes to compare against the reference.

        Returns
        -------
        ``pendulum.DateTime``
            The candidate farthest from ``dt``.
        """
        return dt.farthest(*others)

    @classmethod
    def add(
        cls,
        dt: pendulum.DateTime,
        *,
        years: int = 0,
        months: int = 0,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: float = 0,
        microseconds: int = 0,
    ) -> pendulum.DateTime:
        """
        Add a combination of time units to a given date.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        years : int, optional
            Number of years to add, by default 0.
        months : int, optional
            Number of months to add, by default 0.
        weeks : int, optional
            Number of weeks to add, by default 0.
        days : int, optional
            Number of days to add, by default 0.
        hours : int, optional
            Number of hours to add, by default 0.
        minutes : int, optional
            Number of minutes to add, by default 0.
        seconds : float, optional
            Number of seconds to add, by default 0.
        microseconds : int, optional
            Number of microseconds to add, by default 0.

        Returns
        -------
        ``pendulum.DateTime``
            The resulting datetime after adding the specified units.
        """
        return dt.add(
            years=years,
            months=months,
            weeks=weeks,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            microseconds=microseconds,
        )

    @classmethod
    def subtract(
        cls,
        dt: pendulum.DateTime,
        *,
        years: int = 0,
        months: int = 0,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: float = 0,
        microseconds: int = 0,
    ) -> pendulum.DateTime:
        """
        Subtract a combination of time units from a given date.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        years : int, optional
            Number of years to subtract, by default 0.
        months : int, optional
            Number of months to subtract, by default 0.
        weeks : int, optional
            Number of weeks to subtract, by default 0.
        days : int, optional
            Number of days to subtract, by default 0.
        hours : int, optional
            Number of hours to subtract, by default 0.
        minutes : int, optional
            Number of minutes to subtract, by default 0.
        seconds : float, optional
            Number of seconds to subtract, by default 0.
        microseconds : int, optional
            Number of microseconds to subtract, by default 0.

        Returns
        -------
        ``pendulum.DateTime``
            The resulting datetime after subtracting the specified units.
        """
        return dt.subtract(
            years=years,
            months=months,
            weeks=weeks,
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            microseconds=microseconds,
        )

    @classmethod
    def diff(
        cls,
        dt1: pendulum.DateTime,
        dt2: pendulum.DateTime | None = None,
        *,
        absolute: bool = True,
    ) -> pendulum.Interval:
        """
        Return the full Interval between two dates.

        Parameters
        ----------
        dt1 : ``pendulum.DateTime``
            The reference datetime.
        dt2 : ``pendulum.DateTime`` | None, optional
            The datetime to compare against. If None, uses the current
            datetime in the configured timezone.
        absolute : bool, optional
            Whether to return an always-positive interval, by default True.

        Returns
        -------
        ``pendulum.Interval``
            The Interval instance exposing in_years()/in_months()/
            in_weeks()/in_days()/in_hours()/in_minutes()/in_seconds().
        """
        return dt1.diff(dt2, abs=absolute)

    @classmethod
    def diffForHumans(
        cls,
        dt: pendulum.DateTime,
        other: pendulum.DateTime | None = None,
        *,
        absolute: bool = False,
        locale: str | None = None,
    ) -> str:
        """
        Return a human-readable difference between two dates.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The reference datetime.
        other : ``pendulum.DateTime`` | None, optional
            The datetime to compare against. If None, uses the current
            datetime.
        absolute : bool, optional
            Whether to remove modifiers such as 'ago' or 'from now',
            by default False.
        locale : str | None, optional
            Locale to use for the phrase. If None, uses the configured
            default.

        Returns
        -------
        str
            A human-readable string such as '3 weeks ago'.
        """
        return dt.diff_for_humans(
            other,
            absolute=absolute,
            locale=locale if locale is not None else cls._locale,
        )

    @classmethod
    def next(
        cls,
        dt: pendulum.DateTime,
        day_of_week: int | None = None,
        *,
        keep_time: bool = False,
    ) -> pendulum.DateTime:
        """
        Move to the next occurrence of the given day of the week.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        day_of_week : int | None, optional
            Target day of the week (e.g. ``pendulum.WEDNESDAY``). If None,
            uses the day of the week of ``dt``.
        keep_time : bool, optional
            Whether to keep the time component instead of resetting it
            to midnight, by default False.

        Returns
        -------
        ``pendulum.DateTime``
            The datetime of the next matching day.
        """
        return dt.next(day_of_week, keep_time=keep_time)

    @classmethod
    def previous(
        cls,
        dt: pendulum.DateTime,
        day_of_week: int | None = None,
        *,
        keep_time: bool = False,
    ) -> pendulum.DateTime:
        """
        Move to the previous occurrence of the given day of the week.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        day_of_week : int | None, optional
            Target day of the week (e.g. ``pendulum.WEDNESDAY``). If None,
            uses the day of the week of ``dt``.
        keep_time : bool, optional
            Whether to keep the time component instead of resetting it
            to midnight, by default False.

        Returns
        -------
        ``pendulum.DateTime``
            The datetime of the previous matching day.
        """
        return dt.previous(day_of_week, keep_time=keep_time)

    @classmethod
    def average(
        cls,
        dt1: pendulum.DateTime,
        dt2: pendulum.DateTime | None = None,
    ) -> pendulum.DateTime:
        """
        Return the middle datetime between two dates.

        Parameters
        ----------
        dt1 : ``pendulum.DateTime``
            The reference datetime.
        dt2 : ``pendulum.DateTime`` | None, optional
            The datetime to average with. If None, uses the current
            datetime in the configured timezone.

        Returns
        -------
        ``pendulum.DateTime``
            The datetime halfway between ``dt1`` and ``dt2``.
        """
        return dt1.average(dt2)

    @classmethod
    def firstOf(
        cls,
        dt: pendulum.DateTime,
        unit: str,
        day_of_week: int | None = None,
    ) -> pendulum.DateTime:
        """
        Return the first day of the given unit, optionally on a weekday.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        unit : str
            Unit of time: 'month', 'quarter' or 'year'.
        day_of_week : int | None, optional
            Constrain the result to a specific day of the week
            (e.g. ``pendulum.MONDAY``). If None, returns the first day
            of the unit regardless of weekday.

        Returns
        -------
        ``pendulum.DateTime``
            The resulting datetime.
        """
        return dt.first_of(unit, day_of_week)

    @classmethod
    def lastOf(
        cls,
        dt: pendulum.DateTime,
        unit: str,
        day_of_week: int | None = None,
    ) -> pendulum.DateTime:
        """
        Return the last day of the given unit, optionally on a weekday.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        unit : str
            Unit of time: 'month', 'quarter' or 'year'.
        day_of_week : int | None, optional
            Constrain the result to a specific day of the week
            (e.g. ``pendulum.FRIDAY``). If None, returns the last day
            of the unit regardless of weekday.

        Returns
        -------
        ``pendulum.DateTime``
            The resulting datetime.
        """
        return dt.last_of(unit, day_of_week)

    @classmethod
    def nthOf(
        cls,
        dt: pendulum.DateTime,
        unit: str,
        nth: int,
        day_of_week: int,
    ) -> pendulum.DateTime:
        """
        Return the n-th occurrence of a weekday within the given unit.

        Parameters
        ----------
        dt : ``pendulum.DateTime``
            The original datetime.
        unit : str
            Unit of time: 'month', 'quarter' or 'year'.
        nth : int
            The occurrence index to look for (1-based).
        day_of_week : int
            Target day of the week (e.g. ``pendulum.MONDAY``).

        Returns
        -------
        ``pendulum.DateTime``
            The resulting datetime.

        Raises
        ------
        ``PendulumException``
            If the given occurrence does not exist within the unit.
        """
        return dt.nth_of(unit, nth, day_of_week)
