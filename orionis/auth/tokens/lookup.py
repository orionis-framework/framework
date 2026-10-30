from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, and_, case, cast, func, or_, select
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.database.connection import Connection
from orionis.database.dialect import resolve_driver
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.orm.query.raw_builder import RawQueryBuilder
from orionis.orm.schema.types.column_type import ColumnType

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import NotImplementedType
    from sqlalchemy.sql.elements import ColumnElement

# This integration deliberately uses the native builder/connection hooks. Custom
# providers, connections and nontrivial query shapes keep their original path.
# ruff: noqa: SLF001
_INTEGER_DIGITS = 19
_INTEGERS = frozenset(
    {
        ColumnType.BIG_INTEGER,
        ColumnType.INTEGER,
        ColumnType.SMALL_INTEGER,
        ColumnType.BIGINT,
        ColumnType.INT,
        ColumnType.SMALLINT,
    },
)
_STRINGS = frozenset(
    {
        ColumnType.STRING,
        ColumnType.UNICODE,
        ColumnType.CHAR,
        ColumnType.VARCHAR,
        ColumnType.NCHAR,
        ColumnType.NVARCHAR,
    },
)
_COLUMNS = (
    "id",
    "tokenable_type",
    "tokenable_id",
    "name",
    "abilities",
    "expires_at",
    "created_at",
    "last_used_at",
    "revoked_at",
)

def _integer_key(value: ColumnElement, length: Callable) -> ColumnElement:
    """
    Cast only bounded decimal strings, including on strict SQL engines.

    Parameters
    ----------
    value : ColumnElement
        SQL expression containing the stored string identifier.
    length : Callable
        Dialect-specific SQL string-length function.

    Returns
    -------
    ColumnElement
        Guarded integer cast, yielding SQL NULL for malformed keys.
    """
    digits = func.replace(value, "-", "")
    remainder = digits
    for digit in "0123456789":
        remainder = func.replace(remainder, digit, "")
    negative = value == "-" + digits
    valid = and_(
        or_(value == digits, negative),
        or_(length(remainder) == 0, remainder.is_(None)),
        length(digits).between(1, _INTEGER_DIGITS),
        or_(
            length(digits) < _INTEGER_DIGITS,
            digits
            <= case((negative, "9223372036854775808"), else_="9223372036854775807"),
        ),
    )
    # CAST applies to CASE's safe result, never to untrusted malformed text.
    return cast(case((valid, value), else_=None), BigInteger)

async def lookup_owner(  # noqa: PLR0911
    query: RawQueryBuilder,
    identities: object,
    validate: Callable[[dict], object | None],
) -> tuple[object, object] | NotImplementedType | None:
    """Read a token and a native ORM identity in one bounded SELECT.

    Parameters
    ----------
    query : RawQueryBuilder
        Token digest query, with no plaintext credential in its bindings.
    identities : object
        Provider to optimize only when its native lookup semantics are known.
    validate : Callable
        Validate token metadata before hydrating or dispatching identity events.

    Returns
    -------
    tuple | None | NotImplemented
        Token row and hydrated identity, no match, or an unsupported combination.
        Retrieval events still run before the guard's final conditional touch.
    """
    if (
        type(identities) is not ModelIdentityProvider
        or type(query) is not RawQueryBuilder
    ):
        return NotImplemented
    model = identities.model()
    owner_query = model.query()
    if type(owner_query) is not ModelQueryBuilder:
        return NotImplemented
    owner_query._beforeExecute()
    plan = owner_query.toPlan()
    if (
        plan.joins
        or plan.columns
        or plan.groups
        or plan.havings
        or plan.unions
        or plan.aggregate
        or plan.distinct
        or plan.lock
        or plan.limit_value is not None
        or plan.offset_value is not None
    ):
        return NotImplemented
    connection = query._connection()
    if (
        type(connection) is not Connection
        or owner_query._connection() is not connection
    ):
        return NotImplemented
    key = model.__meta__.primary_key
    kind = model.__meta__.columns[key].column_type
    if kind not in _INTEGERS | _STRINGS:
        return NotImplemented
    token_plan = query.clone().select(*_COLUMNS).limit(1).toPlan()
    tokens = connection._compiler.compileSelect(token_plan).subquery("auth_token")
    # The scopes are isolated in their own SELECT to avoid ambiguous columns.
    owners = connection._compiler.compileSelect(plan).subquery("auth_owner")
    owner_id = tokens.c.tokenable_id
    length = (
        func.len if resolve_driver(connection._config) == "sqlserver" else func.length
    )
    if kind in _INTEGERS:
        owner_id = _integer_key(owner_id, length)
    token_columns = [tokens.c[name].label("token_" + name) for name in _COLUMNS]
    statement = (
        select(*token_columns, *owners.c)
        .select_from(tokens.join(owners, owners.c[key] == owner_id))
        .where(length(tokens.c.tokenable_id).between(1, 255))
        .limit(1)
    )
    async with connection._acquire() as raw:
        result = await connection._run(raw, statement)
        row = next(iter(result.mappings()), None)
        if row is None:
            return None
        token = validate(
            dict(
                zip(
                    _COLUMNS,
                    (row[column] for column in token_columns),
                    strict=True,
                ),
            ),
        )
        if token is None:
            return None
        owner = {column.key: row[column] for column in owners.c}
    instance = model._newFromDatabase(owner)
    await owner_query._fireRetrieved([instance])
    if owner_query._eager_loads:
        await owner_query._eagerLoad([instance])
    return token, instance
