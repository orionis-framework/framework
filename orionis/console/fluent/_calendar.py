"""
Schedule recurring commands against the local calendar.

Calendar triggers evaluate cron fields in the zone captured by each task.
"""

from __future__ import annotations
from datetime import UTC, datetime, timedelta
from apscheduler.triggers.cron import CronTrigger


def _after_transition(local: datetime) -> datetime:
    """
    Find the first unambiguous wall second after a clock transition.

    Parameters
    ----------
    local : datetime.datetime
        Local time inside a gap or repeated interval.

    Returns
    -------
    datetime.datetime
        Earliest ordinary local time following that interval.
    """
    first = local.replace(fold=0, microsecond=0)
    difference = first.replace(fold=1).utcoffset() - first.utcoffset()
    low, high = 0, int(abs(difference).total_seconds())
    while high - low > 1:
        middle = (low + high) // 2
        probe = first + timedelta(seconds=middle)
        if probe.utcoffset() == probe.replace(fold=1).utcoffset():
            high = middle
        else:
            low = middle
    return first + timedelta(seconds=high)


class CalendarCronTrigger(CronTrigger):
    """
    Choose the first occurrence of each existing local cron time.

    A forward clock change skips nonexistent matches. A backward change
    schedules each repeated wall time once.

    Attributes
    ----------
    _calendar : ``CronTrigger``
        Cached UTC trigger that searches the task's cron fields by wall time.
    """

    __slots__ = ("_calendar",)
    """Reserve storage for the cached calendar trigger."""

    def _getNextFireTime(
        self,
        previous_fire_time: datetime | None,
        now: datetime,
    ) -> datetime | None:
        """
        Find the next cron match within the task's scheduling window.

        Parameters
        ----------
        previous_fire_time : datetime.datetime or None
            Last scheduled instant, or None before the first run.
        now : datetime.datetime
            Scheduler clock used to find the first run.

        Returns
        -------
        datetime.datetime or None
            Next run in the task zone after any jitter, or None when exhausted.
        """
        earliest = (
            previous_fire_time.astimezone(UTC) + timedelta(microseconds=1)
            if previous_fire_time is not None
            else now.astimezone(UTC)
        )
        if self.start_date is not None:
            earliest = max(earliest, self.start_date.astimezone(UTC))
        local = earliest.astimezone(self.timezone)
        if local.fold:
            local = _after_transition(local)

        # Search calendar fields on a uniform clock, then interpret the matched
        # components in the task zone. Cache only the compiled field search;
        # APScheduler's serialized state already contains all its inputs.
        if not hasattr(self, "_calendar"):
            calendar = CronTrigger(timezone=UTC)
            calendar.fields = self.fields
            self._calendar = calendar
        cursor = local.replace(tzinfo=UTC)
        end = self.end_date.astimezone(UTC) if self.end_date is not None else None
        while matched := self._calendar.get_next_fire_time(None, cursor):
            candidate = matched.replace(tzinfo=self.timezone, fold=0)
            instant = candidate.astimezone(UTC)
            if instant.astimezone(self.timezone) != candidate:
                cursor = _after_transition(candidate).replace(tzinfo=UTC)
                continue
            if end is not None and instant > end:
                return None
            result = self._apply_jitter(instant, self.jitter, now)
            if end is not None:
                result = min(result, end)
            return result.astimezone(self.timezone)
        return None

    # APScheduler invokes this hook by its external protocol name.
    get_next_fire_time = _getNextFireTime
