# ruff: noqa: DTZ001, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from datetime import UTC
from datetime import datetime as stdlib_datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo
import pendulum
from orionis.support.facades.datetime import DateTime
from orionis.test import TestCase

# Timezone and locale used as a safe, stable default across all tests
_DEFAULT_TZ = "UTC"
_DEFAULT_LOCALE = "en"


class _DateTimeTestCase(TestCase):
    """Restore process-wide date configuration after every scenario."""

    def setUp(self) -> None:
        """Isolate facade defaults and Pendulum's locale for this test."""
        super().setUp()
        self.enterContext(patch.object(DateTime, "_timezone", _DEFAULT_TZ))
        self.enterContext(patch.object(DateTime, "_locale", _DEFAULT_LOCALE))
        self.addCleanup(pendulum.set_locale, pendulum.get_locale())
        pendulum.set_locale(_DEFAULT_LOCALE)


class TestDateTimeConfig(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset DateTime class state before each test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()

    # ------------------------------------------------ loadConfig

    def testLoadConfigSetsBothTimezoneAndLocale(self) -> None:
        """Apply timezone and locale when both are provided to loadConfig.

        Validates that loadConfig delegates correctly to setTimezone
        and setLocale when both arguments are supplied.

        Returns
        -------
        None
            No return value.
        """
        DateTime._loadConfig(
            timezone_name="America/New_York",
            locale="es",
        )
        self.assertEqual(DateTime._timezone, "America/New_York")
        self.assertEqual(DateTime._locale, "es")

    def testLoadConfigWithNoneDoesNotOverwriteDefaults(self) -> None:
        """Leave timezone and locale unchanged when None is passed to loadConfig.

        Validates that providing None for both parameters keeps the
        existing class-level defaults intact.

        Returns
        -------
        None
            No return value.
        """
        DateTime._loadConfig(timezone_name=None, locale=None)
        self.assertEqual(DateTime._timezone, _DEFAULT_TZ)
        self.assertEqual(DateTime._locale, _DEFAULT_LOCALE)

    def testLoadConfigWithTimezoneOnlyDoesNotChangeLocale(self) -> None:
        """Change only the timezone when locale is None in loadConfig.

        Validates that supplying only a timezone leaves the locale
        at its previous value.

        Returns
        -------
        None
            No return value.
        """
        DateTime._loadConfig(timezone_name="Europe/London", locale=None)
        self.assertEqual(DateTime._timezone, "Europe/London")
        self.assertEqual(DateTime._locale, _DEFAULT_LOCALE)

    def testLoadConfigWithLocaleOnlyDoesNotChangeTimezone(self) -> None:
        """Change only the locale when timezone is None in loadConfig.

        Validates that supplying only a locale leaves the timezone
        at its previous value.

        Returns
        -------
        None
            No return value.
        """
        DateTime._loadConfig(timezone_name=None, locale="fr")
        self.assertEqual(DateTime._timezone, _DEFAULT_TZ)
        self.assertEqual(DateTime._locale, "fr")

    # ------------------------------------------------ setTimezone / getTimezone

    def testSetTimezoneStoresValidTimezone(self) -> None:
        """Store a valid timezone string via setTimezone.

        Validates that after calling setTimezone the internal class
        attribute reflects the new timezone name.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setTimezone("Asia/Tokyo")
        self.assertEqual(DateTime._timezone, "Asia/Tokyo")

    def testSetTimezoneRaisesOnInvalidName(self) -> None:
        """Raise ValueError when an invalid timezone name is provided.

        Validates that _setTimezone rejects unrecognised timezone strings.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(ValueError):
            DateTime._setTimezone("Invalid/Timezone_XXXX")

    def testGetTimezoneReturnsCurrentValue(self) -> None:
        """Return the currently configured timezone string from getTimezone.

        Validates that getTimezone reflects the value set by setTimezone.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setTimezone("Europe/Paris")
        self.assertEqual(DateTime.getTimezone(), "Europe/Paris")

    def testGetTimezoneDefaultIsUTC(self) -> None:
        """Return UTC as the default timezone before any configuration.

        Validates that the timezone defaults to 'UTC' on a freshly
        reset class state.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(DateTime.getTimezone(), "UTC")

    # ------------------------------------------------ setLocale

    def testSetLocaleStoresLocaleValue(self) -> None:
        """Store the locale string via setLocale.

        Validates that calling setLocale updates the internal _locale
        attribute to the provided value.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setLocale("de")
        self.assertEqual(DateTime._locale, "de")

    def testSetLocaleUpdatesLatin(self) -> None:
        """Accept a Latin-script locale code without error.

        Validates that setLocale can handle commonly used Latin locale
        codes such as 'es' (Spanish).

        Returns
        -------
        None
            No return value.
        """
        DateTime._setLocale("es")
        self.assertEqual(DateTime._locale, "es")

    # ------------------------------------------------ getZoneinfo

    def testGetZoneinfoReturnsZoneInfoInstance(self) -> None:
        """Return a ZoneInfo object from getZoneinfo.

        Validates that getZoneinfo produces a ZoneInfo instance matching
        the currently configured timezone.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.getZoneInfo()
        self.assertIsInstance(result, ZoneInfo)

    def testGetZoneinfoKeyMatchesConfiguredTimezone(self) -> None:
        """Return ZoneInfo whose key matches the configured timezone.

        Validates that the ZoneInfo key returned by getZoneinfo is
        identical to the timezone stored in DateTime._timezone.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setTimezone("America/Chicago")
        zi = DateTime.getZoneInfo()
        self.assertEqual(zi.key, "America/Chicago")


class TestDateTimeInstants(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state before each test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()

    # ------------------------------------------------ now

    def testNowReturnsPendulumDateTime(self) -> None:
        """Return a pendulum.DateTime from now.

        Validates that now() produces an instance of pendulum.DateTime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.now()
        self.assertIsInstance(result, pendulum.DateTime)

    def testNowUsesDefaultTimezoneWhenNoArgGiven(self) -> None:
        """Use the configured default timezone when tz is None in now.

        Validates that the timezone of the returned datetime matches
        the class-level default when no tz argument is provided.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setTimezone("Europe/Berlin")
        result = DateTime.now()
        self.assertEqual(result.timezone_name, "Europe/Berlin")

    def testNowUsesExplicitTimezoneArgument(self) -> None:
        """Apply the explicit tz argument in now instead of the default.

        Validates that when a timezone is passed to now(), the returned
        datetime reflects that timezone.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.now(tz="Asia/Singapore")
        self.assertEqual(result.timezone_name, "Asia/Singapore")

    # ------------------------------------------------ today

    def testTodayReturnsPendulumDateTime(self) -> None:
        """Return a pendulum.DateTime from today.

        Validates that today() produces a pendulum datetime object.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.today()
        self.assertIsInstance(result, pendulum.DateTime)

    def testTodayHasMidnightTime(self) -> None:
        """Return a datetime at midnight from today.

        Validates that today() always returns a datetime whose
        hour, minute, and second components are all zero.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.today()
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.second, 0)

    def testTodayWithExplicitTimezone(self) -> None:
        """Apply the explicit tz argument in today instead of the default.

        Validates that the returned datetime uses the supplied timezone.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.today(tz="Australia/Sydney")
        self.assertEqual(result.timezone_name, "Australia/Sydney")

    # ------------------------------------------------ tomorrow

    def testTomorrowIsOneDayAfterToday(self) -> None:
        """Return a date exactly one day after today from tomorrow.

        Validates that tomorrow() produces a datetime whose date
        component is one day ahead of today().

        Returns
        -------
        None
            No return value.
        """
        today = DateTime.today()
        tomorrow = DateTime.tomorrow()
        diff = tomorrow.diff(today).in_days()
        self.assertEqual(diff, 1)

    def testTomorrowWithExplicitTimezone(self) -> None:
        """Apply the explicit tz argument in tomorrow instead of the default.

        Validates that the returned datetime uses the supplied timezone.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.tomorrow(tz="America/Sao_Paulo")
        self.assertEqual(result.timezone_name, "America/Sao_Paulo")

    # ------------------------------------------------ yesterday

    def testYesterdayIsOneDayBeforeToday(self) -> None:
        """Return a date exactly one day before today from yesterday.

        Validates that yesterday() produces a datetime one day behind
        today().

        Returns
        -------
        None
            No return value.
        """
        today = DateTime.today()
        yesterday = DateTime.yesterday()
        diff = today.diff(yesterday).in_days()
        self.assertEqual(diff, 1)

    def testYesterdayWithExplicitTimezone(self) -> None:
        """Apply the explicit tz argument in yesterday instead of the default.

        Validates that the returned datetime uses the supplied timezone.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.yesterday(tz="Pacific/Auckland")
        self.assertEqual(result.timezone_name, "Pacific/Auckland")


class TestDateTimeFromConversions(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state before each test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()

    # ------------------------------------------------ parse

    def testParseReturnsPendulumDateTime(self) -> None:
        """Return a pendulum.DateTime from a valid date string.

        Validates that parse() produces a pendulum.DateTime instance
        for a well-formed ISO 8601 date string.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.parse("2024-06-15T12:00:00")
        self.assertIsInstance(result, pendulum.DateTime)

    def testParseConvertsToConfiguredTimezone(self) -> None:
        """Convert the parsed datetime to the configured timezone.

        Validates that when the parsed timezone differs from the class
        default, parse() converts the result to the class timezone.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setTimezone("America/New_York")
        result = DateTime.parse("2024-06-15T12:00:00+00:00")
        self.assertEqual(result.timezone_name, "America/New_York")

    def testParseWithExplicitTzArgument(self) -> None:
        """Apply the explicit tz argument when parsing a date string.

        Validates that passing tz to parse() overrides the class-level
        default timezone for the returned datetime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.parse("2024-01-01T00:00:00+00:00", tz="Asia/Tokyo")
        self.assertEqual(result.timezone_name, "Asia/Tokyo")

    # ------------------------------------------------ fromTimestamp

    def testFromTimestampReturnsPendulumDateTime(self) -> None:
        """Return a pendulum.DateTime from a Unix timestamp.

        Validates that fromTimestamp() converts a float timestamp to a
        valid pendulum.DateTime instance.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.fromTimestamp(0.0)
        self.assertIsInstance(result, pendulum.DateTime)

    def testFromTimestampEpochIsJanuaryFirst1970UTC(self) -> None:
        """Map Unix epoch zero to January 1st 1970 at midnight UTC.

        Validates that timestamp 0 corresponds to the Unix epoch
        in UTC with all time components set to zero.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.fromTimestamp(0.0, tz="UTC")
        self.assertEqual(result.year, 1970)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 0)

    def testFromTimestampUsesExplicitTz(self) -> None:
        """Apply the explicit tz argument in fromTimestamp.

        Validates that the returned datetime is expressed in the
        timezone supplied to fromTimestamp().

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.fromTimestamp(0.0, tz="Asia/Tokyo")
        self.assertEqual(result.timezone_name, "Asia/Tokyo")

    # ------------------------------------------------ fromDatetime

    def testFromDatetimeWithNaiveStdlibDatetime(self) -> None:
        """Convert a naive stdlib datetime to pendulum in the configured tz.

        Validates that fromDatetime() treats a naive (tz-unaware)
        datetime as belonging to the class-level timezone.

        Returns
        -------
        None
            No return value.
        """
        naive_dt = stdlib_datetime(2024, 3, 15, 10, 30, 0)
        result = DateTime.fromDatetime(naive_dt)
        self.assertIsInstance(result, pendulum.DateTime)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 3)
        self.assertEqual(result.day, 15)

    def testFromDatetimeWithAwareStdlibDatetime(self) -> None:
        """Convert an aware stdlib datetime to the configured timezone.

        Validates that fromDatetime() converts a timezone-aware stdlib
        datetime to pendulum.DateTime in the class-level timezone.

        Returns
        -------
        None
            No return value.
        """
        aware_dt = stdlib_datetime(
            2024,
            3,
            15,
            10,
            30,
            0,
            tzinfo=UTC,
        )
        DateTime._setTimezone("America/Chicago")
        result = DateTime.fromDatetime(aware_dt)
        self.assertIsInstance(result, pendulum.DateTime)
        self.assertEqual(result.timezone_name, "America/Chicago")

    def testFromDatetimeWithPendulumDatetime(self) -> None:
        """Convert a pendulum.DateTime to the configured timezone.

        Validates that fromDatetime() correctly converts a pendulum
        instance to the target timezone.

        Returns
        -------
        None
            No return value.
        """
        source = pendulum.datetime(2024, 6, 1, 12, 0, 0, tz="UTC")
        DateTime._setTimezone("Europe/London")
        result = DateTime.fromDatetime(source)
        self.assertEqual(result.timezone_name, "Europe/London")

    def testFromDatetimeRaisesTypeErrorForUnsupportedType(self) -> None:
        """Raise TypeError when an unsupported type is passed to fromDatetime.

        Validates that fromDatetime() rejects plain strings, integers,
        or other non-datetime objects with a TypeError.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            DateTime.fromDatetime("2024-01-01")  # type: ignore[arg-type]

    def testFromDatetimeWithExplicitTzArgument(self) -> None:
        """Apply the explicit tz argument in fromDatetime.

        Validates that when tz is supplied, the result is expressed in
        that timezone regardless of the class-level default.

        Returns
        -------
        None
            No return value.
        """
        naive_dt = stdlib_datetime(2024, 1, 1, 0, 0, 0)
        result = DateTime.fromDatetime(naive_dt, tz="Asia/Seoul")
        self.assertEqual(result.timezone_name, "Asia/Seoul")

    # Calendar component construction

    def testDatetimeCreatesCorrectComponents(self) -> None:
        """Create a pendulum.DateTime with the specified date components.

        Validates that the datetime() factory method produces an object
        with year, month, day, hour, minute, and second matching the
        supplied arguments.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.datetime(2024, 6, 15, 10, 30, 45)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.minute, 30)
        self.assertEqual(result.second, 45)

    def testDatetimeDefaultsMonthAndDayToOne(self) -> None:
        """Default month and day to 1 when only year is provided to datetime.

        Validates that omitting optional components results in the first
        day of January.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.datetime(2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)

    def testDatetimeUsesConfiguredTimezone(self) -> None:
        """Use the configured timezone when tz is None in datetime factory.

        Validates that the produced datetime is expressed in the
        class-level default timezone.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setTimezone("Europe/Madrid")
        result = DateTime.datetime(2024, 1, 1)
        self.assertEqual(result.timezone_name, "Europe/Madrid")

    def testDatetimeWithExplicitTzArgument(self) -> None:
        """Apply the explicit tz argument in the datetime factory.

        Validates that the produced datetime is expressed in the
        supplied timezone rather than the class-level default.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.datetime(2024, 1, 1, tz="Pacific/Honolulu")
        self.assertEqual(result.timezone_name, "Pacific/Honolulu")


