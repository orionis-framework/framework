# ruff: noqa: ARG002, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Retain the permission repository argument required by its contract.
"""Protect request ownership after asynchronous authorization waits."""

import asyncio
import inspect
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import AsyncMock

from orionis.auth.authorization.snapshot import EMPTY_SNAPSHOT
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import authentication_lock, bind_auth_context
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.manager import AuthManager
from orionis.auth.provider import AuthProvider
from orionis.auth.exceptions import AuthException
from orionis.container.context.manager import ScopeManager
from orionis.http.request import Request
from orionis.test import TestCase
from tests.auth.test_context import _Identity


class _PausedRepository:
    """Control permission completion and replacement without timed sleeps."""

    __slots__ = ("calls", "entered", "released", "replace")

    def __init__(self, *, replace: bool) -> None:
        """Configure whether the first successful lookup replaces its context.

        Parameters
        ----------
        replace : bool
            Schedule context replacement immediately before unlocking readers.

        Returns
        -------
        None
            No return value.
        """
        self.calls = 0
        self.entered = asyncio.Event()
        self.released = asyncio.Event()
        self.replace = replace

    async def loadFor(
        self,
        authorizable: object,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Wait until the test releases the first permission lookup.

        Parameters
        ----------
        authorizable : object
            Identity whose permissions are requested.

        Returns
        -------
        tuple[frozenset[str], frozenset[str]]
            One permission and no roles.
        """
        self.calls += 1
        if self.calls == 1:
            self.entered.set()
            await self.released.wait()
            if self.replace:
                asyncio.get_running_loop().call_soon(
                    bind_auth_context,
                    AuthenticationContext(),
                )
        return frozenset({"records.read"}), frozenset()


class _RecordingGuard:
    """Record session transitions without a database or credential service."""

    __slots__ = ("calls", "identity")
    name = "session"

    def __init__(self, identity: object) -> None:
        """Retain the accepted identity and an empty transition journal.

        Parameters
        ----------
        identity : object
            Identity returned by a successful controlled login.

        Returns
        -------
        None
            No return value.
        """
        self.identity = identity
        self.calls = []

    def login(self, request: object, identity: object) -> None:
        """Record a synchronous session transition.

        Parameters
        ----------
        request : object
            Request passed by the manager.
        identity : object
            Identity passed by the manager.

        Returns
        -------
        None
            No return value.
        """
        self.calls.append((request, identity))

    async def logout(self, request: object) -> None:
        """Record an asynchronous logout transition.

        Parameters
        ----------
        request : object
            Request passed by the manager.

        Returns
        -------
        None
            No return value.
        """
        self.calls.append(request)

    async def attempt(
        self,
        request: object,
        credentials: object,
        *,
        remember: bool,
    ) -> object:
        """Record credential processing and return the accepted identity.

        Parameters
        ----------
        request : object
            Request passed by the manager.
        credentials : object
            Credentials passed by the manager.
        remember : bool
            Remember preference passed by the manager.

        Returns
        -------
        object
            Identity accepted by the controlled guard.
        """
        self.calls.append((request, credentials, remember))
        return self.identity


class TestAuthContextRegressions(TestCase):
    """Reject cached and uncached results once their context is replaced."""

    async def testStaleContextForkCannotRevokeItsFormerCredential(self) -> None:
        """Drop the old credential when forking a closed or foreign context.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(
            identity=_Identity(7),
            guard="token",
            credential_id=19,
        )
        revoke = AsyncMock(return_value=True)
        manager = AuthManager(
            SimpleNamespace(config=lambda _: "session"),
            None,
            None,
            _RecordingGuard(_Identity(7)),
            SimpleNamespace(name="token"),
            SimpleNamespace(revoke=revoke),
        )
        async with ScopeManager():
            bind_auth_context(context)
            live = context._fork()
            self.assertEqual(live.credentialId, 19)
            self.assertIs(live.identity, context.identity)
            async with ScopeManager():
                foreign = context._fork()
        closed = context._fork()
        for label, fork in (("foreign", foreign), ("closed", closed)):
            with self.subTest(scope=label):
                async with ScopeManager():
                    bind_auth_context(fork)
                    self.assertIsNone(fork.identity)
                    self.assertFalse(await manager.revokeCurrentToken())
                    self.assertIsNone(fork.credentialId)
        revoke.assert_not_awaited()

    async def testWaitingReadersRecheckContextOwnership(self) -> None:
        """Deny stale readers after either successful or cancelled resolution.

        Returns
        -------
        None
            No return value.
        """
        for cached in (True, False):
            with self.subTest(cached=cached):
                repository = _PausedRepository(replace=cached)
                context = AuthenticationContext(
                    identity=_Identity(7),
                    repository=repository,
                )
                async with ScopeManager():
                    bind_auth_context(context)
                    first = asyncio.create_task(context.authorization())
                    second = None
                    try:
                        await repository.entered.wait()
                        second = asyncio.create_task(context.authorization())
                        # Yield one turn so the reader queues behind the lookup.
                        await asyncio.sleep(0)
                        self.assertFalse(second.done())
                        if cached:
                            repository.released.set()
                            first_snapshot, waiting_snapshot = await asyncio.gather(
                                first,
                                second,
                            )
                            self.assertTrue(first_snapshot.can("records.read"))
                        else:
                            bind_auth_context(AuthenticationContext())
                            first.cancel()
                            with self.assertRaises(asyncio.CancelledError):
                                await first
                            waiting_snapshot = await second
                        self.assertIs(waiting_snapshot, EMPTY_SNAPSHOT)
                        self.assertEqual(repository.calls, 1)
                        self.assertIsNone(context.identity)
                    finally:
                        tasks = [task for task in (first, second) if task is not None]
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)

    def testPublicRuntimeAnnotationsResolveWithoutCallerNamespaces(self) -> None:
        """Resolve native annotations used by reflection and dependency injection.

        Returns
        -------
        None
            No return value.
        """
        classes = (
            AuthenticationContext,
            IAuthenticationContext,
            AuthManager,
            IAuthManager,
            AuthProvider,
        )
        checked = 0
        for owner in classes:
            for name, declared in vars(owner).items():
                member = declared
                if name.startswith("_") and name != "__init__":
                    continue
                if isinstance(member, property):
                    member = member.fget
                elif isinstance(member, (classmethod, staticmethod)):
                    member = member.__func__
                if inspect.isfunction(member):
                    with self.subTest(owner=owner.__name__, member=name):
                        self.assertTrue(get_type_hints(member))
                        checked += 1
        self.assertGreater(checked, 50)

    async def testQueuedSessionTransitionsRejectAClosedRequest(self) -> None:
        """Reject queued transitions before touching a request whose scope ended.

        Returns
        -------
        None
            No return value.
        """
        for operation in ("login", "logout", "attempt"):
            with self.subTest(operation=operation):
                identity = _Identity(7)
                guard = _RecordingGuard(identity)
                app = SimpleNamespace(config=lambda _: "session")
                manager = AuthManager(
                    app,
                    None,
                    None,
                    guard,
                    SimpleNamespace(name="token"),
                    None,
                )
                task = None
                lock = None
                try:
                    async with ScopeManager() as scope:
                        scope[Request] = SimpleNamespace()
                        lock = authentication_lock()
                        await lock.acquire()
                        if operation == "login":
                            pending = manager.login(identity)
                        elif operation == "logout":
                            pending = manager.logout()
                        else:
                            pending = manager.attempt({})
                        task = asyncio.create_task(pending)
                        await asyncio.sleep(0)
                        self.assertFalse(task.done())
                    lock.release()
                    with self.assertRaises(AuthException):
                        await task
                    self.assertEqual(guard.calls, [])
                finally:
                    if lock is not None and lock.locked():
                        lock.release()
                    if task is not None:
                        if not task.done():
                            task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
