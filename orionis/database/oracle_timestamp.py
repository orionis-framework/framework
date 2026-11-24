"""
Preserve Oracle timestamp instants across database session timezones.

Use explicit UTC offsets for bound values and UTC projections for results.
"""

from __future__ import annotations
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from sqlalchemy import TIMESTAMP, cast, func, literal_column
from sqlalchemy.types import TypeDecorator
from orionis.support.facades.datetime import DateTime

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect
    from sqlalchemy.sql.elements import BindParameter, ColumnElement


class OracleZonedTimestamp(TypeDecorator[datetime]):
    """
    Bind and read Oracle TIMESTAMP WITH TIME ZONE values in UTC.

    The driver binds Python datetimes without their offsets and returns
    timestamps without timezone metadata.
    """

    impl = TIMESTAMP(timezone=True)
    """Declare the underlying Oracle timestamp type with timezone support."""
    cache_ok = True
    """Allow SQLAlchemy to cache statements that use this stateless type."""

    def _bindValue(self, value: datetime | None, _dialect: Dialect) -> datetime | None:
        """
        Normalize an input instant before the driver discards its offset.

        Parameters
        ----------
        value : datetime.datetime or None
            Timestamp to bind. Interpret naive inputs in the application zone.
        _dialect : ``sqlalchemy.engine.Dialect``
            Oracle dialect supplied by SQLAlchemy.

        Returns
        -------
        datetime.datetime or None
            UTC wall time, or None for SQL NULL.
        """
        if value is None:
            return None
        if value.utcoffset() is None:
            value = DateTime.fromDatetime(value)
        return value.astimezone(UTC).replace(tzinfo=None)

    def _bindExpression(self, bindvalue: BindParameter) -> ColumnElement:
        """
        Attach the UTC offset explicitly to each bound Oracle timestamp.

        Parameters
        ----------
        bindvalue : ``sqlalchemy.sql.elements.BindParameter``
            UTC wall time passed to the timestamp driver variable.

        Returns
        -------
        ``sqlalchemy.sql.elements.ColumnElement``
            Oracle timestamp with its UTC offset and fractional seconds.
        """
        return func.from_tz(cast(bindvalue, TIMESTAMP()), literal_column("'+00:00'"))

    def _columnExpression(self, column: ColumnElement) -> ColumnElement:
        """
        Extract the UTC instant before the driver decodes an Oracle timestamp.

        Parameters
        ----------
        column : ``sqlalchemy.sql.elements.ColumnElement``
            Zoned timestamp, including values stored with nonzero offsets.

        Returns
        -------
        ``sqlalchemy.sql.elements.ColumnElement``
            UTC timestamp projection with the result processor attached.
        """
        return func.sys_extract_utc(column, type_=self)

    def _readValue(self, value: datetime | None, _dialect: Dialect) -> datetime | None:
        """
        Restore the UTC metadata of a timestamp extracted by Oracle.

        Parameters
        ----------
        value : datetime.datetime or None
            UTC wall time returned by the driver.
        _dialect : ``sqlalchemy.engine.Dialect``
            Oracle dialect supplied by SQLAlchemy.

        Returns
        -------
        datetime.datetime or None
            Aware UTC datetime, or None for SQL NULL.
        """
        return value.replace(tzinfo=UTC) if value is not None else None

    process_bind_param = _bindValue
    bind_expression = _bindExpression
    column_expression = _columnExpression
    process_result_value = _readValue