class TestDateTimeBoundaries(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state and build a stable reference datetime.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        # Wednesday, June 12 2024 at 14:30:45 UTC - used across boundary tests
        self.ref = DateTime.datetime(2024, 6, 12, 14, 30, 45, tz="UTC")

    # ------------------------------------------------ startOfDay / endOfDay

    def testStartOfDayReturnsFirstSecondOfDay(self) -> None:
        """Return midnight at the start of the given day from startOfDay.

        Validates that startOfDay() sets hour, minute, and second to
        zero without changing the date.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOfDay(self.ref)
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.second, 0)
        self.assertEqual(result.date(), self.ref.date())

    def testStartOfDayWithoutDtUsesNow(self) -> None:
        """Use the current datetime when no argument is given to startOfDay.

        Validates that startOfDay() without arguments returns today's
        midnight.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOfDay()
        today = DateTime.today()
        self.assertEqual(result.date(), today.date())
        self.assertEqual(result.hour, 0)

    def testEndOfDayReturnsLastSecondOfDay(self) -> None:
        """Return 23:59:59 at the end of the given day from endOfDay.

        Validates that endOfDay() returns the last representable
        second of the supplied date.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.endOfDay(self.ref)
        self.assertEqual(result.hour, 23)
        self.assertEqual(result.minute, 59)
        self.assertEqual(result.second, 59)
        self.assertEqual(result.date(), self.ref.date())

    def testEndOfDayWithoutDtUsesNow(self) -> None:
        """Use the current datetime when no argument is given to endOfDay.

        Validates that endOfDay() without arguments returns the last
        second of today.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.endOfDay()
        today = DateTime.today()
        self.assertEqual(result.date(), today.date())
        self.assertEqual(result.hour, 23)

    # ------------------------------------------------ startOfWeek / endOfWeek

    def testStartOfWeekReturnsMondayMidnight(self) -> None:
        """Return the Monday at midnight of the given week from startOfWeek.

        Validates that startOfWeek() produces a datetime on Monday
        at 00:00:00.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOfWeek(self.ref)
        # pendulum week starts on Monday (day_of_week == MONDAY == 1)
        self.assertEqual(result.day_of_week, pendulum.MONDAY)
        self.assertEqual(result.hour, 0)

    def testEndOfWeekReturnsSundayLastSecond(self) -> None:
        """Return Sunday at 23:59:59 of the given week from endOfWeek.

        Validates that endOfWeek() produces a datetime on Sunday
        at 23:59:59.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.endOfWeek(self.ref)
        self.assertEqual(result.day_of_week, pendulum.SUNDAY)
        self.assertEqual(result.hour, 23)

    def testStartOfWeekWithoutDtUsesNow(self) -> None:
        """Use the current datetime when no argument is given to startOfWeek.

        Validates that startOfWeek() without arguments returns a Monday.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOfWeek()
        self.assertEqual(result.day_of_week, pendulum.MONDAY)

    # ------------------------------------------------ startOfMonth / endOfMonth

    def testStartOfMonthReturnsFirstDayMidnight(self) -> None:
        """Return the first day of the month at midnight from startOfMonth.

        Validates that startOfMonth() sets the day to 1 and time to
        00:00:00 for the month of the supplied datetime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOfMonth(self.ref)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.month, self.ref.month)
        self.assertEqual(result.hour, 0)

    def testEndOfMonthReturnsLastDayLastSecond(self) -> None:
        """Return the last day of the month at 23:59:59 from endOfMonth.

        Validates that endOfMonth() returns the final second of the
        last calendar day of the supplied month.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.endOfMonth(self.ref)
        # June has 30 days
        self.assertEqual(result.day, 30)
        self.assertEqual(result.month, self.ref.month)
        self.assertEqual(result.hour, 23)

    def testStartOfMonthWithoutDtUsesNow(self) -> None:
        """Use the current datetime when no argument is given to startOfMonth.

        Validates that startOfMonth() without arguments sets the day to
        1 for the current month.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOfMonth()
        self.assertEqual(result.day, 1)

    # ------------------------------------------------ startOfYear / endOfYear

    def testStartOfYearReturnsJanuaryFirstMidnight(self) -> None:
        """Return January 1st at midnight from startOfYear.

        Validates that startOfYear() produces a datetime on January 1st
        at 00:00:00 for the year of the supplied datetime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOfYear(self.ref)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.year, self.ref.year)

    def testEndOfYearReturnsDecember31LastSecond(self) -> None:
        """Return December 31st at 23:59:59 from endOfYear.

        Validates that endOfYear() produces a datetime on December 31st
        at 23:59:59 for the year of the supplied datetime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.endOfYear(self.ref)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 31)
        self.assertEqual(result.hour, 23)
        self.assertEqual(result.year, self.ref.year)

    def testStartOfYearWithoutDtUsesNow(self) -> None:
        """Use the current datetime when no argument is given to startOfYear.

        Validates that startOfYear() without arguments returns January
        1st of the current year.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOfYear()
        now = DateTime.now()
        self.assertEqual(result.year, now.year)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)


class TestDateTimeArithmetic(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state and build a stable reference datetime.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        self.ref = DateTime.datetime(2024, 1, 1, 12, 0, 0, tz="UTC")

    # ------------------------------------------------ addDays

    def testAddDaysShiftsDateBySpecifiedAmount(self) -> None:
        """Shift the date forward by the specified number of days.

        Validates that addDays() returns a datetime exactly n calendar
        days after the supplied one.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addDays(self.ref, 5)
        self.assertEqual(result.day, 6)
        self.assertEqual(result.month, 1)

    def testAddDaysWithZeroReturnsUnchanged(self) -> None:
        """Return the same date when zero days are added.

        Validates that addDays(dt, 0) is an identity operation.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addDays(self.ref, 0)
        self.assertEqual(result.date(), self.ref.date())

    def testAddDaysWithNegativeValueGoesBackward(self) -> None:
        """Go backward in time when a negative day count is added.

        Validates that addDays() with a negative integer moves the
        datetime into the past.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addDays(self.ref, -3)
        self.assertEqual(result.day, 29)  # Dec 29 2023
        self.assertEqual(result.month, 12)

    # ------------------------------------------------ addHours

    def testAddHoursShiftsTimeBySpecifiedAmount(self) -> None:
        """Shift the time forward by the specified number of hours.

        Validates that addHours() returns a datetime exactly n hours
        after the supplied one.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addHours(self.ref, 3)
        self.assertEqual(result.hour, 15)

    def testAddHoursRollsOverToNextDay(self) -> None:
        """Roll over to the next day when hours exceed 24.

        Validates that adding hours beyond midnight correctly advances
        the date by the appropriate number of days.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addHours(self.ref, 14)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 2)

    def testAddHoursWithZeroReturnsUnchanged(self) -> None:
        """Return the same datetime when zero hours are added.

        Validates that addHours(dt, 0) is an identity operation
        with respect to time.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addHours(self.ref, 0)
        self.assertEqual(result.hour, self.ref.hour)

    # ------------------------------------------------ addMinutes

    def testAddMinutesShiftsTimeBySpecifiedAmount(self) -> None:
        """Shift the time forward by the specified number of minutes.

        Validates that addMinutes() returns a datetime exactly n
        minutes after the supplied one.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addMinutes(self.ref, 30)
        self.assertEqual(result.minute, 30)

    def testAddMinutesRollsOverToNextHour(self) -> None:
        """Roll over to the next hour when minutes exceed 60.

        Validates that adding minutes beyond 60 correctly advances
        the hour.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addMinutes(self.ref, 90)
        self.assertEqual(result.hour, 13)
        self.assertEqual(result.minute, 30)

    def testAddMinutesWithZeroReturnsUnchanged(self) -> None:
        """Return the same datetime when zero minutes are added.

        Validates that addMinutes(dt, 0) is an identity operation
        with respect to time.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.addMinutes(self.ref, 0)
        self.assertEqual(result.minute, self.ref.minute)

    # ------------------------------------------------ diffInDays

    def testDiffInDaysReturnsDifferenceBetweenDates(self) -> None:
        """Return the correct number of days between two dates.

        Validates that diffInDays() computes the absolute calendar-day
        difference between two pendulum.DateTime instances.

        Returns
        -------
        None
            No return value.
        """
        dt2 = DateTime.addDays(self.ref, 10)
        diff = DateTime.diffInDays(self.ref, dt2)
        self.assertEqual(diff, 10)

    def testDiffInDaysIsZeroForSameDate(self) -> None:
        """Return zero when both dates are identical.

        Validates that diffInDays() returns 0 when both arguments
        reference the same point in time.

        Returns
        -------
        None
            No return value.
        """
        diff = DateTime.diffInDays(self.ref, self.ref)
        self.assertEqual(diff, 0)

    def testDiffInDaysIsPositiveRegardlessOfOrder(self) -> None:
        """Return a non-negative value regardless of argument order.

        Validates that diffInDays() returns a positive integer even when
        dt2 is earlier than dt1 (pendulum diffs are always absolute).

        Returns
        -------
        None
            No return value.
        """
        earlier = DateTime.addDays(self.ref, -5)
        diff = DateTime.diffInDays(self.ref, earlier)
        self.assertEqual(diff, 5)

    # ------------------------------------------------ diffInHours

    def testDiffInHoursReturnsDifferenceBetweenDatetimes(self) -> None:
        """Return the correct number of hours between two datetimes.

        Validates that diffInHours() computes the integer-hour
        difference between two pendulum.DateTime instances.

        Returns
        -------
        None
            No return value.
        """
        dt2 = DateTime.addHours(self.ref, 6)
        diff = DateTime.diffInHours(self.ref, dt2)
        self.assertEqual(diff, 6)

    def testDiffInHoursIsZeroForSameDatetime(self) -> None:
        """Return zero when both datetimes are identical.

        Validates that diffInHours() returns 0 when both arguments
        reference the same point in time.

        Returns
        -------
        None
            No return value.
        """
        diff = DateTime.diffInHours(self.ref, self.ref)
        self.assertEqual(diff, 0)


