# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve authorization metadata, failure identity and cache ownership."""

import gc
import inspect
import weakref
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING, get_type_hints
from unittest.mock import AsyncMock, MagicMock, patch

from orionis.auth.authorization.authorizer import Authorizer
from orionis.auth.authorization.policy import Policy
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.auth.authorization.registry import PolicyRegistry
from orionis.auth.authorization.repository import DatabasePermissionRepository
from orionis.auth.authorization.snapshot import AuthorizationSnapshot
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.concerns.functions import authorizable_key
from orionis.auth.contracts.authenticatable import IAuthenticatable
from orionis.auth.contracts.authorizable import IAuthorizable
from orionis.auth.contracts.authorizer import IAuthorizer
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.contracts.policy import IPolicy
from orionis.auth.contracts.snapshot import IAuthorizationSnapshot
from orionis.auth.exceptions import AuthException
from orionis.database.exceptions import QueryException
from orionis.test import TestCase


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _Owner(Authorizable):
    """Expose a declared type and an arbitrary scalar owner key."""

    __slots__ = ("id",)
    AUTHORIZABLE_TYPE = "tests.AuthorizationOwner"

    def __init__(self, identifier: int) -> None:
        """Store a scalar key without converting it to text.

        Parameters
        ----------
        identifier : int
            Key supplied to the authorization boundary.

        Returns
        -------
        None
            No return value.
        """
        self.id = identifier


class _Resource:
    """Represent a persistent resource type with transient subclasses."""

    __slots__ = ()


class TestAuthorizationRegressions(TestCase):
    """Exercise public authorization boundaries without external storage."""

    def testPublicAnnotationsResolveAtRuntime(self) -> None:
        """Resolve every owned contract and implementation method annotation.

        Returns
        -------
        None
            No return value.
        """
        classes = (
            IAuthenticatable,
            IAuthorizable,
            IAuthorizer,
            IPermissionRepository,
            IPolicy,
            IAuthorizationSnapshot,
            Authenticatable,
            Authorizable,
            Authorizer,
            PermissionRegistrar,
            DatabasePermissionRepository,
            AuthorizationSnapshot,
            PolicyRegistry,
            Policy,
        )
        for target in classes:
            for name, descriptor in vars(target).items():
                if name.startswith("_") and name != "__init__":
                    continue
                method = (
                    descriptor.fget if isinstance(descriptor, property) else descriptor
                )
                if inspect.isfunction(method):
                    with self.subTest(target=target.__name__, method=name):
                        self.assertIn("return", get_type_hints(method))

    async def testHugeOwnerKeysFailBeforeDatabaseAccess(self) -> None:
        """Reject oversized integers through the documented authorization paths.

        Returns
        -------
        None
            No return value.
        """
        database = MagicMock()
        repository = DatabasePermissionRepository(database)
        for label, identifier in (
            ("positive", 1 << 20000),
            ("negative", -(1 << 20000)),
        ):
            for surface in ("key", "repository"):
                with self.subTest(sign=label, surface=surface):
                    owner = _Owner(identifier)
                    if surface == "key":
                        with self.assertRaises(AuthException):
                            authorizable_key(owner)
                    else:
                        self.assertEqual(
                            await repository.loadFor(owner),
                            (frozenset(), frozenset()),
                        )
        database.table.assert_not_called()
        for identifier in (10**254, -(10**253)):
            self.assertEqual(authorizable_key(_Owner(identifier))[1], str(identifier))
        for identifier in (10**255, -(10**254)):
            with self.assertRaises(AuthException):
                authorizable_key(_Owner(identifier))

    def testLookupsDoNotRetainUnregisteredResourceClasses(self) -> None:
        """Release transient classes after both inherited hits and cached misses.

        Returns
        -------
        None
            No return value.
        """
        registry = PolicyRegistry()
        registry.register(_Resource, Policy)

        def lookup(
            base: type,
            expected: type[Policy] | None,
        ) -> weakref.ReferenceType[type]:
            """Resolve one ephemeral resource and retain only its weak reference.

            Parameters
            ----------
            base : type
                Parent controlling whether a registered policy is inherited.
            expected : type of Policy or None
                Policy expected for the transient resource.

            Returns
            -------
            weakref.ReferenceType[type]
                Reference that must not keep the resource class alive.
            """
            resource = type("TransientResource", (base,), {})
            self.assertIs(registry.policyFor(resource), expected)
            self.assertIs(registry.policyFor(resource), expected)
            return weakref.ref(resource)

        for base, expected in ((_Resource, Policy), (object, None)):
            with self.subTest(inherited=expected is not None):
                reference = lookup(base, expected)
                gc.collect()
                self.assertIsNone(reference())
        self.assertEqual(registry.bindings(), {_Resource: Policy})

    async def testRecoveryPreservesTheOriginalWriteFailure(self) -> None:
        """Observe failed recovery reads without replacing the failed write.

        Returns
        -------
        None
            No return value.
        """
        for operation in ("create", "attach"):
            with self.subTest(operation=operation):
                original = QueryException("The controlled authorization write failed.")
                cause = OSError("The controlled storage cause.")
                original.__cause__ = cause
                secondary = QueryException("The controlled recovery read failed.")
                settled = []

                @asynccontextmanager
                async def transaction(
                    _settled: list[str] = settled,
                ) -> AsyncIterator[None]:
                    """Settle the write before attempting the recovery query.

                    Parameters
                    ----------
                    _settled : list[str]
                        Journal belonging to this controlled transaction.

                    Yields
                    ------
                    None
                        Control while the write transaction is active.
                    """
                    try:
                        yield
                    finally:
                        _settled.append("settled")

                query = MagicMock()
                query.where.return_value = query
                query.first = AsyncMock(
                    side_effect=[None, secondary]
                    if operation == "create"
                    else [{"id": 7}],
                )
                query.insert = AsyncMock(side_effect=original)
                query.exists = AsyncMock(side_effect=secondary)
                database = SimpleNamespace(
                    table=MagicMock(return_value=query),
                    transaction=transaction,
                )
                registrar = PermissionRegistrar(database)
                with (
                    patch(
                        "orionis.failure.runtime.capture",
                        new_callable=AsyncMock,
                    ) as capture,
                    self.assertRaises(QueryException) as raised,
                ):
                    if operation == "create":
                        await registrar.createPermission("posts.read")
                    else:
                        await registrar.givePermissionTo(_Owner(1), "posts.read")
                self.assertIs(raised.exception, original)
                self.assertIs(raised.exception.__cause__, cause)
                self.assertEqual(settled, ["settled"])
                capture.assert_awaited_once()
                self.assertIs(capture.await_args.args[0], secondary)
                self.assertEqual(capture.await_args.kwargs["phase"], "recovery")
