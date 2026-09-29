from __future__ import annotations
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from orionis.foundation.config.session.entities.session import Session as SessionConfig
from orionis.session.entities.record import SessionRecord
from orionis.session.manager import SessionManager
from orionis.session.stores.memory import MemorySessionStore
from orionis.test import TestCase
from tests.session.test_manager import (
    _FakeApplication,
    _FakeRequest,
    _FakeResponse,
    _make_config,
    _RecordingStore,
)

_NOW = datetime(2030, 1, 1, tzinfo=UTC)
_LIFETIME = timedelta(minutes=120)

def make_manager(
    *,
    data: dict[str, object] | None = None,
    **overrides: object,
) -> tuple[SessionManager, _RecordingStore]:
    """Build a manager with a record last renewed ten seconds before the clock.

    Parameters
    ----------
    data : dict[str, object] or None, optional
        Persisted values, or a scalar identity payload when omitted.
    **overrides : object
        Configuration values replacing the sixty-second renewal interval.

    Returns
    -------
    tuple[SessionManager, _RecordingStore]
        Manager and store used to count renewal writes.
    """
    config = _make_config({"renewal_interval": 60, **overrides})
    manager = SessionManager(_FakeApplication(config, Path()), None)
    store = _RecordingStore(
        SessionRecord(
            id="current",
            data=data if data is not None else {"user_id": 42},
            expires_at=_NOW + _LIFETIME - timedelta(seconds=10),
        ),
    )
    manager._store = store
    return manager, store