class TestDateTimePredicates(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state before each test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()

    # ------------------------------------------------ isWeekend

    def testIsWeekendReturnsTrueForSaturday(self) -> None:
        """Return True when the given date falls on Saturday.

        Validates that isWeekend() identifies Saturday correctly.

        Returns
        -------
        None
            No return value.
        """
        # 2024-06-08 is a Saturday
        saturday = DateTime.datetime(2024, 6, 8, tz="UTC")
        self.assertTrue(DateTime.isWeekend(saturday))

    def testIsWeekendReturnsTrueForSunday(self) -> None:
        """Return True when the given date falls on Sunday.

        Validates that isWeekend() identifies Sunday correctly.

        Returns
        -------
        None
            No return value.
        """
        # 2024-06-09 is a Sunday
        sunday = DateTime.datetime(2024, 6, 9, tz="UTC")
        self.assertTrue(DateTime.isWeekend(sunday))

    def testIsWeekendReturnsFalseForWeekday(self) -> None:
        """Return False when the given date falls on a weekday.

        Validates that isWeekend() returns False for Monday through
        Friday.

        Returns
        -------
        None
            No return value.
        """
        # 2024-06-10 is a Monday
        monday = DateTime.datetime(2024, 6, 10, tz="UTC")
        self.assertFalse(DateTime.isWeekend(monday))

    def testIsWeekendWithoutArgumentUsesNow(self) -> None:
        """Use the current datetime when no argument is given to isWeekend.

        Validates that isWeekend() without arguments produces a boolean
        result consistent with the current day of the week.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.isWeekend()
        now = DateTime.now()
        expected = now.day_of_week in [pendulum.SATURDAY, pendulum.SUNDAY]
        self.assertEqual(result, expected)

    # ------------------------------------------------ isToday

    def testIsTodayReturnsTrueForCurrentDatetime(self) -> None:
        """Return True when the given datetime is today.

        Validates that isToday() correctly identifies the current
        date as today.

        Returns
        -------
        None
            No return value.
        """
        now = DateTime.now()
        self.assertTrue(DateTime.isToday(now))

    def testIsTodayReturnsFalseForYesterdayDatetime(self) -> None:
        """Return False when the given datetime is yesterday.

        Validates that isToday() returns False for a datetime that
        falls one day in the past.

        Returns
        -------
        None
            No return value.
        """
        yesterday = DateTime.yesterday()
        self.assertFalse(DateTime.isToday(yesterday))

    def testIsTodayReturnsFalseForTomorrowDatetime(self) -> None:
        """Return False when the given datetime is tomorrow.

        Validates that isToday() returns False for a datetime that
        falls one day in the future.

        Returns
        -------
        None
            No return value.
        """
        tomorrow = DateTime.tomorrow()
        self.assertFalse(DateTime.isToday(tomorrow))

    # ------------------------------------------------ isFuture

    def testIsFutureReturnsTrueForFutureDate(self) -> None:
        """Return True when the given datetime is in the future.

        Validates that isFuture() correctly identifies a datetime
        set far ahead of the current moment.

        Returns
        -------
        None
            No return value.
        """
        future = DateTime.addDays(DateTime.now(), 100)
        self.assertTrue(DateTime.isFuture(future))

    def testIsFutureReturnsFalseForPastDate(self) -> None:
        """Return False when the given datetime is in the past.

        Validates that isFuture() correctly rejects a datetime
        set far behind the current moment.

        Returns
        -------
        None
            No return value.
        """
        past = DateTime.addDays(DateTime.now(), -100)
        self.assertFalse(DateTime.isFuture(past))

    # ------------------------------------------------ isPast

    def testIsPastReturnsTrueForPastDate(self) -> None:
        """Return True when the given datetime is in the past.

        Validates that isPast() correctly identifies a datetime
        set far behind the current moment.

        Returns
        -------
        None
            No return value.
        """
        past = DateTime.addDays(DateTime.now(), -100)
        self.assertTrue(DateTime.isPast(past))

    def testIsPastReturnsFalseForFutureDate(self) -> None:
        """Return False when the given datetime is in the future.

        Validates that isPast() correctly rejects a datetime
        set far ahead of the current moment.

        Returns
        -------
        None
            No return value.
        """
        future = DateTime.addDays(DateTime.now(), 100)
        self.assertFalse(DateTime.isPast(future))

    # ------------------------------------------------ convertToLocal

    def testConvertToLocalFromString(self) -> None:
        """Convert an ISO string to the configured local timezone.

        Validates that convertToLocal() accepts a plain date string
        and returns a pendulum.DateTime in the class timezone.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.convertToLocal("2024-06-15T12:00:00+00:00")
        self.assertIsInstance(result, pendulum.DateTime)
        self.assertEqual(result.timezone_name, _DEFAULT_TZ)

    def testConvertToLocalFromStdlibDatetime(self) -> None:
        """Convert a stdlib datetime to the configured local timezone.

        Validates that convertToLocal() accepts a stdlib datetime
        object and returns a pendulum.DateTime in the class timezone.

        Returns
        -------
        None
            No return value.
        """
        naive_dt = stdlib_datetime(2024, 6, 15, 12, 0, 0)
        result = DateTime.convertToLocal(naive_dt)
        self.assertIsInstance(result, pendulum.DateTime)
        self.assertEqual(result.timezone_name, _DEFAULT_TZ)

    def testConvertToLocalFromPendulumDatetime(self) -> None:
        """Convert a pendulum datetime to the configured local timezone.

        Validates that convertToLocal() accepts a pendulum.DateTime
        and returns one in the class timezone.

        Returns
        -------
        None
            No return value.
        """
        source = pendulum.datetime(2024, 6, 15, 12, 0, 0, tz="Asia/Tokyo")
        result = DateTime.convertToLocal(source)
        self.assertIsInstance(result, pendulum.DateTime)
        self.assertEqual(result.timezone_name, _DEFAULT_TZ)

    # ------------------------------------------------ formatLocal

    def testFormatLocalReturnsString(self) -> None:
        """Return a formatted date string from formatLocal.

        Validates that formatLocal() produces a non-empty string
        for a given pendulum.DateTime.

        Returns
        -------
        None
            No return value.
        """
        dt = DateTime.datetime(2024, 6, 15, 10, 30, 45, tz="UTC")
        result = DateTime.formatLocal(dt)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def testFormatLocalDefaultFormatMatchesISO(self) -> None:
        """Use the default format YYYY-MM-DD HH:mm:ss in formatLocal.

        Validates that the default format string produces output in
        the expected pattern for a known datetime.

        Returns
        -------
        None
            No return value.
        """
        dt = DateTime.datetime(2024, 6, 15, 10, 30, 45, tz="UTC")
        result = DateTime.formatLocal(dt)
        self.assertEqual(result, "2024-06-15 10:30:45")

    def testFormatLocalWithCustomFormat(self) -> None:
        """Apply a custom format string in formatLocal.

        Validates that formatLocal() respects an explicit format_string
        argument and returns output matching that pattern.

        Returns
        -------
        None
            No return value.
        """
        dt = DateTime.datetime(2024, 6, 15, tz="UTC")
        result = DateTime.formatLocal(dt, format_string="YYYY/MM/DD")
        self.assertEqual(result, "2024/06/15")

    def testFormatLocalWithoutDtUsesNow(self) -> None:
        """Use the current datetime when no dt is given to formatLocal.

        Validates that formatLocal() without a dt argument returns a
        non-empty string representing the current moment.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.formatLocal()
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


class TestDateTimeExtendedConfig(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset DateTime class state before each test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()

    # ------------------------------------------------ getLocale

    def testGetLocaleReturnsCurrentValue(self) -> None:
        """Return the currently configured locale from getLocale.

        Validates that getLocale reflects the value set by setLocale.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setLocale("fr")
        self.assertEqual(DateTime.getLocale(), "fr")

    def testGetLocaleDefaultIsEn(self) -> None:
        """Return 'en' as the default locale before any configuration.

        Validates that the locale defaults to 'en' on a freshly reset
        class state.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(DateTime.getLocale(), _DEFAULT_LOCALE)


class TestDateTimeAdditionalInstantiation(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state before each test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()

    # ------------------------------------------------ local

    def testLocalReturnsPendulumDateTime(self) -> None:
        """Return a pendulum.DateTime from local.

        Validates that local() produces a pendulum.DateTime instance
        with the specified date components.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.local(2024, 6, 15, 10, 30, 45)
        self.assertIsInstance(result, pendulum.DateTime)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def testLocalUsesLocalTimezone(self) -> None:
        """Express the result of local() in the local system timezone.

        Validates that the timezone name is not UTC unless the local
        system timezone happens to be UTC.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.local(2024, 1, 1)
        self.assertEqual(result.timezone_name, pendulum.local_timezone().name)

    # ------------------------------------------------ naive

    def testNaiveReturnsDatetimeWithoutTimezone(self) -> None:
        """Return a timezone-naive datetime from naive.

        Validates that naive() produces a pendulum.DateTime whose
        timezone attribute is None.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.naive(2024, 6, 15, 10, 30, 45)
        self.assertIsInstance(result, pendulum.DateTime)
        self.assertIsNone(result.timezone)

    def testNaiveDefaultsMonthAndDayToOne(self) -> None:
        """Default month and day to 1 when only year is provided to naive.

        Validates that omitting optional components results in the
        first day of January.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.naive(2024)
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)

    # ------------------------------------------------ fromFormat

    def testFromFormatParsesCustomTokens(self) -> None:
        """Parse a date string using explicit pendulum format tokens.

        Validates that fromFormat() correctly interprets the supplied
        format string and returns a matching pendulum.DateTime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.fromFormat("15/06/2024", "DD/MM/YYYY")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def testFromFormatUsesConfiguredTimezone(self) -> None:
        """Use the configured timezone when tz is None in fromFormat.

        Validates that the produced datetime is expressed in the
        class-level default timezone.

        Returns
        -------
        None
            No return value.
        """
        DateTime._setTimezone("Asia/Tokyo")
        result = DateTime.fromFormat("2024-01-01", "YYYY-MM-DD")
        self.assertEqual(result.timezone_name, "Asia/Tokyo")

    def testFromFormatWithExplicitTzArgument(self) -> None:
        """Apply the explicit tz argument in fromFormat.

        Validates that passing tz overrides the class-level default
        timezone for the returned datetime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.fromFormat(
            "2024-01-01",
            "YYYY-MM-DD",
            tz="Europe/Paris",
        )
        self.assertEqual(result.timezone_name, "Europe/Paris")


class TestDateTimeDurationAndInterval(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state before each test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()

    # ------------------------------------------------ duration

    def testDurationCreatesPendulumDuration(self) -> None:
        """Return a pendulum.Duration from duration.

        Validates that duration() produces a Duration instance whose
        total hours match the supplied days and hours.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.duration(days=1, hours=2)
        self.assertIsInstance(result, pendulum.Duration)
        self.assertEqual(result.in_hours(), 26)

    def testDurationDefaultsToZero(self) -> None:
        """Return a zero-length Duration when no arguments are provided.

        Validates that duration() with no keyword arguments results in
        a Duration whose total seconds equal zero.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.duration()
        self.assertEqual(result.total_seconds(), 0)

    # ------------------------------------------------ interval

    def testIntervalCreatesPendulumInterval(self) -> None:
        """Return a pendulum.Interval from interval.

        Validates that interval() produces an Interval instance spanning
        the correct number of days between two datetimes.

        Returns
        -------
        None
            No return value.
        """
        start = DateTime.datetime(2024, 1, 1, tz="UTC")
        end = DateTime.datetime(2024, 1, 31, tz="UTC")
        result = DateTime.interval(start, end)
        self.assertIsInstance(result, pendulum.Interval)
        self.assertEqual(result.in_days(), 30)

    def testIntervalWithAbsoluteTrueIsAlwaysPositive(self) -> None:
        """Force a positive interval when absolute is True.

        Validates that interval() with absolute=True returns a
        non-negative day count even when start is after end.

        Returns
        -------
        None
            No return value.
        """
        start = DateTime.datetime(2024, 1, 31, tz="UTC")
        end = DateTime.datetime(2024, 1, 1, tz="UTC")
        result = DateTime.interval(start, end, absolute=True)
        self.assertGreaterEqual(result.in_days(), 0)


class TestDateTimeGenericModifiers(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state and build a stable reference datetime.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        self.ref = DateTime.datetime(2024, 6, 12, 14, 30, 45, tz="UTC")

    # ------------------------------------------------ startOf / endOf

    def testStartOfHourZeroesMinutesAndSeconds(self) -> None:
        """Return the given hour with minutes and seconds zeroed.

        Validates that startOf('hour') resets minute and second to
        zero while preserving the hour.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOf("hour", self.ref)
        self.assertEqual(result.hour, self.ref.hour)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.second, 0)

    def testEndOfHourSetsMinutesAndSecondsToMax(self) -> None:
        """Return the given hour with minutes and seconds at their maximum.

        Validates that endOf('hour') sets minute and second to 59.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.endOf("hour", self.ref)
        self.assertEqual(result.minute, 59)
        self.assertEqual(result.second, 59)

    def testStartOfWithoutDtUsesNow(self) -> None:
        """Use the current datetime when no dt is given to startOf.

        Validates that startOf() without a dt argument still returns
        a datetime with the seconds reset to zero for the 'minute' unit.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.startOf("minute")
        self.assertEqual(result.second, 0)


