# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve credential validity, connection ownership, and returned account state."""

import importlib
import inspect
from typing import TYPE_CHECKING, get_type_hints
from unittest.mock import AsyncMock, patch
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.guards.session_guard import SessionGuard
from orionis.auth.guards.token_guard import TokenGuard
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.auth.passwords.broker import PasswordBroker
from orionis.auth.remember import RememberMe
from orionis.database.exceptions import QueryException
from orionis.orm.query.raw_builder import RawQueryBuilder
from tests.auth.test_remember import request, queued_cookie
from orionis.auth.passwords.schema import build_password_reset_table
from orionis.database.connection_manager import ConnectionManager
from orionis.hashing.hash_manager import HashManager
from orionis.orm import BigInteger, Boolean, Model, String
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.session.session import Session
from orionis.test import TestCase
from tests.auth.test_identity_and_session import build_app, fake_request
from tests.auth.test_tokens import _TokenCase, bearer_request


if TYPE_CHECKING:
    from types import ModuleType
    from orionis.auth.contracts.authorizable import IAuthorizable
    from orionis.auth.tokens.repository import AccessTokenRepository


def _annotation_subjects(module: ModuleType) -> list[object]:
    """Collect declared types and callables whose annotations must resolve.

    Parameters
    ----------
    module : types.ModuleType
        Reviewed module exposing its own classes and functions.

    Returns
    -------
    list of object
        Declared classes, functions, and descriptor functions.
    """
    subjects = []
    for value in vars(module).values():
        if getattr(value, "__module__", None) != module.__name__:
            continue
        if inspect.isfunction(value):
            subjects.append(value)
        elif inspect.isclass(value):
            subjects.append(value)
            for member in vars(value).values():
                function = _descriptor_function(member)
                if inspect.isfunction(function):
                    subjects.append(function)
    return subjects


def _descriptor_function(member: object) -> object:
    """Unwrap class, static, and property descriptors for annotation inspection.

    Parameters
    ----------
    member : object
        Value declared in a reviewed class namespace.

    Returns
    -------
    object
        Underlying function or the original non-descriptor value.
    """
    if isinstance(member, (classmethod, staticmethod)):
        return member.__func__
    if isinstance(member, property):
        return member.fget
    return member


class _AuthAccount(Model, Authenticatable, Authorizable):
    """Expose account status and persistent credentials on a real SQLite model."""

    table = "auth_guard_accounts"
    timestamps = False
    id = BigInteger().primary().autoIncrement()
    email = String(255)
    password = String(255)
    active = Boolean().nullable()
    remember_token = String(100).nullable()


class _FallbackProvider(ModelIdentityProvider):
    """Keep native identity lookup while selecting the token guard fallback."""

    __slots__ = ()


