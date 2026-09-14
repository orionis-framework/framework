from orionis.auth.authorization.authorizer import Authorizer
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.auth.authorization.repository import DatabasePermissionRepository
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.contracts.authorizer import IAuthorizer
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.contracts.session_guard import ISessionGuard
from orionis.auth.contracts.token_repository import IAccessTokenRepository
from orionis.auth.guards.session_guard import SessionGuard
from orionis.auth.guards.token_guard import TokenGuard
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.auth.manager import AuthManager
from orionis.auth.provider import AuthProvider
from orionis.auth.tokens.repository import AccessTokenRepository
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.container.context.manager import ScopeManager
from orionis.foundation.application import Application
from orionis.foundation.core_providers import CORE_PROVIDERS
from orionis.support.facades.auth import Auth as AuthFacade
from orionis.test import TestCase

class _RecordingApp:
    """Application double recording every container registration."""

    __slots__ = ("scopeds", "singletons")

    def __init__(self) -> None:
        """Start with an empty registration journal."""
        self.singletons: list[tuple[type, type]] = []
        self.scopeds: list[tuple[type, type]] = []

    def scoped(self, abstract: type, concrete: type) -> bool:
        """Record a request-scoped registration."""
        self.scopeds.append((abstract, concrete))
        return True

    def singleton(self, abstract: type, concrete: type) -> bool:
        """Record a singleton registration."""
        self.singletons.append((abstract, concrete))
        return True

class _StubFacade:
    """Facade double recording how many times it was pinned."""

    __slots__ = ("pins",)

    def __init__(self) -> None:
        """Start with an empty pin counter."""
        self.pins = 0

    async def pin(self) -> None:
        """Record that the facade was pinned."""
        self.pins += 1

class TestAuthProvider(TestCase):
    """Validate how the authentication module is wired."""

    def testIsRegisteredAsACoreProvider(self) -> None:
        """Validates that the module ships enabled by default.

        Applications must not have to register it by hand.
        """
        self.assertIn(AuthProvider, CORE_PROVIDERS)

    def testIsAServiceProvider(self) -> None:
        """Validates the base class of the provider.

        The container only boots real service providers.
        """
        self.assertTrue(issubclass(AuthProvider, ServiceProvider))

    def testIsNotDeferred(self) -> None:
        """Validates that the provider boots eagerly.

        ``Auth.user()`` is synchronous, so the facade must already be
        pinned when a template or a controller reads it. A deferred
        provider would hand out a dispatcher instead.
        """
        self.assertFalse(issubclass(AuthProvider, DeferrableProvider))

    def testRegistersEveryServiceAsASingleton(self) -> None:
        """Validates the exact set of container bindings.

        Every service is stateless, so a shared instance is both safe and
        cheaper than rebuilding one per request.
        """
        app = _RecordingApp()
        AuthProvider(app).register()

        self.assertEqual(app.singletons, [
            (IIdentityProvider, ModelIdentityProvider),
            (IPermissionRepository, DatabasePermissionRepository),
            (IAuthorizer, Authorizer),
            (PermissionRegistrar, PermissionRegistrar),
            (IAccessTokenRepository, AccessTokenRepository),
            (ISessionGuard, SessionGuard),
            (TokenGuard, TokenGuard),
            (IAuthManager, AuthManager),
        ])
        self.assertEqual(
            app.scopeds, [(IAuthenticationContext, AuthenticationContext)],
        )

    def testTheFacadeAccessorMatchesTheRegisteredContract(self) -> None:
        """Validates the consistency between provider and facade.

        A mismatch would make the facade unresolvable at boot time.
        """
        self.assertIs(AuthFacade.getFacadeAccessor(), IAuthManager)

class TestAuthProviderBoot(TestCase):
    """Validate the boot phase of the provider."""

    def setUp(self) -> None:
        """Install a facade double for the duration of the test."""
        from orionis.auth import provider as provider_module

        self._module = provider_module
        self._original = provider_module.AuthFacade
        self._facade = _StubFacade()
        provider_module.AuthFacade = self._facade

    def tearDown(self) -> None:
        """Restore the real facade."""
        self._module.AuthFacade = self._original

    async def testBootPinsTheFacade(self) -> None:
        """Validates that the facade becomes a direct passthrough.

        Without pinning, every ``Auth`` attribute access would build a
        deferred dispatcher and break the synchronous API.
        """
        await AuthProvider(_RecordingApp()).boot()
        self.assertEqual(self._facade.pins, 1)

class TestAuthFacadeInABootedApplication(TestCase):
    """Validate the facade as the running application exposes it."""

    def testTheFacadeIsPinnedAfterStartup(self) -> None:
        """Validates that the eager provider ran during boot.

        These assertions only hold inside a booted runtime, which is
        exactly the environment the test runner provides.
        """
        self.assertIsNotNone(AuthFacade._pinned_instance)

    def testTheFacadeAnswersSynchronously(self) -> None:
        """Validates the synchronous surface used by templates.

        ``Auth.check()`` must return a boolean, never a dispatcher.
        """
        self.assertIsInstance(AuthFacade.check(), bool)
        self.assertIsInstance(AuthFacade.guest(), bool)
        self.assertIsNone(AuthFacade.user())

    async def testContextInjectionIsScopedEvenBeforeAuthentication(self) -> None:
        """Resolve independent guest contexts through the real application DI."""
        app = Application()
        async with ScopeManager():
            first = await app.make(IAuthenticationContext)
            self.assertIs(first, await app.make(IAuthenticationContext))
            self.assertTrue(first.isGuest)
        async with ScopeManager():
            second = await app.make(IAuthenticationContext)
            self.assertIsNot(first, second)
            self.assertTrue(second.isGuest)