class TestDateTimeGenericArithmetic(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state and build a stable reference datetime.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        self.ref = DateTime.datetime(2024, 1, 1, 12, 0, 0, tz="UTC")

    # ------------------------------------------------ add / subtract

    def testAddCombinesMultipleUnits(self) -> None:
        """Add a combination of years, months, and days in a single call.

        Validates that add() applies all supplied units simultaneously.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.add(self.ref, years=1, months=2, days=3)
        self.assertEqual(result.year, 2025)
        self.assertEqual(result.month, 3)
        self.assertEqual(result.day, 4)

    def testAddWithNoUnitsReturnsSameInstant(self) -> None:
        """Return an equal datetime when no units are supplied to add.

        Validates that add() without arguments is an identity operation.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.add(self.ref)
        self.assertEqual(result, self.ref)

    def testSubtractCombinesMultipleUnits(self) -> None:
        """Subtract a combination of weeks and hours in a single call.

        Validates that subtract() applies all supplied units
        simultaneously.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.subtract(self.ref, weeks=1, hours=6)
        self.assertEqual(result.day, 25)
        self.assertEqual(result.month, 12)
        self.assertEqual(result.hour, 6)

    def testAddAndSubtractAreInverses(self) -> None:
        """Return to the original instant after add() followed by subtract().

        Validates that applying add() and then subtract() with the same
        units is a round trip.

        Returns
        -------
        None
            No return value.
        """
        shifted = DateTime.add(self.ref, days=10, hours=4)
        restored = DateTime.subtract(shifted, days=10, hours=4)
        self.assertEqual(restored, self.ref)

    # ------------------------------------------------ diff / diffForHumans

    def testDiffReturnsIntervalWithExpectedDays(self) -> None:
        """Return a pendulum.Interval from diff with the correct day count.

        Validates that diff() computes an Interval whose in_days()
        matches the elapsed time between the two datetimes.

        Returns
        -------
        None
            No return value.
        """
        other = DateTime.add(self.ref, days=15)
        result = DateTime.diff(self.ref, other)
        self.assertIsInstance(result, pendulum.Interval)
        self.assertEqual(result.in_days(), 15)

    def testDiffWithAbsoluteFalseCanBeNegative(self) -> None:
        """Return a negative interval when absolute is False and dt2 is earlier.

        Validates that diff() with absolute=False reflects the sign of
        the temporal ordering between the two datetimes.

        Returns
        -------
        None
            No return value.
        """
        earlier = DateTime.subtract(self.ref, days=5)
        result = DateTime.diff(self.ref, earlier, absolute=False)
        self.assertLess(result.in_days(), 0)

    def testDiffForHumansReturnsNonEmptyString(self) -> None:
        """Return a human-readable phrase from diffForHumans.

        Validates that diffForHumans() produces a non-empty string
        describing the relative difference between two datetimes.

        Returns
        -------
        None
            No return value.
        """
        other = DateTime.add(self.ref, days=7)
        result = DateTime.diffForHumans(self.ref, other)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)


class TestDateTimeFluentModifiers(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state and build a stable reference datetime.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()
        # Monday, January 1 2024
        self.ref = DateTime.datetime(2024, 1, 1, tz="UTC")

    # ------------------------------------------------ next / previous

    def testNextReturnsUpcomingWeekday(self) -> None:
        """Return the next occurrence of the given weekday from next.

        Validates that next() advances to the requested day of the
        week following the reference datetime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.next(self.ref, pendulum.WEDNESDAY)
        self.assertEqual(result.day_of_week, pendulum.WEDNESDAY)
        self.assertGreater(result, self.ref)

    def testPreviousReturnsPriorWeekday(self) -> None:
        """Return the previous occurrence of the given weekday from previous.

        Validates that previous() moves back to the requested day of
        the week before the reference datetime.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.previous(self.ref, pendulum.WEDNESDAY)
        self.assertEqual(result.day_of_week, pendulum.WEDNESDAY)
        self.assertLess(result, self.ref)

    # ------------------------------------------------ average

    def testAverageReturnsMidpointBetweenDates(self) -> None:
        """Return the midpoint datetime from average.

        Validates that average() produces a datetime exactly halfway
        between the reference and the supplied datetime.

        Returns
        -------
        None
            No return value.
        """
        other = DateTime.add(self.ref, days=10)
        result = DateTime.average(self.ref, other)
        self.assertEqual(result.day, 6)

    # ------------------------------------------------ firstOf / lastOf / nthOf

    def testFirstOfMonthReturnsDayOne(self) -> None:
        """Return the first day of the month from firstOf.

        Validates that firstOf('month') without a weekday constraint
        returns the first calendar day of the month.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.firstOf(self.ref, "month")
        self.assertEqual(result.day, 1)

    def testLastOfMonthReturnsFinalDay(self) -> None:
        """Return the last day of the month from lastOf.

        Validates that lastOf('month') without a weekday constraint
        returns the final calendar day of the month (January has 31).

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.lastOf(self.ref, "month")
        self.assertEqual(result.day, 31)

    def testNthOfMonthReturnsCorrectOccurrence(self) -> None:
        """Return the n-th occurrence of a weekday within the month.

        Validates that nthOf('month', 2, MONDAY) returns the second
        Monday of January 2024, which falls on the 8th.

        Returns
        -------
        None
            No return value.
        """
        result = DateTime.nthOf(self.ref, "month", 2, pendulum.MONDAY)
        self.assertEqual(result.day, 8)
        self.assertEqual(result.day_of_week, pendulum.MONDAY)


class TestDateTimeAdditionalPredicates(_DateTimeTestCase):
    def setUp(self) -> None:
        """Reset class state before each test.

        Returns
        -------
        None
            No return value.
        """
        super().setUp()

    # ------------------------------------------------ isLeapYear

    def testIsLeapYearReturnsTrueForLeapYear(self) -> None:
        """Return True when the given year is a leap year.

        Validates that isLeapYear() correctly identifies 2024 as a
        leap year.

        Returns
        -------
        None
            No return value.
        """
        dt = DateTime.datetime(2024, 1, 1, tz="UTC")
        self.assertTrue(DateTime.isLeapYear(dt))

    def testIsLeapYearReturnsFalseForNonLeapYear(self) -> None:
        """Return False when the given year is not a leap year.

        Validates that isLeapYear() correctly rejects 2023 as a
        non-leap year.

        Returns
        -------
        None
            No return value.
        """
        dt = DateTime.datetime(2023, 1, 1, tz="UTC")
        self.assertFalse(DateTime.isLeapYear(dt))

    # ------------------------------------------------ isBirthday

    def testIsBirthdayReturnsTrueForMatchingMonthAndDay(self) -> None:
        """Return True when month and day match between two dates.

        Validates that isBirthday() correctly identifies a date sharing
        the same month and day as another, regardless of year.

        Returns
        -------
        None
            No return value.
        """
        born = DateTime.datetime(1990, 4, 23, tz="UTC")
        other = DateTime.datetime(2024, 4, 23, tz="UTC")
        self.assertTrue(DateTime.isBirthday(born, other))

    def testIsBirthdayReturnsFalseForDifferentMonthOrDay(self) -> None:
        """Return False when month or day differ between two dates.

        Validates that isBirthday() correctly rejects dates that do not
        share the same month and day.

        Returns
        -------
        None
            No return value.
        """
        born = DateTime.datetime(1990, 4, 23, tz="UTC")
        other = DateTime.datetime(2024, 9, 26, tz="UTC")
        self.assertFalse(DateTime.isBirthday(born, other))

    # ------------------------------------------------ closest / farthest

    def testClosestReturnsNearestCandidate(self) -> None:
        """Return the candidate closest to the reference datetime.

        Validates that closest() selects the candidate with the smallest
        temporal distance to the reference.

        Returns
        -------
        None
            No return value.
        """
        ref = DateTime.datetime(2024, 1, 10, tz="UTC")
        near = DateTime.datetime(2024, 1, 11, tz="UTC")
        far = DateTime.datetime(2024, 3, 1, tz="UTC")
        result = DateTime.closest(ref, far, near)
        self.assertEqual(result, near)

    def testFarthestReturnsFurthestCandidate(self) -> None:
        """Return the candidate farthest from the reference datetime.

        Validates that farthest() selects the candidate with the
        largest temporal distance to the reference.

        Returns
        -------
        None
            No return value.
        """
        ref = DateTime.datetime(2024, 1, 10, tz="UTC")
        near = DateTime.datetime(2024, 1, 11, tz="UTC")
        far = DateTime.datetime(2024, 3, 1, tz="UTC")
        result = DateTime.farthest(ref, far, near)
        self.assertEqual(result, far)
