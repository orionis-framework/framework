# ruff: noqa: PLC0415, SLF001, TC001
# Keep runtime annotations, guarded exits, and framework integration explicit.
"""Issue hashed credentials and consume them with the password atomically."""

import re
import secrets
import time
from orionis.auth.contracts.authorizable import IAuthorizable
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.auth.tokens.functions import hash_token_secret
from orionis.auth.tokens.repository import AccessTokenRepository
from orionis.database.exceptions import QueryException
from orionis.foundation.config.auth.entities.password_reset import PasswordReset
from orionis.foundation.contracts.application import IApplication
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.orm.contracts.query_builder import IQueryBuilder

import orionis.orm as _orm
from orionis.orm.contracts.raw_builder import IRawQueryBuilder


class _StalePassword(Exception):
    """Roll back consumption if the identity changed during reset."""


class PasswordBroker:
    """Issue hashed credentials and consume them with the password atomically."""

    def __init__(
        self,
        app: IApplication,
        db: IQueryBuilder,
        hashing: IHashManager,
    ) -> None:
        """
        Initialize the broker with the configured identity and services.

        Parameters
        ----------
        app : orionis.IApplication
            Application providing password-reset configuration.
        db : orionis.orm.contracts.query_builder.IQueryBuilder
            Query builder used to access the reset table.
        hashing : orionis.hashing.contracts.IHashManager
            Password hasher used to fingerprint and replace passwords.

        Returns
        -------
        None
            No return value.
        """
        # Resolve the configured identity once for this broker.
        self.settings = PasswordReset(**(app.config("auth.passwords") or {}))
        """Resolve the configured identity once for this broker."""
        self.model = ModelIdentityProvider(app, hashing).model()
        """Model selected for generation or persistence."""
        self.db = db.connection(self.model.connection or db.getDefaultName())
        """Query builder used to access the reset table."""
        self.hashing = hashing
        """Password hasher used to fingerprint and replace passwords."""
        self.tokens = AccessTokenRepository(app, self.db)
        """Tokens produced by ``AccessTokenRepository``."""

    def _records(self, email: str) -> IRawQueryBuilder:
        """
        Build a query for the account's password-reset record.

        Parameters
        ----------
        email : str
            Normalized email address identifying the account.

        Returns
        -------
        orionis.orm.contracts.raw_builder.IRawQueryBuilder
            Fresh query scoped to the configured reset table and email.
        """
        # Keep each operation isolated in a fresh query builder.
        return self.db.table(self.settings.table).where("email", email)

    def _query(self) -> _orm.ModelQueryBuilder:
        """Build an identity query on the reset store's exact connection.

        Returns
        -------
        orionis.orm.query.ModelQueryBuilder
            Fresh scoped model query retaining the injected gateway's connection.
        """
        query = self.model.query()
        records = self._records("")
        query._bindConnectionManager(
            records._connection_manager,
            connection=records._connection(),
        )
        return query

    async def _creationConflict(self, email: str) -> bool:
        """Check an insert conflict without replacing its original failure.

        Parameters
        ----------
        email : str
            Address whose reset record may have been inserted concurrently.

        Returns
        -------
        bool
            Whether the recovery lookup confirms that a reset record now exists.
        """
        try:
            return await self._records(email).exists()
        except QueryException as error:
            from orionis.failure.runtime import capture

            await capture(
                error,
                flow="auth",
                phase="recovery",
                operation="password.create",
            )
            return False

    async def issue(self, email: str) -> tuple[_orm.Model, str] | None:
        """
        Issue a reset token when the account's cooldown has elapsed.

        Parameters
        ----------
        email : str
            Email address associated with the identity.

        Returns
        -------
        tuple[orionis.orm.Model, str] | None
            The identity and plain token when issued, or ``None`` when the
            identity is unknown or a recent token is still in its cooldown.
        """
        email = email.strip().lower()
        user = await self._query().where("email", email).first()
        if user is None:
            return None
        now = int(time.time())
        token = secrets.token_urlsafe(32)
        values = {
            "token": hash_token_secret(token),
            "user_id": str(user.getAuthIdentifier()),
            "password_fingerprint": hash_token_secret(user.getAuthPassword()),
            "created_at": now,
        }
        # Conditional writes, rather than a process-local lock, arbitrate
        # concurrent requests across workers. Consumed rows retain the cooldown.
        existing = await self._records(email).first()
        if existing is not None:
            updated = (
                await self._records(email)
                .where(
                    "created_at",
                    "<=",
                    now - self.settings.throttle,
                )
                .update(values)
            )
            return (user, token) if updated == 1 else None
        try:
            await self.db.table(self.settings.table).insert(
                {
                    "email": email,
                    **values,
                },
            )
        except QueryException as error:
            # Only swallow a competing insert; other database failures surface.
            if await self._creationConflict(email):
                from orionis.failure.runtime import capture

                await capture(
                    error,
                    flow="auth",
                    phase="recovery",
                    operation="password.create",
                    expected=True,
                )
                return None
            raise
        return user, token

    async def _resolve(self, email: str, token: str) -> _orm.Model | None:
        """
        Resolve a current reset token to its identity.

        Parameters
        ----------
        email : str
            Normalized email address associated with the token.
        token : str
            Plain reset token supplied by the caller.

        Returns
        -------
        orionis.orm.Model | None
            Matching identity when the token is valid and current, otherwise
            ``None``.
        """
        # Reject malformed credentials before querying persisted records.
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            return None
        row = (
            await self._records(email)
            .where(
                "token",
                hash_token_secret(token),
            )
            .where(
                "created_at",
                ">",
                int(time.time()) - self.settings.expiration * 60,
            )
            .first()
        )
        if row is None:
            return None
        user = await self._query().where("email", email).first()
        fingerprint = row["password_fingerprint"]
        if (
            user is None
            or str(user.getAuthIdentifier()) != row["user_id"]
            or not isinstance(fingerprint, str)
            or not fingerprint.isascii()
            or not secrets.compare_digest(
                hash_token_secret(user.getAuthPassword()),
                fingerprint,
            )
        ):
            return None
        return user

    async def valid(self, email: str, token: str) -> bool:
        """
        Validate a reset link without consuming its token.

        Parameters
        ----------
        email : str
            Email address associated with the token.
        token : str
            Plain reset token supplied by the caller.

        Returns
        -------
        bool
            ``True`` when the token resolves to the current identity;
            otherwise, ``False``.
        """
        # Normalize the address as issuance and consumption do.
        return await self._resolve(email.strip().lower(), token) is not None

    async def reset(self, email: str, token: str, password: str) -> _orm.Model | None:
        """
        Consume a reset token and atomically replace the password.

        Parameters
        ----------
        email : str
            Email address associated with the token.
        token : str
            Plain reset token supplied by the caller.
        password : str
            New plaintext password to hash and store.

        Returns
        -------
        orionis.orm.Model | None
            Updated identity when the reset succeeds, or ``None`` when the
            token is invalid, stale, expired, or already consumed.
        """
        email = email.strip().lower()
        user = await self._resolve(email, token)
        if user is None:
            return None
        previous = user.getAuthPassword()
        # Hash before opening the transaction to keep its critical section short.
        hashed = await self.hashing.make(password)
        try:
            async with self.db.transaction():
                consumed = (
                    await self._records(email)
                    .where(
                        "token",
                        hash_token_secret(token),
                    )
                    .where(
                        "created_at",
                        ">",
                        int(time.time()) - self.settings.expiration * 60,
                    )
                    .update({"token": None})
                )
                if consumed != 1:
                    return None
                values = {user.AUTH_PASSWORD: hashed}
                if "remember_token" in self.model.__meta__.columns:
                    values["remember_token"] = None
                updated = (
                    await self._query()
                    .where(
                        user.getAuthIdentifierName(),
                        user.getAuthIdentifier(),
                    )
                    .where("email", email)
                    .where(
                        user.AUTH_PASSWORD,
                        previous,
                    )
                    .update(values)
                )
                if updated != 1:
                    raise _StalePassword
                if isinstance(user, IAuthorizable):
                    await self.tokens.revokeAll(user)
                refreshed = (
                    await self._query()
                    .where(
                        user.getAuthIdentifierName(),
                        user.getAuthIdentifier(),
                    )
                    .first()
                )
                if refreshed is None:
                    raise _StalePassword
        except _StalePassword:
            return None
        return refreshed