class TestSessionRenewal(TestCase):
    """Exercise persistence, cookie and revocation rules with renewal intervals."""

    def testConfigurationPreservesDefaultsAndRejectsInvalidIntervals(self) -> None:
        """Validate explicit types and interval bounds without changing defaults.

        Returns
        -------
        None
            Default behavior and exclusive lifetime bounds are checked.
        """
        config = SessionConfig()
        self.assertTrue(config.track_previous_url)
        self.assertEqual(config.renewal_interval, 0)
        self.assertEqual(
            SessionConfig(lifetime=2, renewal_interval=119).renewal_interval, 119,
        )
        for value in (True, False, 1.5, "30", None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                SessionConfig(renewal_interval=value)
        for value in (-1, 120, 121):
            with self.subTest(value=value), self.assertRaises(ValueError):
                SessionConfig(lifetime=2, renewal_interval=value)
        for value in (0, 1, "false", None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                SessionConfig(track_previous_url=value)

    async def testCleanSessionsKeepExistingExpiryUntilRenewalIsDue(self) -> None:
        """Read each request but omit writes and cookies within the interval.

        Returns
        -------
        None
            Store reads remain independent and response headers remain untouched.
        """
        manager, store = make_manager()
        with patch("orionis.session.manager.datetime") as clock:
            clock.now.return_value = _NOW
            for _ in range(2):
                session = await manager.start(_FakeRequest({"sessionid": "current"}))
                response = _FakeResponse()
                await manager.save(response, session)
                self.assertEqual(response.set_calls, [])
        self.assertEqual(store.read_ids, ["current", "current"])
        self.assertEqual(store.written, [])

    async def testDeadlineIsCheckedWhenTheResponseIsReady(self) -> None:
        """Renew a request that crosses the deadline after restoring its session.

        Returns
        -------
        None
            Server expiration and browser Max-Age are refreshed together.
        """
        manager, store = make_manager()
        with patch("orionis.session.manager.datetime") as clock:
            clock.now.return_value = _NOW
            session = await manager.start(_FakeRequest({"sessionid": "current"}))
            clock.now.return_value = _NOW + timedelta(seconds=50)
            response = _FakeResponse()
            await manager.save(response, session)
            self.assertEqual(len(store.written), 1)
            self.assertEqual(
                store.written[0].expires_at, clock.now.return_value + _LIFETIME,
            )
            self.assertEqual(response.set_calls[0][2]["max_age"], 7200)
            await manager.save(_FakeResponse(), session)
            self.assertEqual(len(store.written), 1)

    async def testZeroIntervalRenewsCleanSessionsOnEverySave(self) -> None:
        """Preserve unconditional renewal when the configured interval is zero.

        Returns
        -------
        None
            Clean restored sessions still issue a write and Set-Cookie header.
        """
        manager, store = make_manager(renewal_interval=0)
        with patch("orionis.session.manager.datetime") as clock:
            clock.now.return_value = _NOW
            session = await manager.start(_FakeRequest({"sessionid": "current"}))
            response = _FakeResponse()
            await manager.save(response, session)
        self.assertEqual(len(store.written), 1)
        self.assertEqual(len(response.set_calls), 1)

    async def testDirtyFlashNewAndRotatedSessionsAlwaysPersist(self) -> None:
        """Save state transitions even before a clean session's renewal deadline.

        Returns
        -------
        None
            Every state transition writes once and produces a session cookie.
        """
        for operation in ("put", "flash", "new", "rotate"):
            with self.subTest(operation=operation):
                manager, store = make_manager()
                with patch("orionis.session.manager.datetime") as clock:
                    clock.now.return_value = _NOW
                    request = _FakeRequest(
                        {} if operation == "new" else {"sessionid": "current"},
                    )
                    session = await manager.start(request)
                    if operation == "rotate":
                        session.regenerate()
                    elif operation == "flash":
                        session.flash("message", "saved")
                    else:
                        session.put("name", "updated")
                    response = _FakeResponse()
                    await manager.save(response, session)
                self.assertEqual(len(store.written), 1)
                self.assertEqual(len(response.set_calls), 1)
                self.assertFalse(session.dirty)
                if operation == "rotate":
                    self.assertEqual(store.deleted, ["current"])
                    self.assertNotEqual(session.id, "current")

    async def testFlashAgingPersistsBeforeTheRenewalDeadline(self) -> None:
        """Persist flash aging even when the handler does not change session data.

        Returns
        -------
        None
            New flash becomes old and a subsequent request removes it.
        """
        for payload in ({"_flash_new": {"message": "saved"}}, {"_flash_old": {"x": 1}}):
            manager, store = make_manager(data=payload)
            with patch("orionis.session.manager.datetime") as clock:
                clock.now.return_value = _NOW
                session = await manager.start(_FakeRequest({"sessionid": "current"}))
                await manager.save(_FakeResponse(), session)
            self.assertEqual(len(store.written), 1)

    async def testNestedMutableValuesArePersistedConservatively(self) -> None:
        """Retain changes made through references without marking the session dirty.

        Returns
        -------
        None
            Nested values are never eligible for skipped persistence.
        """
        for value in (["book"], {"cart": ["book"]}, (["book"],)):
            manager, store = make_manager(data={"cart": value})
            with patch("orionis.session.manager.datetime") as clock:
                clock.now.return_value = _NOW
                session = await manager.start(_FakeRequest({"sessionid": "current"}))
                payload = session.get("cart")
                if isinstance(payload, dict):
                    payload["cart"].append("pen")
                elif isinstance(payload, tuple):
                    payload[0].append("pen")
                else:
                    payload.append("pen")
                self.assertFalse(session.dirty)
                await manager.save(_FakeResponse(), session)
            self.assertEqual(len(store.written), 1)
            self.assertEqual(store.written[0].data["cart"], payload)

    async def testBrowserSessionCookiesStillOmitMaxAge(self) -> None:
        """Renew server expiry without adding Max-Age to an expire-on-close cookie.

        Returns
        -------
        None
            The interval does not convert browser session cookies to persistent ones.
        """
        manager, store = make_manager(expire_on_close=True)
        with patch("orionis.session.manager.datetime") as clock:
            clock.now.return_value = _NOW + timedelta(seconds=50)
            session = await manager.start(_FakeRequest({"sessionid": "current"}))
            response = _FakeResponse()
            await manager.save(response, session)
        self.assertEqual(len(store.written), 1)
        self.assertIsNone(response.set_calls[0][2]["max_age"])

    async def testRevocationWinsOverSkippedRenewalAndLaterWrites(self) -> None:
        """Keep logout final while clean requests skip renewal and stale writes fail.

        Returns
        -------
        None
            A revoked session cannot be recreated by clean, dirty or rotating requests.
        """
        manager, records = make_manager()
        store = MemorySessionStore()
        manager._store = store
        await store.write(records.record)
        with patch("orionis.session.manager.datetime") as clock:
            clock.now.return_value = _NOW
            requests = [
                await manager.start(_FakeRequest({"sessionid": "current"}))
                for _ in range(4)
            ]
            logout, clean, dirty, rotating = requests
            logout.invalidate()
            await manager.save(_FakeResponse(), logout)
            dirty.put("later", True)
            rotating.regenerate()
            for stale in (clean, dirty, rotating):
                response = _FakeResponse()
                await manager.save(response, stale)
                self.assertEqual(response.set_calls, [])
            restored = await manager.start(_FakeRequest({"sessionid": "current"}))
        self.assertFalse(restored.started)
        self.assertIsNone(await store.read("current"))
