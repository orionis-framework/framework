from __future__ import annotations
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from orionis.database.connection_manager import ConnectionManager
from orionis.orm.resolver import ConnectionResolver
from orionis.session.contracts.session import ISession
from orionis.session.entities.record import SessionRecord
from orionis.session.manager import SessionManager
from orionis.session.session import Session
from orionis.session.stores.cache import CacheSessionStore
from orionis.session.stores.database import DatabaseSessionStore
from orionis.session.stores.file import FileSessionStore
from orionis.session.stores.memory import MemorySessionStore
from orionis.test import TestCase

# ruff: noqa: ANN401

class _FakeCacheRepository:
    """Minimal in-memory stand-in for ICacheRepository."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}

    async def get(self, key: str) -> Any:
        return self.data.get(key)

    async def set(self, key: str, value: Any, ttl: float | None = None) -> bool:  # noqa: ARG002
        self.data[key] = value
        return True

    async def delete(self, key: str) -> bool:
        return self.data.pop(key, None) is not None

class _FakeCacheManager:
    """Fake ICacheManager exposing only the store() factory method."""

    def __init__(self) -> None:
        self.repository = _FakeCacheRepository()

    def store(self, name: str | None = None) -> _FakeCacheRepository:
        self.requested_store = name
        return self.repository

class _StubDatabaseApp:
    """Application stub exposing an in-memory SQLite configuration."""

    def config(self, key: str) -> dict[str, Any]:  # noqa: ARG002
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": ":memory:",
                    "prefix": "",
                },
            },
        }

def _make_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Build a complete session configuration payload.

    Parameters
    ----------
    overrides : dict[str, Any] | None
        Entries replacing the defaults.

    Returns
    -------
    dict[str, Any]
        Configuration mapping accepted by the session entity.
    """
    config: dict[str, Any] = {
        "driver": "memory",
        "lifetime": 120,
        "expire_on_close": False,
        "files": "storage/framework/sessions",
        "connection": None,
        "table": "sessions",
        "cache": None,
        "cookie": "sessionid",
        "path": "/",
        "domain": None,
        "secure": False,
        "http_only": True,
        "same_site": "lax",
        "partitioned": False,
    }
    if overrides:
        config.update(overrides)
    return config

class _FakeRequest:
    """Request stub exposing only the cookie jar the manager reads."""

    def __init__(self, cookies: dict[str, str] | None = None) -> None:
        self.cookies: dict[str, str] = cookies if cookies is not None else {}

class _FakeResponse:
    """Response stub recording cookie mutations issued by the manager."""

    def __init__(self) -> None:
        self.set_calls: list[tuple[str, str, dict[str, Any]]] = []
        self.delete_calls: list[tuple[str, dict[str, Any]]] = []

    def setCookie(self, name: str, value: str, **options: Any) -> None:
        self.set_calls.append((name, value, options))

    def deleteCookie(self, name: str, **options: Any) -> None:
        self.delete_calls.append((name, options))

class _FakeApplication:
    """Application stub providing config, base path and instance binding."""

    def __init__(self, config: dict[str, Any], base_path: Path) -> None:
        self._config = config
        self.basePath = base_path
        self.bindings: list[tuple[Any, Any]] = []

    def config(self, key: str, default: Any = None) -> Any:
        return self._config if key == "session" else default

    def instance(self, abstract: Any, instance: Any, **_options: Any) -> bool:
        self.bindings.append((abstract, instance))
        return True

class _RecordingStore:
    """Store stub tracking every call made by the manager."""

    def __init__(self, record: SessionRecord | None = None) -> None:
        self.record = record
        self.written: list[SessionRecord] = []
        self.deleted: list[str] = []
        self.read_ids: list[str] = []

    async def read(self, session_id: str) -> SessionRecord | None:
        self.read_ids.append(session_id)
        return self.record

    async def write(self, record: SessionRecord) -> None:
        self.written.append(record)

    async def delete(self, session_id: str) -> None:
        self.deleted.append(session_id)

    async def gc(self) -> None:
        return

