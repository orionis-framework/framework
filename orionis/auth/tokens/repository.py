from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
import msgspec
from orionis.auth.concerns.functions import authorizable_key
from orionis.auth.contracts.token_repository import IAccessTokenRepository
from orionis.auth.entities.access_token import AccessToken
from orionis.auth.entities.new_access_token import NewAccessToken
from orionis.auth.exceptions import TokenException
from orionis.auth.tokens.functions import generate_token_secret, hash_token_secret
from orionis.foundation.contracts.application import IApplication
from orionis.orm.contracts.query_builder import IQueryBuilder

if TYPE_CHECKING:
    from collections.abc import Iterable
    from orionis.auth.contracts.authorizable import IAuthorizable
    from orionis.orm.query.base_builder import QueryBuilderBase

# Fallbacks applied when the configuration section is absent.
_DEFAULT_TABLE: str = "personal_access_tokens"
_DEFAULT_SECRET_BYTES: int = 40
_MAX_TOKEN_LENGTH: int = 512
_MAX_NAME_LENGTH: int = 255
_MAX_ABILITIES: int = 256

# Column holding the digest of the presented secret.
_TOKEN_COLUMN: str = "token"  # noqa: S105

class AccessTokenRepository(IAccessTokenRepository):
    """
    Persist personal access tokens through the Orionis query builder.

    Tokens are opaque: the client receives a random secret and the store
    only keeps its SHA-256 digest in a unique column. Verification is a
    single indexed lookup on that digest, so no plain text secret ever
    needs to be compared.

    Concurrency
    -----------
    Issuance uses a unique digest, with an optional ID lookup for drivers
    that do not return generated keys. Revocation and usage confirmation
    use conditional updates. Usage cannot reactivate a revoked token;
    concurrent timestamps are last-writer-wins. Purging uses two deletes.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("__db", "__expiration", "__secret_bytes", "__table")

    def __init__(self, app: IApplication, db: IQueryBuilder) -> None:
        """
        Initialise the repository from the token configuration.

        Parameters
        ----------
        app : IApplication
            Application exposing the ``auth.tokens`` configuration.
        db : IQueryBuilder
            Gateway used to build queries over the token table.

        Returns
        -------
        None
            Only configuration values and the gateway are retained.
        """
        self.__db = db
        self.__table: str = app.config("auth.tokens.table") or _DEFAULT_TABLE
        self.__expiration: int | None = app.config("auth.tokens.expiration")
        self.__secret_bytes: int = (
            app.config("auth.tokens.secret_bytes") or _DEFAULT_SECRET_BYTES
        )

    async def create(
        self,
        tokenable: IAuthorizable,
        name: str,
        *,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
        """
        Issue a new personal access token for an identity.

        Parameters
        ----------
        tokenable : IAuthorizable
            Identity the token belongs to.
        name : str
            Human readable label describing the token.
        abilities : Iterable[str] | None, optional
            Abilities the token may use, or ``None`` to keep the full
            authorization of the identity.
        expires_at : datetime | None, optional
            Explicit expiration. ``None`` applies the configured default.

        Returns
        -------
        NewAccessToken
            Stored metadata plus the plain text value of the token.

        Raises
        ------
        TokenException
            When the token name is empty.
        """
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name) > _MAX_NAME_LENGTH
        ):
            error_msg = "A personal access token requires a non-empty name."
            raise TokenException(error_msg)

        plain_text = generate_token_secret(self.__secret_bytes)
        digest = hash_token_secret(plain_text)
        issued_at = _utc_now()

        # Fall back to the configured lifetime when no explicit moment is
        # requested; a null expiration keeps the token alive until revoked.
        deadline = _as_datetime(expires_at)
        if deadline is None and self.__expiration is not None:
            deadline = issued_at + timedelta(minutes=self.__expiration)

        granted = _normalize_abilities(abilities)
        tokenable_type, tokenable_id = authorizable_key(tokenable)

        result = await self.__db.table(self.__table).insert({
            "tokenable_type": tokenable_type,
            "tokenable_id": tokenable_id,
            "name": name,
            _TOKEN_COLUMN: digest,
            "abilities": _encode_abilities(granted),
            "expires_at": deadline,
            "last_used_at": None,
            "revoked_at": None,
            "created_at": issued_at,
            "updated_at": issued_at,
        })

        token_id = result.last_insert_id
        if token_id is None:
            row = await (
                self.__db.table(self.__table)
                .select("id")
                .where(_TOKEN_COLUMN, digest)
                .first()
            )
            if row is None:
                error_msg = "The newly issued token is no longer available."
                raise TokenException(error_msg)
            token_id = row["id"]

        access_token = AccessToken(
            id=token_id,
            tokenable_type=tokenable_type,
            tokenable_id=tokenable_id,
            name=name,
            abilities=granted,
            created_at=issued_at,
            expires_at=deadline,
        )
        return NewAccessToken(access_token=access_token, plain_text=plain_text)

    async def findByPlainText(self, plain_text: str) -> AccessToken | None:
        """
        Resolve a token from the value presented by the client.

        Parameters
        ----------
        plain_text : str
            Value received in the ``Authorization`` header.

        Returns
        -------
        AccessToken | None
            Matching token, or ``None`` when the value is unknown, has
            been revoked or has already expired.
        """
        if (
            not isinstance(plain_text, str)
            or not plain_text
            or len(plain_text) > _MAX_TOKEN_LENGTH
        ):
            return None

        row = await (
            self.__db.table(self.__table)
            .where(_TOKEN_COLUMN, hash_token_secret(plain_text))
            .first()
        )
        if row is None:
            return None

        # A revoked token is treated exactly like an unknown one.
        if row.get("revoked_at") is not None:
            return None

        try:
            expires_at = _as_datetime(row.get("expires_at"))
            abilities = _decode_abilities(row.get("abilities"))
            created_at = _as_datetime(row.get("created_at"))
            last_used_at = _as_datetime(row.get("last_used_at"))
        except TokenException:
            return None
        if _is_expired(expires_at):
            return None

        return AccessToken(
            id=row.get("id"),
            tokenable_type=str(row.get("tokenable_type")),
            tokenable_id=row.get("tokenable_id"),
            name=str(row.get("name")),
            abilities=abilities,
            created_at=created_at,
            expires_at=expires_at,
            last_used_at=last_used_at,
        )

    async def touch(self, token_id: object) -> bool:
        """
        Confirm token validity and record its use atomically.

        Parameters
        ----------
        token_id : object
            Identifier of the token to update.

        Returns
        -------
        bool
            True only if a non-revoked, unexpired row was updated. This
            is the final validity check before a guard publishes identity.
        """
        if token_id is None:
            return False

        affected = await (
            self.__db.table(self.__table)
            .where("id", token_id)
            .whereNull("revoked_at")
            .where(_unexpired_tokens)
            .update({"last_used_at": _utc_now()})
        )
        return affected > 0

    async def revoke(self, token_id: object) -> bool:
        """
        Revoke a single token.

        Parameters
        ----------
        token_id : object
            Identifier of the token to revoke.

        Returns
        -------
        bool
            True when this call revoked a token that was still active.
        """
        if token_id is None:
            return False

        now = _utc_now()
        affected = await (
            self.__db.table(self.__table)
            .where("id", token_id)
            .whereNull("revoked_at")
            .update({"revoked_at": now, "updated_at": now})
        )
        return affected > 0

    async def revokeAll(self, tokenable: IAuthorizable) -> int:
        """
        Revoke every active token of an identity.

        Parameters
        ----------
        tokenable : IAuthorizable
            Identity whose tokens must be revoked.

        Returns
        -------
        int
            Number of tokens revoked by this call.
        """
        now = _utc_now()
        tokenable_type, tokenable_id = authorizable_key(tokenable)
        return await (
            self.__db.table(self.__table)
            .where("tokenable_type", tokenable_type)
            .where("tokenable_id", tokenable_id)
            .whereNull("revoked_at")
            .update({"revoked_at": now, "updated_at": now})
        )

    async def purgeExpired(self) -> int:
        """
        Delete tokens that expired or were revoked.

        Returns
        -------
        int
            Number of rows removed from the store.
        """
        now = _utc_now()
        expired = await (
            self.__db.table(self.__table)
            .whereNotNull("expires_at")
            .where("expires_at", "<=", now)
            .delete()
        )
        revoked = await (
            self.__db.table(self.__table)
            .whereNotNull("revoked_at")
            .delete()
        )
        return expired + revoked

def _utc_now() -> datetime:
    """
    Return the current UTC moment as a naive datetime.

    Token columns are declared without a timezone so every dialect stores
    the same value. Dropping the offset here keeps writes and reads
    symmetric across SQLite, PostgreSQL and MySQL.

    Returns
    -------
    datetime
        Current UTC moment without timezone information.
    """
    return datetime.now(UTC).replace(tzinfo=None)

def _as_datetime(value: object) -> datetime | None:
    """
    Coerce a stored timestamp into a datetime.

    Queries over a table the builder knows no schema for come back with
    whatever the driver produced, and SQLite hands timestamps back as
    plain strings. Normalising here keeps the expiration check correct on
    every dialect.

    Parameters
    ----------
    value : object
        Raw value read from a timestamp column.

    Returns
    -------
    datetime | None
        Parsed UTC moment without an offset, or ``None`` for SQL NULL.

    Raises
    ------
    TokenException
        If a non-null timestamp is malformed.
    """
    if value is None:
        return None
    if isinstance(value, str) and value:
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            error_msg = "Invalid token timestamp."
            raise TokenException(error_msg) from None
    if not isinstance(value, datetime):
        error_msg = "Invalid token timestamp."
        raise TokenException(error_msg)
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value

def _unexpired_tokens(query: QueryBuilderBase) -> None:
    """
    Group the nullable expiration constraint for token use.

    Parameters
    ----------
    query : QueryBuilderBase
        Nested group assembled by the query builder.

    Returns
    -------
    None
        The group accepts only unexpired tokens or SQL NULL deadlines.
    """
    query.whereNull("expires_at").orWhere("expires_at", ">", _utc_now())

def _is_expired(value: datetime | None) -> bool:
    """
    Report whether an expiration moment already elapsed.

    Parameters
    ----------
    value : datetime | None
        Normalised expiration moment of the token.

    Returns
    -------
    bool
        True when the moment is in the past. A missing value means the
        token never expires on its own.
    """
    if value is None:
        return False

    # Values stored without an offset are UTC by construction.
    moment = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return moment <= datetime.now(UTC)

def _encode_abilities(abilities: frozenset[str] | None) -> str | None:
    """
    Serialise the abilities of a token for storage.

    Parameters
    ----------
    abilities : frozenset[str] | None
        Abilities granted to the token.

    Returns
    -------
    str | None
        Sorted JSON array, or ``None`` for an unrestricted token.
    """
    if abilities is None:
        return None
    return msgspec.json.encode(sorted(abilities)).decode("utf-8")

def _decode_abilities(value: object) -> frozenset[str] | None:
    """
    Deserialise the abilities stored for a token.

    Parameters
    ----------
    value : object
        Raw value read from the ``abilities`` column.

    Returns
    -------
    frozenset[str] | None
        Validated abilities, or ``None`` only for a SQL NULL value.

    Raises
    ------
    TokenException
        If the stored payload is not an array of non-empty strings.
    """
    if value is None:
        return None
    if isinstance(value, (str, bytes)):
        try:
            value = msgspec.json.decode(value)
        except ValueError:
            error_msg = "Invalid stored token abilities."
            raise TokenException(error_msg) from None
    if not isinstance(value, (list, tuple, set, frozenset)):
        error_msg = "Invalid stored token abilities."
        raise TokenException(error_msg)
    return _normalize_abilities(value)

def _normalize_abilities(abilities: Iterable[str] | None) -> frozenset[str] | None:
    """
    Validate credential restrictions without coercing malformed values.

    Parameters
    ----------
    abilities : Iterable[str] | None
        Explicit restrictions, or None for an unrestricted credential.

    Returns
    -------
    frozenset[str] | None
        Deduplicated, validated abilities.

    Raises
    ------
    TokenException
        If the input is a string or contains invalid ability names.
    """
    if abilities is None:
        return None
    error_msg = "Token abilities must be a bounded collection of non-empty strings."
    if isinstance(abilities, (str, bytes)):
        raise TokenException(error_msg)
    try:
        granted = frozenset(abilities)
    except TypeError:
        raise TokenException(error_msg) from None
    if len(granted) > _MAX_ABILITIES or any(
        not isinstance(ability, str)
        or not ability.strip()
        or len(ability) > _MAX_NAME_LENGTH
        for ability in granted
    ):
        raise TokenException(error_msg)
    return granted
