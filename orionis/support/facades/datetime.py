from __future__ import annotations
import pendulum
from datetime import datetime as stdlib_datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

class DateTime:
    """
    Provide a high-level interface for date and time operations.

    All methods are class-level, using a configurable default timezone
    and locale backed by `pendulum` for immutable datetime arithmetic.
    """

    # ruff: noqa: PLR0913

    __slots__ = ()

    # Default timezone and locale
    _timezone: str = "UTC"
    _locale: str = "en"
    _zoneinfo_cache: ClassVar[dict[str, ZoneInfo]] = {}

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
        Set the default timezone for the application.

        Parameters
        ----------
        timezone_name : str
            Name of the timezone (e.g., 'America/Mexico_City').

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the timezone is invalid.
        """
        try:
            # Check that the timezone name is recognized.
            pendulum.timezone(timezone_name)
            cls._timezone = timezone_name
            cls._zoneinfo_cache.clear()
        except pendulum.tz.zoneinfo.exceptions.InvalidTimezone as e:
            error_msg = f"Invalid timezone '{timezone_name}': {e}"
            raise ValueError(error_msg) from e

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
        cls._locale = locale
        pendulum.set_locale(locale)

    @classmethod
    def getTimezone(cls) -> str:
        """
        Return the configured timezone.

        Returns
        -------
        str
            The currently configured timezone name.
        """
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
        Return the ZoneInfo object for the configured timezone.

        Returns
        -------
        ZoneInfo
            The ZoneInfo instance corresponding to the configured timezone.
        """
        _tz = cls._timezone
        cached = cls._zoneinfo_cache.get(_tz)
        if cached is None:
            cached = ZoneInfo(_tz)
            cls._zoneinfo_cache[_tz] = cached
        return cached

    @classmethod
    def now(cls, tz: str | None = None) -> pendulum.DateTime:
        """
        Get the current date and time.

        Parameters
        ----------
        tz : str | None, optional
            Specific timezone name. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The current date and time in the specified or default timezone.
        """
        return pendulum.now(tz if tz is not None else cls._timezone)

    @classmethod
    def today(cls, tz: str | None = None) -> pendulum.Date:
        """
        Return the current date without time component.

        Parameters
        ----------
        tz : str | None, optional
            Specific timezone name. If None, uses the configured default.

        Returns
        -------
        pendulum.Date
            The current date in the specified or default timezone.
        """
        return pendulum.today(tz if tz is not None else cls._timezone)

    @classmethod
    def tomorrow(cls, tz: str | None = None) -> pendulum.Date:
        """
        Return tomorrow's date in the specified or default timezone.

        Parameters
        ----------
        tz : str | None, optional
            Timezone name. If None, uses the configured default.

        Returns
        -------
        pendulum.Date
            The date for tomorrow in the specified or default timezone.
        """
        return pendulum.tomorrow(tz if tz is not None else cls._timezone)

    @classmethod
    def yesterday(cls, tz: str | None = None) -> pendulum.Date:
        """
        Return the date for yesterday in the specified or default timezone.

        Parameters
        ----------
        tz : str | None, optional
            Timezone name. If None, uses the configured default.

        Returns
        -------
        pendulum.Date
            The date for yesterday in the specified or default timezone.
        """
        return pendulum.yesterday(tz if tz is not None else cls._timezone)

    @classmethod
    def parse(
        cls,
        date_string: str,
        tz: str | None = None,
        *,
        strict: bool = True,
    ) -> pendulum.DateTime:
        """
        Parse a date string and convert it to the configured timezone.

        Parameters
        ----------
        date_string : str
            Date string to parse.
        tz : str | None, optional
            Specific timezone name. If None, uses the configured default.
        strict : bool, optional
            Whether to use strict parsing mode, by default True.

        Returns
        -------
        pendulum.DateTime
            Parsed datetime object in the specified or default timezone.
        """
        # Determine the timezone to use
        timezone = tz if tz is not None else cls._timezone
        parsed_dt = pendulum.parse(date_string, strict=strict)

        # Convert to the configured timezone if necessary
        if parsed_dt.timezone_name != timezone:
            return parsed_dt.in_timezone(timezone)
        return parsed_dt

    @classmethod
    def fromFormat(
        cls,
        date_string: str,
        fmt: str,
        tz: str | None = None,
        locale: str | None = None,
    ) -> pendulum.DateTime:
        """
        Parse a date string using explicit format tokens.

        Parameters
        ----------
        date_string : str
            Date string to parse.
        fmt : str
            Format string using pendulum's custom tokens (e.g. 'YYYY-MM-DD').
        tz : str | None, optional
            Specific timezone name. If None, uses the configured default.
        locale : str | None, optional
            Locale to use while parsing localized tokens (e.g. month or day
            names). If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            Parsed datetime object in the specified or default timezone.
        """
        return pendulum.from_format(
            date_string,
            fmt,
            tz=tz if tz is not None else cls._timezone,
            locale=locale if locale is not None else cls._locale,
        )

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
        pendulum.DateTime
            Datetime object expressed in the local system timezone.
        """
        return pendulum.local(
            year, month, day, hour, minute, second, microsecond,
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
        Create a timezone-naive datetime object.

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
        pendulum.DateTime
            Datetime object with no timezone information attached.
        """
        return pendulum.naive(
            year, month, day, hour, minute, second, microsecond,
        )

    @classmethod
    def fromTimestamp(
        cls, timestamp: float, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Convert a Unix timestamp to a datetime in the configured timezone.

        Parameters
        ----------
        timestamp : int | float
            Unix timestamp to convert.
        tz : str | None, optional
            Specific timezone name. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            Datetime object in the specified or default timezone.
        """
        _tz = tz if tz is not None else cls._timezone
        return pendulum.from_timestamp(timestamp, tz=_tz)

    @classmethod
    def fromDatetime(
        cls,
        dt: stdlib_datetime | pendulum.DateTime,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Convert a standard datetime object to the configured timezone.

        Parameters
        ----------
        dt : datetime.datetime or pendulum.DateTime
            Datetime object to convert.
        tz : str or None, optional
            Specific timezone name. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            Datetime object in the specified or default timezone.

        Raises
        ------
        TypeError
            If the input type is not supported.
        """
        timezone = tz if tz is not None else cls._timezone

        # Most specific type first: pendulum.DateTime ⊂ stdlib_datetime
        if isinstance(dt, pendulum.DateTime):
            return dt.in_timezone(timezone)
        if isinstance(dt, stdlib_datetime):
            if dt.tzinfo is None:
                # Naive datetime: assume it is in the configured timezone
                return pendulum.instance(dt, tz=timezone)
            # Aware datetime: convert to the configured timezone
            return pendulum.instance(dt).in_timezone(timezone)
        error_msg = f"Unsupported type: {type(dt)}"
        raise TypeError(error_msg)

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
        Create a datetime object in the configured timezone.

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
        tz : str | None, optional
            Specific timezone name. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            Datetime object in the specified or default timezone.
        """
        return pendulum.datetime(
            year, month, day, hour, minute, second, microsecond,
            tz=tz if tz is not None else cls._timezone,
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
        pendulum.Duration
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
        start : pendulum.DateTime
            The start of the interval.
        end : pendulum.DateTime
            The end of the interval.
        absolute : bool, optional
            Whether to force a positive interval regardless of the order
            of ``start`` and ``end``, by default False.

        Returns
        -------
        pendulum.Interval
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
        Return the start of the given unit of time (e.g. 'hour', 'decade').

        Parameters
        ----------
        unit : str
            Unit of time: 'second', 'minute', 'hour', 'day', 'week',
            'month', 'quarter', 'year', 'decade' or 'century'.
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the start of the given unit.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.start_of(unit)

    @classmethod
    def endOf(
        cls,
        unit: str,
        dt: pendulum.DateTime | None = None,
        tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the given unit of time (e.g. 'hour', 'decade').

        Parameters
        ----------
        unit : str
            Unit of time: 'second', 'minute', 'hour', 'day', 'week',
            'month', 'quarter', 'year', 'decade' or 'century'.
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the end of the given unit.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.end_of(unit)

    @classmethod
    def startOfDay(
        cls, dt: pendulum.DateTime | None = None, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the day (00:00:00).

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the start of the day.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.start_of("day")

    @classmethod
    def endOfDay(
        cls, dt: pendulum.DateTime | None = None, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the day (23:59:59).

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the end of the day.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.end_of("day")

    @classmethod
    def convertToLocal(
        cls, dt: str | stdlib_datetime | pendulum.DateTime,
    ) -> pendulum.DateTime:
        """
        Convert a date to the configured local timezone.

        Parameters
        ----------
        dt : str | datetime.datetime | pendulum.DateTime
            Date to convert. Accepts string, standard datetime, or pendulum.DateTime.

        Returns
        -------
        pendulum.DateTime
            The date converted to the configured timezone.
        """
        _tz = cls._timezone
        # Most specific type first: pendulum.DateTime ⊂ stdlib_datetime
        if isinstance(dt, pendulum.DateTime):
            return dt.in_timezone(_tz)
        if isinstance(dt, str):
            return pendulum.parse(dt).in_timezone(_tz)
        if isinstance(dt, stdlib_datetime):
            return pendulum.instance(dt).in_timezone(_tz)
        error_msg = f"Unsupported type: {type(dt)}"
        raise TypeError(error_msg)

    @classmethod
    def formatLocal(
        cls,
        dt: pendulum.DateTime | None = None,
        format_string: str = "YYYY-MM-DD HH:mm:ss",
    ) -> str:
        """
        Format a date in the local timezone.

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            Date to format. If None, uses now().
        format_string : str, optional
            Output format string.

        Returns
        -------
        str
            The formatted date string.
        """
        # Format the current time when no datetime is provided.
        if dt is None:
            return cls.now().format(format_string)
        # Ensure dt is a pendulum.DateTime in the local timezone
        if not isinstance(dt, pendulum.DateTime):
            dt = cls.convertToLocal(dt)
        return dt.format(format_string)

    @classmethod
    def startOfWeek(
        cls, dt: pendulum.DateTime | None = None, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the week (Monday 00:00:00).

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the start of the week.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.start_of("week")

    @classmethod
    def endOfWeek(
        cls, dt: pendulum.DateTime | None = None, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the week (Sunday 23:59:59).

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the end of the week.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.end_of("week")

    @classmethod
    def startOfMonth(
        cls, dt: pendulum.DateTime | None = None, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the month (first day at 00:00:00).

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the start of the month.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.start_of("month")

    @classmethod
    def endOfMonth(
        cls, dt: pendulum.DateTime | None = None, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the month (last day at 23:59:59).

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the end of the month.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.end_of("month")

    @classmethod
    def startOfYear(
        cls, dt: pendulum.DateTime | None = None, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the start of the year (January 1st at 00:00:00).

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the start of the year.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.start_of("year")

    @classmethod
    def endOfYear(
        cls, dt: pendulum.DateTime | None = None, tz: str | None = None,
    ) -> pendulum.DateTime:
        """
        Return the end of the year (December 31st at 23:59:59).

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to use. If None, uses the current datetime.
        tz : str | None, optional
            The timezone to use. If None, uses the configured default.

        Returns
        -------
        pendulum.DateTime
            The datetime at the end of the year.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(tz if tz is not None else cls._timezone)
        return dt.end_of("year")

    @classmethod
    def addDays(cls, dt: pendulum.DateTime, days: int) -> pendulum.DateTime:
        """
        Add days to a given date.

        Parameters
        ----------
        dt : pendulum.DateTime
            The original date.
        days : int
            Number of days to add.

        Returns
        -------
        pendulum.DateTime
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
        dt : pendulum.DateTime
            The original datetime.
        hours : int
            Number of hours to add.

        Returns
        -------
        pendulum.DateTime
            The resulting datetime after adding the specified hours.
        """
        # Add the specified number of hours to the datetime
        return dt.add(hours=hours)

    @classmethod
    def addMinutes(
        cls, dt: pendulum.DateTime, minutes: int,
    ) -> pendulum.DateTime:
        """
        Add minutes to a given datetime.

        Parameters
        ----------
        dt : pendulum.DateTime
            The original datetime.
        minutes : int
            Number of minutes to add.

        Returns
        -------
        pendulum.DateTime
            The resulting datetime after adding the specified minutes.
        """
        # Add the specified number of minutes to the datetime
        return dt.add(minutes=minutes)

    @classmethod
    def diffInDays(
        cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime,
    ) -> int:
        """
        Calculate the difference in days between two dates.

        Parameters
        ----------
        dt1 : pendulum.DateTime
            The first date.
        dt2 : pendulum.DateTime
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
        cls, dt1: pendulum.DateTime, dt2: pendulum.DateTime,
    ) -> int:
        """
        Compute the difference in hours between two dates.

        Parameters
        ----------
        dt1 : pendulum.DateTime
            The first datetime.
        dt2 : pendulum.DateTime
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
        cls, dt: pendulum.DateTime | None = None,
    ) -> bool:
        """
        Determine if the given date falls on a weekend.

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to check. If None, uses the current datetime.

        Returns
        -------
        bool
            True if the date is Saturday or Sunday, False otherwise.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(cls._timezone)
        return dt.day_of_week in (pendulum.SATURDAY, pendulum.SUNDAY)

    @classmethod
    def isToday(cls, dt: pendulum.DateTime) -> bool:
        """
        Check if the given date is today.

        Parameters
        ----------
        dt : pendulum.DateTime
            The datetime to check.

        Returns
        -------
        bool
            True if the date is today, False otherwise.
        """
        # Read the current date in the configured timezone.
        today = pendulum.today(cls._timezone)
        return (
            dt.year == today.year
            and dt.month == today.month
            and dt.day == today.day
        )

    @classmethod
    def isFuture(cls, dt: pendulum.DateTime) -> bool:
        """
        Determine if the given date is in the future.

        Parameters
        ----------
        dt : pendulum.DateTime
            The datetime to check.

        Returns
        -------
        bool
            True if the date is in the future, False otherwise.
        """
        return dt > pendulum.now(cls._timezone)

    @classmethod
    def isPast(cls, dt: pendulum.DateTime) -> bool:
        """
        Determine if the given date is in the past.

        Parameters
        ----------
        dt : pendulum.DateTime
            The datetime to check.

        Returns
        -------
        bool
            True if the date is in the past, False otherwise.
        """
        return dt < pendulum.now(cls._timezone)

    @classmethod
    def isLeapYear(cls, dt: pendulum.DateTime | None = None) -> bool:
        """
        Determine if the year of the given date is a leap year.

        Parameters
        ----------
        dt : pendulum.DateTime | None, optional
            The datetime to check. If None, uses the current datetime.

        Returns
        -------
        bool
            True if the year is a leap year, False otherwise.
        """
        # Use current datetime if none is provided
        if dt is None:
            dt = pendulum.now(cls._timezone)
        return dt.is_leap_year()

    @classmethod
    def isBirthday(
        cls,
        dt: pendulum.DateTime,
        other: pendulum.DateTime | None = None,
    ) -> bool:
        """
        Determine if the given date shares month and day with another date.

        Parameters
        ----------
        dt : pendulum.DateTime
            The reference date (e.g. a date of birth).
        other : pendulum.DateTime | None, optional
            The date to compare against. If None, uses the current datetime
            in the configured timezone.

        Returns
        -------
        bool
            True if both dates share the same month and day, False otherwise.
        """
        reference = other if other is not None else pendulum.now(cls._timezone)
        return dt.is_birthday(reference)

    @classmethod
    def closest(
        cls, dt: pendulum.DateTime, *others: pendulum.DateTime,
    ) -> pendulum.DateTime:
        """
        Return the datetime closest to the given one among the candidates.

        Parameters
        ----------
        dt : pendulum.DateTime
            The reference datetime.
        *others : pendulum.DateTime
            Candidate datetimes to compare against the reference.

        Returns
        -------
        pendulum.DateTime
            The candidate closest to ``dt``.
        """
        return dt.closest(*others)

    @classmethod
    def farthest(
        cls, dt: pendulum.DateTime, *others: pendulum.DateTime,
    ) -> pendulum.DateTime:
        """
        Return the datetime farthest from the given one among the candidates.

        Parameters
        ----------
        dt : pendulum.DateTime
            The reference datetime.
        *others : pendulum.DateTime
            Candidate datetimes to compare against the reference.

        Returns
        -------
        pendulum.DateTime
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
        dt : pendulum.DateTime
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
        pendulum.DateTime
            The resulting datetime after adding the specified units.
        """
        return dt.add(
            years=years, months=months, weeks=weeks, days=days,
            hours=hours, minutes=minutes, seconds=seconds,
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
        dt : pendulum.DateTime
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
        pendulum.DateTime
            The resulting datetime after subtracting the specified units.
        """
        return dt.subtract(
            years=years, months=months, weeks=weeks, days=days,
            hours=hours, minutes=minutes, seconds=seconds,
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
        dt1 : pendulum.DateTime
            The reference datetime.
        dt2 : pendulum.DateTime | None, optional
            The datetime to compare against. If None, uses the current
            datetime in the configured timezone.
        absolute : bool, optional
            Whether to return an always-positive interval, by default True.

        Returns
        -------
        pendulum.Interval
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
        dt : pendulum.DateTime
            The reference datetime.
        other : pendulum.DateTime | None, optional
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
            other, absolute=absolute,
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
        dt : pendulum.DateTime
            The original datetime.
        day_of_week : int | None, optional
            Target day of the week (e.g. `pendulum.WEDNESDAY`). If None,
            uses the day of the week of ``dt``.
        keep_time : bool, optional
            Whether to keep the time component instead of resetting it
            to midnight, by default False.

        Returns
        -------
        pendulum.DateTime
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
        dt : pendulum.DateTime
            The original datetime.
        day_of_week : int | None, optional
            Target day of the week (e.g. `pendulum.WEDNESDAY`). If None,
            uses the day of the week of ``dt``.
        keep_time : bool, optional
            Whether to keep the time component instead of resetting it
            to midnight, by default False.

        Returns
        -------
        pendulum.DateTime
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
        dt1 : pendulum.DateTime
            The reference datetime.
        dt2 : pendulum.DateTime | None, optional
            The datetime to average with. If None, uses the current
            datetime in the configured timezone.

        Returns
        -------
        pendulum.DateTime
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
        dt : pendulum.DateTime
            The original datetime.
        unit : str
            Unit of time: 'month', 'quarter' or 'year'.
        day_of_week : int | None, optional
            Constrain the result to a specific day of the week
            (e.g. `pendulum.MONDAY`). If None, returns the first day
            of the unit regardless of weekday.

        Returns
        -------
        pendulum.DateTime
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
        dt : pendulum.DateTime
            The original datetime.
        unit : str
            Unit of time: 'month', 'quarter' or 'year'.
        day_of_week : int | None, optional
            Constrain the result to a specific day of the week
            (e.g. `pendulum.FRIDAY`). If None, returns the last day
            of the unit regardless of weekday.

        Returns
        -------
        pendulum.DateTime
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
        dt : pendulum.DateTime
            The original datetime.
        unit : str
            Unit of time: 'month', 'quarter' or 'year'.
        nth : int
            The occurrence index to look for (1-based).
        day_of_week : int
            Target day of the week (e.g. `pendulum.MONDAY`).

        Returns
        -------
        pendulum.DateTime
            The resulting datetime.

        Raises
        ------
        PendulumException
            If the given occurrence does not exist within the unit.
        """
        return dt.nth_of(unit, nth, day_of_week)