class TestSessionManager(TestCase):
    """Unit tests for the request-scoped SessionManager coordinator."""

    def setUp(self) -> None:
        """
        Create an isolated temporary base path before each test.

        Returns
        -------
        None
        """
        self._tmp = tempfile.TemporaryDirectory()
        self._base_path = Path(self._tmp.name)

    def tearDown(self) -> None:
        """
        Remove the temporary base path after each test.

        Returns
        -------
        None
        """
        self._tmp.cleanup()

    def _makeManager(
        self,
        overrides: dict[str, Any] | None = None,
        cache: _FakeCacheManager | None = None,
    ) -> tuple[SessionManager, _FakeApplication]:
        """
        Build a manager wired to stubbed collaborators.

        Parameters
        ----------
        overrides : dict[str, Any] | None
            Session configuration entries overriding the defaults.
        cache : _FakeCacheManager | None
            Cache manager used by the cache driver.

        Returns
        -------
        tuple[SessionManager, _FakeApplication]
            The manager under test and the application stub it uses.
        """
        config: dict[str, Any] = _make_config(overrides)
        app = _FakeApplication(config, self._base_path)
        manager = SessionManager(app, cache or _FakeCacheManager())
        return manager, app

    # ── Store resolution ─────────────────────────────────────────────────────

    def testMemoryDriverResolvesToMemoryStore(self) -> None:
        """
        Select the in-memory store for the memory driver.

        Validates the default driver never touches disk or the database.
        """
        manager, _ = self._makeManager()
        self.assertIsInstance(manager._store, MemorySessionStore)

    def testFileDriverResolvesToFileStore(self) -> None:
        """
        Select the filesystem store for the file driver.

        Validates that the configured directory is resolved relative to
        the application base path.
        """
        manager, _ = self._makeManager({"driver": "file", "files": "sessions"})
        self.assertIsInstance(manager._store, FileSessionStore)
        self.assertTrue((self._base_path / "sessions").is_dir())

    def testCacheDriverResolvesToCacheStore(self) -> None:
        """
        Select the cache-backed store for the cache driver.

        Validates that the configured store name is forwarded to the
        cache manager.
        """
        cache = _FakeCacheManager()
        manager, _ = self._makeManager({"driver": "cache", "cache": "redis"}, cache)
        self.assertIsInstance(manager._store, CacheSessionStore)
        self.assertEqual(cache.requested_store, "redis")

    # ── Cookie configuration ─────────────────────────────────────────────────

    def testCookieMaxAgeDerivesFromLifetime(self) -> None:
        """
        Convert the configured lifetime into cookie seconds.

        Validates that a 120-minute lifetime yields a 7200-second cookie.
        """
        manager, _ = self._makeManager({"lifetime": 120})
        self.assertEqual(manager._cookie_max_age, 7200)

    def testExpireOnCloseOmitsMaxAge(self) -> None:
        """
        Produce a browser-session cookie when expire_on_close is set.

        Validates that no Max-Age is emitted so the cookie dies with the
        browser session.
        """
        manager, _ = self._makeManager({"expire_on_close": True})
        self.assertIsNone(manager._cookie_max_age)

    def testSameSitePolicyIsStoredAsPlainValue(self) -> None:
        """
        Unwrap the SameSite enum into its header value.

        Validates that the cookie writer receives a plain string.
        """
        manager, _ = self._makeManager({"same_site": "strict"})
        self.assertEqual(manager._cookie_same_site, "strict")

    # ── start ────────────────────────────────────────────────────────────────

    async def testStartWithoutCookieReturnsLazySession(self) -> None:
        """
        Return a blank lazy session when no cookie is present.

        Validates that anonymous traffic never hits the backing store.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store

        session = await manager.start(_FakeRequest())

        self.assertFalse(session.started)
        self.assertIsNone(session.id)
        self.assertEqual(store.read_ids, [])

    async def testStartRestoresRecordFromStore(self) -> None:
        """
        Rebuild the session from the stored record.

        Validates that the identifier and payload survive a round trip.
        """
        manager, _ = self._makeManager()
        manager._store = _RecordingStore(
            SessionRecord(
                id="abc",
                data={"user_id": 7},
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        )

        session = await manager.start(_FakeRequest({"sessionid": "abc"}))

        self.assertEqual(session.id, "abc")
        self.assertEqual(session.get("user_id"), 7)
        self.assertTrue(session.started)
        self.assertFalse(session.isNew)

    async def testStartWithUnknownCookieReturnsLazySession(self) -> None:
        """
        Fall back to a blank session when the record is gone.

        Validates that an expired or forged cookie cannot resurrect data.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store

        session = await manager.start(_FakeRequest({"sessionid": "ghost"}))

        self.assertEqual(store.read_ids, ["ghost"])
        self.assertIsNone(session.id)
        self.assertFalse(session.started)

    async def testStartAgesFlashData(self) -> None:
        """
        Advance the flash lifecycle on restore.

        Validates that values flashed in the previous request are still
        readable exactly once.
        """
        manager, _ = self._makeManager()
        manager._store = _RecordingStore(
            SessionRecord(
                id="abc",
                data={"_flash_new": {"success": "Saved"}},
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        )

        session = await manager.start(_FakeRequest({"sessionid": "abc"}))

        self.assertEqual(session.getFlash("success"), "Saved")
        self.assertIn("_flash_old", session.all())

    async def testStartRegistersSessionUnderItsContract(self) -> None:
        """
        Bind the active session into the container.

        Validates that a single binding is issued, keyed by ISession, so
        globals and facades can resolve it.
        """
        manager, app = self._makeManager()
        manager._store = _RecordingStore()

        session = await manager.start(_FakeRequest())

        self.assertEqual(app.bindings, [(ISession, session)])

    # ── save ─────────────────────────────────────────────────────────────────

    async def testSaveIsNoOpForUnusedSession(self) -> None:
        """
        Skip persistence and cookies for untouched sessions.

        Validates that read-only traffic issues no Set-Cookie header.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store
        response = _FakeResponse()

        await manager.save(response, Session())

        self.assertEqual(store.written, [])
        self.assertEqual(response.set_calls, [])

    async def testSavePersistsDirtySessionAndSetsCookie(self) -> None:
        """
        Write the record and emit the cookie for a used session.

        Validates that the persisted payload matches the session data
        and the dirty flag is cleared afterwards.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store
        session = Session()
        session.put("user_id", 7)
        response = _FakeResponse()

        await manager.save(response, session)

        self.assertEqual(len(store.written), 1)
        self.assertEqual(store.written[0].data, {"user_id": 7})
        self.assertFalse(session.dirty)
        self.assertEqual(response.set_calls[0][0], "sessionid")
        self.assertEqual(response.set_calls[0][1], session.id)

    async def testSaveSkipsWriteWhenNotDirty(self) -> None:
        """
        Refresh the cookie without rewriting a clean record.

        Validates that idle requests do not hit the backing store.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store
        session = Session(id="abc", data={}, started=True, is_new=False)
        response = _FakeResponse()

        await manager.save(response, session)

        self.assertEqual(store.written, [])
        self.assertEqual(len(response.set_calls), 1)

    async def testSavePersistsExpiryFromConfiguredLifetime(self) -> None:
        """
        Stamp the record with the configured lifetime.

        Validates that expires_at lands within the expected window.
        """
        manager, _ = self._makeManager({"lifetime": 10})
        store = _RecordingStore()
        manager._store = store
        session = Session()
        session.put("a", 1)

        await manager.save(_FakeResponse(), session)

        delta = store.written[0].expires_at - datetime.now(UTC)
        self.assertGreater(delta.total_seconds(), 9 * 60)
        self.assertLessEqual(delta.total_seconds(), 10 * 60)

    async def testSaveRotatesIdentifierAndDropsOldRecord(self) -> None:
        """
        Swap the identifier when a regeneration was requested.

        Validates that the previous record is deleted and the cookie
        carries the new identifier.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store
        session = Session(id="old", data={}, started=True, is_new=False)
        session.regenerate()
        response = _FakeResponse()

        await manager.save(response, session)

        self.assertEqual(store.deleted, ["old"])
        self.assertNotEqual(session.id, "old")
        self.assertEqual(response.set_calls[0][1], session.id)

    async def testSaveInvalidatedSessionDeletesRecordAndCookie(self) -> None:
        """
        Purge the record and expire the cookie on invalidation.

        Validates that logout leaves no server-side or client-side trace.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store
        session = Session(id="abc", data={"a": 1}, started=True, is_new=False)
        session.invalidate()
        response = _FakeResponse()

        await manager.save(response, session)

        self.assertEqual(store.deleted, ["abc"])
        self.assertEqual(store.written, [])
        self.assertEqual(response.delete_calls[0][0], "sessionid")
        self.assertEqual(response.set_calls, [])

    async def testSaveInvalidatedSessionWithoutIdentifierSkipsStore(self) -> None:
        """
        Expire the cookie without touching the store when no ID exists.

        Validates that a session invalidated before it ever received an
        identifier issues no delete against the backing store.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store
        session = Session(started=True)
        session.invalidate()
        response = _FakeResponse()

        await manager.save(response, session)

        self.assertEqual(store.deleted, [])
        self.assertEqual(response.delete_calls[0][0], "sessionid")

    async def testSaveRotationWithoutPreviousIdentifierSkipsDelete(self) -> None:
        """
        Rotate without deleting when no previous record existed.

        Validates that the manager only removes a stale record when the
        session actually had an identifier.
        """
        manager, _ = self._makeManager()
        store = _RecordingStore()
        manager._store = store
        session = Session(started=True)
        session.regenerate()
        response = _FakeResponse()

        await manager.save(response, session)

        self.assertEqual(store.deleted, [])
        self.assertIsNotNone(session.id)
        self.assertEqual(response.set_calls[0][1], session.id)

    async def testSaveForwardsCookieAttributes(self) -> None:
        """
        Propagate every configured cookie attribute.

        Validates that security flags reach the outgoing response.
        """
        manager, _ = self._makeManager({
            "cookie": "orionis_session",
            "path": "/app",
            "domain": "example.com",
            "secure": True,
            "http_only": True,
            "same_site": "strict",
            "partitioned": True,
        })
        manager._store = _RecordingStore()
        session = Session()
        session.put("a", 1)
        response = _FakeResponse()

        await manager.save(response, session)

        name, _, options = response.set_calls[0]
        self.assertEqual(name, "orionis_session")
        self.assertEqual(options["path"], "/app")
        self.assertEqual(options["domain"], "example.com")
        self.assertTrue(options["secure"])
        self.assertTrue(options["http_only"])
        self.assertEqual(options["same_site"], "strict")
        self.assertTrue(options["partitioned"])

    async def testFullCycleRoundTripsThroughMemoryStore(self) -> None:
        """
        Persist and restore a session through the real memory store.

        Validates that start() and save() interoperate end to end.
        """
        manager, _ = self._makeManager()
        session = await manager.start(_FakeRequest())
        session.put("user_id", 42)
        await manager.save(_FakeResponse(), session)

        restored = await manager.start(_FakeRequest({"sessionid": session.id}))

        self.assertEqual(restored.get("user_id"), 42)
        self.assertFalse(restored.isNew)

class TestSessionManagerDatabaseDriver(TestCase):
    """Unit tests for the database-backed store resolution."""

    async def asyncSetUp(self) -> None:
        """
        Install an isolated in-memory connection manager.

        Returns
        -------
        None
        """
        self._connections = ConnectionManager(_StubDatabaseApp())
        self._previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self._connections)
        self._tmp = tempfile.TemporaryDirectory()
        self._base_path = Path(self._tmp.name)

    async def asyncTearDown(self) -> None:
        """
        Restore the previously installed connection manager.

        Returns
        -------
        None
        """
        await self._connections.disconnect()
        ConnectionResolver._manager = self._previous_manager
        self._tmp.cleanup()

    def _makeManager(self, overrides: dict[str, Any]) -> SessionManager:
        """
        Build a manager backed by the in-memory SQLite connection.

        Parameters
        ----------
        overrides : dict[str, Any]
            Session configuration entries overriding the defaults.

        Returns
        -------
        SessionManager
            The manager under test.
        """
        app = _FakeApplication(_make_config(overrides), self._base_path)
        return SessionManager(app, _FakeCacheManager())

    def testDatabaseDriverResolvesToDatabaseStore(self) -> None:
        """
        Select the database store for the database driver.

        Validates that the connection is resolved through the ORM
        resolver and that the configured table name is honoured.
        """
        manager = self._makeManager({
            "driver": "database",
            "connection": "sqlite",
            "table": "user_sessions",
        })
        self.assertIsInstance(manager._store, DatabaseSessionStore)
        self.assertEqual(manager._store._table, "user_sessions")

    def testDatabaseDriverFallsBackToDefaultTable(self) -> None:
        """
        Use the built-in table name when the configuration omits one.

        Validates the ``sessions`` default applied by the manager.
        """
        manager = self._makeManager({
            "driver": "database",
            "connection": "sqlite",
            "table": None,
        })
        self.assertEqual(manager._store._table, "sessions")

