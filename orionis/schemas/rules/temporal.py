from datetime import date, datetime
from typing import TYPE_CHECKING
from orionis.support.facades.datetime import DateTime

if TYPE_CHECKING:
    import pendulum

def to_datetime(value: object) -> pendulum.DateTime | None:
    """
    Coerce a value into a timezone-aware datetime.

    Parameters
    ----------
    value : object
        Value to coerce. Accepts ``datetime``, ``date`` and strings.

    Returns
    -------
    pendulum.DateTime | None
        Coerced datetime, or ``None`` when the value is not a moment.
    """
    # ``pendulum.DateTime`` subclasses ``datetime``, so it is handled here too.
    if isinstance(value, datetime):
        return DateTime.fromDatetime(value)

    if isinstance(value, date):
        return DateTime.datetime(value.year, value.month, value.day)

    if isinstance(value, str):
        return parse_moment(value)

    return None

def parse_moment(text: str) -> pendulum.DateTime | None:
    """
    Parse a textual moment, honouring the relative keywords.

    Parameters
    ----------
    text : str
        Date string or one of ``now``, ``today``, ``tomorrow``, ``yesterday``.

    Returns
    -------
    pendulum.DateTime | None
        Parsed datetime, or ``None`` when the text is not a valid date.
    """
    keyword = text.strip().lower()

    if keyword == "now":
        return DateTime.now()
    if keyword == "today":
        return DateTime.startOfDay(DateTime.now())
    if keyword == "tomorrow":
        return DateTime.startOfDay(DateTime.addDays(DateTime.now(), 1))
    if keyword == "yesterday":
        return DateTime.startOfDay(DateTime.addDays(DateTime.now(), -1))

    try:
        return DateTime.parse(text, strict=False)
    except (ValueError, TypeError):
        return None

def resolve_moment(reference: object, instance: object) -> pendulum.DateTime | None:
    """
    Resolve a rule reference into the datetime it points at.

    Parameters
    ----------
    reference : object
        Field name, date string, ``datetime``/``date`` value, or ``None`` to
        use the current moment.
    instance : object
        Schema instance used to resolve sibling field names.

    Returns
    -------
    pendulum.DateTime | None
        Resolved datetime, or ``None`` when the reference is not a moment.
    """
    if reference is None:
        return DateTime.now()

    # A string may name a sibling field before being treated as a date.
    if isinstance(reference, str):
        sibling = getattr(instance, reference, None)
        if sibling is not None:
            return to_datetime(sibling)

    return to_datetime(reference)
