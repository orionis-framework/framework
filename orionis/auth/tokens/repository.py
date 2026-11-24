# ruff: noqa: PLC0415, S105, TC001, TC003
# Keep runtime types; token is a column name and lookup loads lazily.
"""Persist personal access tokens through the Orionis query builder."""

from datetime import UTC, datetime, timedelta, tzinfo
from typing import Self
import msgspec
from orionis.auth.concerns.functions import authorizable_key
from orionis.auth.contracts.token_repository import IAccessTokenRepository
from orionis.auth.entities.access_token import AccessToken
from orionis.auth.entities.new_access_token import NewAccessToken
from orionis.auth.exceptions import TokenException
from orionis.auth.tokens.functions import generate_token_secret, hash_token_secret
from orionis.foundation.contracts.application import IApplication
from orionis.orm.contracts.query_builder import IQueryBuilder
from collections.abc import Iterable
from orionis.auth.contracts.authorizable import IAuthorizable
from orionis.orm.query.base_builder import QueryBuilderBase
from orionis.support.facades import DateTime


# Fallbacks applied when the configuration section is absent.
_DEFAULT_TABLE: str = "personal_access_tokens"
"""Fallbacks applied when the configuration section is absent."""
_DEFAULT_SECRET_BYTES: int = 40
"""Default secret bytes value used by ``repository``."""
_MAX_TOKEN_LENGTH: int = 512
"""Max token length value used by ``repository``."""
_MAX_NAME_LENGTH: int = 255
"""Max name length value used by ``repository``."""
_MAX_ABILITIES: int = 256
"""Max abilities value used by ``repository``."""

# Column holding the digest of the presented secret.
_TOKEN_COLUMN: str = "token"
"""Column holding the digest of the presented secret."""


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

    __slots__ = ("__db", "__expiration", "__secret_bytes", "__table")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self: Self, app: IApplication, db: IQueryBuilder) -> None:
        """
        Initialise the repository from the token configuration.

        Parameters
        ----------
        app : orionis.IApplication
            Application exposing the ``auth.tokens`` configuration.
        db : orionis.orm.contracts.query_builder.IQueryBuilder
            Gateway used to build queries over the token table.

        Returns
        -------
        None
            No return value.
        """
        self.__db = db
        """Gateway used to build queries over the token table."""
        self.__table: str = app.config("auth.tokens.table") or _DEFAULT_TABLE
        """Database table used to persist access-token records."""
        self.__expiration: int | None = app.config("auth.tokens.expiration")
        """Expiration produced by ``app.config``."""
        self.__secret_bytes: int = (
            app.config("auth.tokens.secret_bytes") or _DEFAULT_SECRET_BYTES
        )
        """Encoded application secret used to protect token lookups."""

    async def create(
        self: Self,
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
        tokenable : orionis.auth.contracts.IAuthorizable
            Identity the token belongs to.
        name : str
            Human readable label describing the token.
        abilities : collections.abc.Iterable[str] | None, optional
            Abilities the token may use, or ``None`` to keep the full
            authorization of the identity.
        expires_at : datetime.datetime | None, optional
            Explicit expiration. A value without an offset uses the application
            timezone. ``None`` applies the configured lifetime.

        Returns
        -------
        orionis.auth.entities.NewAccessToken
            Stored metadata plus the plain text value of the token.

        Raises
        ------
        orionis.auth.TokenException
            If the name, expiration or abilities are invalid, or the inserted token
            cannot be recovered.
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
        deadline = _as_datetime(expires_at, naive_zone=DateTime.getZoneInfo())
        if deadline is None and self.__expiration is not None:
            deadline = issued_at + timedelta(minutes=self.__expiration)

        granted = _normalize_abilities(abilities)
        tokenable_type, tokenable_id = authorizable_key(tokenable)

        result = await self.__db.table(self.__table).insert(
            {
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
            },
        )

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
            created_at=DateTime.fromDatetime(issued_at),
            expires_at=DateTime.fromDatetime(deadline) if deadline else None,
        )
        return NewAccessToken(access_token=access_token, plain_text=plain_text)

    async def findByPlainText(self: Self, plain_text: str) -> AccessToken | None:
        """
        Resolve a token from the value presented by the client.

        Parameters
        ----------
        plain_text : str
            Value received in the ``Authorization`` header.

        Returns
        -------
        orionis.auth.entities.AccessToken | None
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

        return self._fromRow(row)

    async def findWithIdentity(
        self: Self,
        plain_text: str,
        identities: object,
    ) -> object:
        """
        Combine native ORM reads, or opt out for custom implementations.

        Parameters
        ----------
        plain_text : str
            Presented credential, hashed before constructing the query.
        identities : object
            Identity provider whose lookup semantics must be preserved.

        Returns
        -------
        object
            (token, identity), None for no match, or NotImplemented for fallback.
        """
        from orionis.auth.tokens.lookup import lookup_owner

        if type(self).findByPlainText is not AccessTokenRepository.findByPlainText:
            return NotImplemented
        if (
            not isinstance(plain_text, str)
            or not plain_text
            or len(plain_text) > _MAX_TOKEN_LENGTH
        ):
            return None
        return await lookup_owner(
            self.__db.table(self.__table)
            .where(_TOKEN_COLUMN, hash_token_secret(plain_text))
            .whereNull("revoked_at")
            .where(_unexpired_tokens),
            identities,
            self._fromRow,
        )

    @staticmethod
    def _fromRow(row: dict) -> AccessToken | None:
        """
        Validate stored metadata equally for separate and combined reads.

        Parameters
        ----------
        row : dict
            Stored token metadata returned by the database.

        Returns
        -------
        orionis.auth.entities.AccessToken | None
            Validated token, or None for invalid, revoked or expired metadata.
        """
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
            created_at=DateTime.fromDatetime(created_at) if created_at else None,
            expires_at=DateTime.fromDatetime(expires_at) if expires_at else None,
            last_used_at=DateTime.fromDatetime(last_used_at) if last_used_at else None,
        )

    async def touch(self: Self, token_id: object) -> bool:
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

    async def revoke(self: Self, token_id: object) -> bool:
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

    async def revokeAll(self: Self, tokenable: IAuthorizable) -> int:
        """
        Revoke every active token of an identity.

        Parameters
        ----------
        tokenable : orionis.auth.contracts.IAuthorizable
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

    async def purgeExpired(self: Self) -> int:
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
            self.__db.table(self.__table).whereNotNull("revoked_at").delete()
        )
        return expired + revoked