class TestGuardRegressions(_TokenCase):
    """Exercise account and credential transitions through their real services."""

    async def asyncSetUp(self) -> None:
        """Create the identity schema alongside the isolated token store.

        Returns
        -------
        None
            No return value.
        """
        await super().asyncSetUp()
        await self.connection.createTable(_AuthAccount.__meta__.table)
        await self.connection.createTable(
            build_password_reset_table("password_reset_tokens"),
        )
        self.auth_app = build_app(identity={"model": f"{__name__}._AuthAccount"})
        self.provider = ModelIdentityProvider(self.auth_app, None)
        self.user = await _AuthAccount.create(
            {
                "email": "original@example.test",
                "password": "synthetic-stored-hash",
                "active": True,
                "remember_token": "synthetic-previous-grant",
            },
        )

    async def testSessionRejectsAccountsDisabledAfterLogin(self) -> None:
        """Retire sessions when the account's explicit status becomes invalid.

        Returns
        -------
        None
            No return value.
        """
        guard = SessionGuard(self.auth_app, self.provider)
        for status in (False, None):
            with self.subTest(status=status):
                await (
                    self.db.table(_AuthAccount.table)
                    .where("id", self.user.id)
                    .update(
                        {"active": status},
                    )
                )
                incoming = fake_request(Session())
                guard.login(incoming, self.user)
                self.assertIsNone(await guard.resolve(incoming))
                self.assertIsNone(incoming.state.session.get("_auth_identifier"))

    async def testMalformedSessionFingerprintsFailClosed(self) -> None:
        """Reject non-ASCII session fingerprints without raising comparison errors.

        Returns
        -------
        None
            No return value.
        """
        guard = SessionGuard(self.auth_app, self.provider)
        for index, fingerprint in enumerate(("é" * 64, "\ud800")):
            with self.subTest(case=index):
                incoming = fake_request(Session())
                guard.login(incoming, self.user)
                incoming.state.session.put("_auth_identifier_password", fingerprint)
                self.assertIsNone(await guard.resolve(incoming))
                self.assertIsNone(incoming.state.session.get("_auth_identifier"))

    async def testTokenPathsRejectExplicitInactiveStatusBeforeTouch(self) -> None:
        """Deny inactive owners before updating token usage in both lookup paths.

        Returns
        -------
        None
            No return value.
        """
        issued = await self.repository.create(self.user, "status")
        for provider_type in (ModelIdentityProvider, _FallbackProvider):
            guard = TokenGuard(
                self.repository,
                provider_type(self.auth_app, None),
            )
            for status in (False, None):
                with self.subTest(provider=provider_type.__name__, status=status):
                    await (
                        self.db.table(_AuthAccount.table)
                        .where(
                            "id",
                            self.user.id,
                        )
                        .update({"active": status})
                    )
                    await (
                        self.db.table("personal_access_tokens")
                        .where(
                            "id",
                            issued.access_token.id,
                        )
                        .update({"last_used_at": None})
                    )
                    self.assertIsNone(
                        await guard.resolve(bearer_request(issued.plain_text)),
                    )
                    row = (
                        await self.db.table("personal_access_tokens")
                        .where(
                            "id",
                            issued.access_token.id,
                        )
                        .first()
                    )
                    self.assertIsNone(row["last_used_at"])

    async def testCombinedHydrationRetainsTheConnectionBeforeRetrievedEvents(
        self,
    ) -> None:
        """Persist retrieved identities on the exact connection used by the join.

        Returns
        -------
        None
            No return value.
        """
        other_manager = ConnectionManager(build_app())
        self.addAsyncCleanup(other_manager.disconnect)
        other_connection = other_manager.connection()
        await other_connection.createTable(_AuthAccount.__meta__.table)
        other_db = QueryBuilder(other_manager)
        await other_db.table(_AuthAccount.table).insert(
            {
                "id": self.user.id,
                "email": "other@example.test",
                "password": "synthetic-stored-hash",
                "active": True,
            },
        )
        issued = await self.repository.create(self.user, "connection")
        original = ModelQueryBuilder._fireRetrieved

        async def persist(query: ModelQueryBuilder, models: list[_AuthAccount]) -> None:
            """Switch the resolver before saving the newly hydrated identity.

            Parameters
            ----------
            query : ModelQueryBuilder
                Query dispatching its retrieved callbacks.
            models : list of _AuthAccount
                Identities produced by the combined lookup.

            Returns
            -------
            None
                No return value.
            """
            ConnectionResolver.setManager(other_manager)
            for model in models:
                model.email = "retained@example.test"
                await model.save()
            await original(query, models)

        try:
            with patch.object(ModelQueryBuilder, "_fireRetrieved", persist):
                result = await TokenGuard(self.repository, self.provider).resolve(
                    bearer_request(issued.plain_text),
                )
        finally:
            ConnectionResolver.setManager(self.manager)
        self.assertIsNotNone(result)
        original_row = (
            await self.db.table(_AuthAccount.table)
            .where(
                "id",
                self.user.id,
            )
            .first()
        )
        other_row = (
            await other_db.table(_AuthAccount.table)
            .where(
                "id",
                self.user.id,
            )
            .first()
        )
        self.assertEqual(original_row["email"], "retained@example.test")
        self.assertEqual(other_row["email"], "other@example.test")

    async def testPasswordResetReturnsTheCommittedAccountState(self) -> None:
        """Return the new hash and cleared remember token without dirty attributes.

        Returns
        -------
        None
            No return value.
        """
        broker = PasswordBroker(self.auth_app, self.db, HashManager(self.auth_app))
        issued = await broker.issue(self.user.email)
        result = await broker.reset(self.user.email, issued[1], "ReplacementPassword1!")
        row = await self.db.table(_AuthAccount.table).where("id", self.user.id).first()
        self.assertIsNotNone(result)
        with self.subTest(field="password"):
            self.assertEqual(result.getAuthPassword(), row["password"])
        with self.subTest(field="remember_token"):
            self.assertIsNone(result.remember_token)
        with self.subTest(field="state"):
            self.assertFalse(result.isDirty())

    async def testResetRollsBackWhenItsUpdatedIdentityDisappears(self) -> None:
        """Restore the credential and account if the post-update read cannot find it.

        Returns
        -------
        None
            No return value.
        """
        broker = PasswordBroker(self.auth_app, self.db, HashManager(self.auth_app))
        issued = await broker.issue(self.user.email)
        original = type(broker.tokens).revokeAll

        async def remove_then_revoke(
            repository: AccessTokenRepository,
            identity: IAuthorizable,
        ) -> int:
            """Remove the account inside the same transaction before token revocation.

            Parameters
            ----------
            repository : AccessTokenRepository
                Repository performing the normal revocation.
            identity : IAuthorizable
                Identity whose transaction must fail atomically.

            Returns
            -------
            int
                Number of personal credentials revoked by the real repository.
            """
            await self.db.table(_AuthAccount.table).where("id", self.user.id).delete()
            return await original(repository, identity)

        with patch.object(type(broker.tokens), "revokeAll", remove_then_revoke):
            self.assertIsNone(
                await broker.reset(self.user.email, issued[1], "ReplacementPassword1!"),
            )
        restored = (
            await self.db.table(_AuthAccount.table).where("id", self.user.id).first()
        )
        self.assertEqual(restored["password"], self.user.password)
        self.assertTrue(await broker.valid(self.user.email, issued[1]))

    async def testBrokerKeepsItsInjectedConnectionAcrossResolverChanges(self) -> None:
        """Read and mutate the account only in the reset store's transaction.

        Returns
        -------
        None
            No return value.
        """
        other_manager = ConnectionManager(build_app())
        self.addAsyncCleanup(other_manager.disconnect)
        other_connection = other_manager.connection()
        await other_connection.createTable(_AuthAccount.__meta__.table)
        other_db = QueryBuilder(other_manager)
        await other_db.table(_AuthAccount.table).insert(
            {
                "id": self.user.id,
                "email": self.user.email,
                "password": "other-stored-hash",
                "active": True,
            },
        )
        broker = PasswordBroker(self.auth_app, self.db, HashManager(self.auth_app))
        ConnectionResolver.setManager(other_manager)
        try:
            issued = await broker.issue(self.user.email)
            with self.subTest(stage="issuance"):
                self.assertEqual(issued[0].password, self.user.password)
                self.assertIs(issued[0]._read_connection, self.connection)
            result = await broker.reset(
                self.user.email,
                issued[1],
                "ReplacementPassword1!",
            )
            original_row = (
                await self.db.table(_AuthAccount.table)
                .where("id", self.user.id)
                .first()
            )
            other_row = (
                await other_db.table(_AuthAccount.table)
                .where("id", self.user.id)
                .first()
            )
            with self.subTest(stage="reset"):
                self.assertIsNotNone(result)
                self.assertNotEqual(original_row["password"], self.user.password)
                self.assertEqual(other_row["password"], "other-stored-hash")
                self.assertIs(result._read_connection, self.connection)
        finally:
            ConnectionResolver.setManager(self.manager)

    async def testMalformedStoredFingerprintsFailClosed(self) -> None:
        """Reject persisted non-ASCII fingerprints in recovery and remembered login.

        Returns
        -------
        None
            No return value.
        """
        broker = PasswordBroker(self.auth_app, self.db, HashManager(self.auth_app))
        issued = await broker.issue(self.user.email)
        await self.db.table("password_reset_tokens").update(
            {"password_fingerprint": "é" * 64},
        )
        with self.subTest(kind="reset"):
            self.assertFalse(await broker.valid(self.user.email, issued[1]))
        remember = RememberMe(self.auth_app, self.provider)
        incoming = request()
        await remember.issue(incoming, self.user)
        cookie = queued_cookie(incoming)
        for fingerprint in ("é" * 64, "\ud800"):
            with self.subTest(kind="remember", fingerprint=ascii(fingerprint)):
                self.user.remember_token = fingerprint
                with patch.object(
                    type(self.provider),
                    "retrieveById",
                    AsyncMock(return_value=self.user),
                ):
                    self.assertIsNone(await remember.restore(request(cookie)))

    async def testTokenGuardRejectsOversizedCustomOwnerKeys(self) -> None:
        """Reject malformed provider keys before conversion or token usage writes.

        Returns
        -------
        None
            No return value.
        """
        issued = await self.repository.create(self.identity, "custom-owner")
        self.identity.identifier = 10**5000
        provider = _FallbackProvider(self.auth_app, None)
        with patch.object(
            type(provider),
            "retrieveById",
            AsyncMock(return_value=self.identity),
        ):
            self.assertIsNone(
                await TokenGuard(self.repository, provider).resolve(
                    bearer_request(issued.plain_text),
                ),
            )
        record = await self.repository.findByPlainText(issued.plain_text)
        self.assertIsNone(record.last_used_at)

    async def testIssuePreservesWriteFailureWhenRecoveryLookupFails(self) -> None:
        """Propagate the original write failure and report the failed recovery once.

        Returns
        -------
        None
            No return value.
        """
        broker = PasswordBroker(self.auth_app, self.db, HashManager(self.auth_app))
        primary = QueryException("synthetic insert failure")
        secondary = QueryException("synthetic recovery failure")
        with (
            patch.object(RawQueryBuilder, "insert", AsyncMock(side_effect=primary)),
            patch.object(RawQueryBuilder, "exists", AsyncMock(side_effect=secondary)),
            patch("orionis.failure.runtime.capture", new_callable=AsyncMock) as capture,
            self.assertRaises(QueryException) as raised,
        ):
            await broker.issue(self.user.email)
        self.assertIs(raised.exception, primary)
        capture.assert_awaited_once_with(
            secondary,
            flow="auth",
            phase="recovery",
            operation="password.create",
        )


class TestAuthRuntimeAnnotations(TestCase):
    """Resolve the public and internal annotations of the reviewed auth surfaces."""

    def testAnnotationsResolveWithoutCallerNamespaces(self) -> None:
        """Evaluate annotations without supplying missing imports from the caller.

        Returns
        -------
        None
            No return value.
        """
        names = (
            "tokens",
            "tokens.functions",
            "tokens.lookup",
            "tokens.repository",
            "tokens.schema",
            "passwords",
            "passwords.broker",
            "passwords.schema",
            "guards",
            "guards.session_guard",
            "guards.token_guard",
            "remember",
            "entities",
            "entities.access_token",
            "entities.guard_result",
            "entities.new_access_token",
            "contracts.guard",
            "contracts.session_guard",
            "contracts.token_repository",
        )
        for name in names:
            module = importlib.import_module("orionis.auth." + name)
            for subject in _annotation_subjects(module):
                with self.subTest(module=name, subject=subject.__qualname__):
                    get_type_hints(subject)
