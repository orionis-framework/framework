# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify identity input bounds and public middleware runtime metadata."""

from inspect import iscoroutinefunction, isfunction
from typing import get_type_hints
from unittest.mock import patch

from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.exceptions import IdentityProviderException
from orionis.orm import Model
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.auth.middleware.authenticate import AuthenticateMiddleware
from orionis.auth.middleware.authorize import (
    RequirePermissionMiddleware,
    RequireRoleMiddleware,
)
from orionis.auth.middleware.guest import GuestMiddleware
from orionis.auth.middleware.policy import RequirePolicyMiddleware
from orionis.auth.middleware.resolve_identity import (
    ResolveIdentityMiddleware,
    ResolveSessionIdentityMiddleware,
)
from orionis.test import TestCase
from tests.auth import test_identity_and_session as fixtures


class _AbstractIdentity(Model, Authenticatable):
    """Declare a nonpersistable identity template for configuration rejection."""

    __abstract__ = True


class TestIdentityInputAndMetadata(TestCase):
    """Exercise input rejection and reflection on the concrete public APIs."""

    async def testOversizedIntegerIdentifiersCannotReachStorage(self) -> None:
        """Reject oversized integer keys before string conversion or database work.

        Returns
        -------
        None
            No return value.
        """
        provider = ModelIdentityProvider(fixtures.build_app(), object())
        with patch.object(
            fixtures.Account,
            "query",
            side_effect=AssertionError("Invalid identifiers must not reach storage"),
        ) as query:
            for identifier in (10**5000, -(10**5000), 10**255, "1" * 256):
                with self.subTest(kind=type(identifier).__name__):
                    self.assertIsNone(await provider.retrieveById(identifier))
            query.assert_not_called()

    def testConfiguredIdentityMustBeAConcreteOrmModel(self) -> None:
        """Reject the standalone concern and abstract templates as native models.

        Returns
        -------
        None
            No return value.
        """
        for path in (
            "orionis.auth.concerns.authenticatable.Authenticatable",
            f"{__name__}._AbstractIdentity",
        ):
            with self.subTest(path=path):
                provider = ModelIdentityProvider(
                    fixtures.build_app(identity={"model": path}),
                    object(),
                )
                with self.assertRaises(IdentityProviderException):
                    provider.model()

    async def testPublicIdentityAndMiddlewareAnnotationsResolve(self) -> None:
        """Resolve public annotations and preserve the optional asynchronous hook.

        Returns
        -------
        None
            No return value.
        """
        for cls in (
            IIdentityProvider,
            ModelIdentityProvider,
            ResolveIdentityMiddleware,
            ResolveSessionIdentityMiddleware,
            AuthenticateMiddleware,
            GuestMiddleware,
            RequirePermissionMiddleware,
            RequireRoleMiddleware,
            RequirePolicyMiddleware,
        ):
            for name, member in vars(cls).items():
                method = (
                    member.__func__
                    if isinstance(member, (classmethod, staticmethod))
                    else member
                )
                if isfunction(method) and name != "__annotate_func__":
                    with self.subTest(owner=cls.__name__, method=name):
                        self.assertTrue(get_type_hints(method))

        hook = IIdentityProvider.updateRememberToken
        self.assertTrue(iscoroutinefunction(hook))
        self.assertNotIn("updateRememberToken", IIdentityProvider.__abstractmethods__)
        provider = ModelIdentityProvider(fixtures.build_app(), object())
        identity = fixtures.Account({"id": 1, "active": True})
        with patch.object(
            fixtures.Account,
            "query",
            side_effect=AssertionError("The optional fallback must not access storage"),
        ) as query:
            for expected, token in ((None, "issued-token"), ("stored-token", None)):
                with self.subTest(operation="revoke" if token is None else "issue"):
                    self.assertIs(
                        await hook(provider, identity, expected, token),
                        expr2=False,
                    )
            query.assert_not_called()
