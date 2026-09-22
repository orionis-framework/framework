import types
from orionis import auth as package
from orionis.auth import __all__ as auth_exports
from orionis.auth.authorization.policy import Policy
from orionis.auth.authorization.snapshot import AuthorizationSnapshot
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.entities.access_token import AccessToken
from orionis.auth.entities.new_access_token import NewAccessToken
from orionis.auth.exceptions import (
    AuthConfigurationException,
    AuthenticationException,
    AuthException,
    AuthorizationException,
    GuardNotFoundException,
    IdentityProviderException,
    PolicyNotFoundException,
    TokenException,
)
from orionis.test import TestCase

# Exact public surface the package promises, mapped to the object each
# name must resolve to.
_EXPECTED_EXPORTS: dict[str, object] = {
    "AccessToken": AccessToken,
    "AuthConfigurationException": AuthConfigurationException,
    "AuthException": AuthException,
    "Authenticatable": Authenticatable,
    "AuthenticationContext": AuthenticationContext,
    "AuthenticationException": AuthenticationException,
    "Authorizable": Authorizable,
    "AuthorizationException": AuthorizationException,
    "AuthorizationSnapshot": AuthorizationSnapshot,
    "GuardNotFoundException": GuardNotFoundException,
    "IdentityProviderException": IdentityProviderException,
    "NewAccessToken": NewAccessToken,
    "Policy": Policy,
    "PolicyNotFoundException": PolicyNotFoundException,
    "TokenException": TokenException,
}

# Services deliberately left out of the package because they drag the
# HTTP and ORM stacks in.
_HEAVY_SERVICES = (
    "AuthManager",
    "AuthProvider",
    "SessionGuard",
    "TokenGuard",
    "ModelIdentityProvider",
    "AccessTokenRepository",
)


class TestPackageSurface(TestCase):
    """Validate the public surface of the authentication package."""

    def testExportsExactlyTheDocumentedNames(self) -> None:
        """Compare the advertised exports against the expected set.

        Validates that no name is silently added or dropped from the
        package entry point.
        """
        self.assertEqual(set(auth_exports), set(_EXPECTED_EXPORTS))

    def testEveryExportResolvesToItsOwnObject(self) -> None:
        """Resolve each advertised name through the package.

        Validates that the re-exports point at the very objects their
        defining modules expose, never at a copy or an alias.
        """
        for name, expected in _EXPECTED_EXPORTS.items():
            self.assertIs(getattr(package, name), expected, name)

    def testTheExportListStaysSorted(self) -> None:
        """Compare the export list against its sorted counterpart.

        Validates that the list keeps a deterministic order, which makes
        review diffs readable.
        """
        self.assertEqual(list(auth_exports), sorted(auth_exports))

    def testNoExportShadowsASubmodule(self) -> None:
        """Check that no advertised name resolves to a module.

        Validates the package never hides one of its own submodules,
        which would make it unreachable through attribute access.
        """
        for name in auth_exports:
            self.assertNotIsInstance(getattr(package, name), types.ModuleType)

    def testHeavyServicesStayOutOfThePackage(self) -> None:
        """Check that the eager services are not re-exported.

        Validates the guard against a circular import: the facades
        package imports this one very early, so the manager, the provider
        and the guards must stay in their own modules.
        """
        for name in _HEAVY_SERVICES:
            self.assertNotIn(name, auth_exports)
            self.assertFalse(hasattr(package, name), name)