def _utc_now() -> datetime:
    """
    Return the current UTC instant for persistence and validity checks.

    Returns
    -------
    datetime.datetime
        Current UTC moment with timezone information.
    """
    return datetime.now(UTC)


def _as_datetime(value: object, *, naive_zone: tzinfo = UTC) -> datetime | None:
    """
    Convert a token deadline or stored timestamp to UTC.

    Parameters
    ----------
    value : object
        Expiration supplied by the caller or a timestamp read as text or datetime.
    naive_zone : datetime.tzinfo, optional
        Source timezone for an offset-less value. Stored timestamps use UTC.

    Returns
    -------
    datetime.datetime | None
        Parsed UTC moment, or ``None`` for SQL NULL.

    Raises
    ------
    orionis.auth.TokenException
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
    if value.tzinfo is None:
        value = value.replace(tzinfo=naive_zone)
    return value.astimezone(UTC)


def _unexpired_tokens(query: QueryBuilderBase) -> None:
    """
    Group the nullable expiration constraint for token use.

    Parameters
    ----------
    query : orionis.orm.query.base_builder.QueryBuilderBase
        Nested group assembled by the query builder.

    Returns
    -------
    None
        No return value.
    """
    query.whereNull("expires_at").orWhere("expires_at", ">", _utc_now())


def _is_expired(value: datetime | None) -> bool:
    """
    Report whether an expiration moment already elapsed.

    Parameters
    ----------
    value : datetime.datetime | None
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
    return moment <= _utc_now()


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
    orionis.auth.TokenException
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
    abilities : collections.abc.Iterable[str] | None
        Explicit restrictions, or None for an unrestricted credential.

    Returns
    -------
    frozenset[str] | None
        Deduplicated, validated abilities.

    Raises
    ------
    orionis.auth.TokenException
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
