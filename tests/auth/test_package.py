from __future__ import annotations
import types
from orionis.auth import __all__ as auth_exports
from orionis.auth import concerns, contracts, exceptions
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.concerns.functions import model_primary_key
from orionis.auth.entities.access_token import AccessToken
from orionis.auth.entities.guard_result import GuardResult
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
from orionis.failure.base.handler import _HTTP_STATUS_MAP
from orionis.http.enums.status import HTTPStatus
from orionis.test import TestCase

# Every exception of the module, used to assert the shared hierarchy.
_EXCEPTIONS = (
    AuthConfigurationException,
    AuthenticationException,
    AuthorizationException,
    GuardNotFoundException,
    IdentityProviderException,
    PolicyNotFoundException,
    TokenException,
)

class _Identity(Authenticatable, Authorizable):
    """Plain object mixing both authentication concerns."""

    __slots__ = ("id", "password")

    def __init__(self, identifier: int, password: str) -> None:
        """Store the identifier and the stored password hash."""
        self.id = identifier
        self.password = password

class _Meta:
    """Model metadata double exposing a custom primary key."""

    __slots__ = ("primary_key",)

    def __init__(self, primary_key: str) -> None:
        """Store the primary key name."""
        self.primary_key = primary_key

class _CustomKeyIdentity(Authenticatable, Authorizable):
    """Identity whose primary key is not called ``id``."""

    __slots__ = ("uuid",)

    __meta__ = _Meta("uuid")

    AUTHORIZABLE_TYPE = "tests.CustomIdentity"

    def __init__(self, uuid: str) -> None:
        """Store the custom primary key value."""
        self.uuid = uuid

class TestPackageSurface(TestCase):
    """Validate the public surface of the authentication package."""

    def testNoExportShadowsASubmodule(self) -> None:
        """Validates that the package never hides one of its modules.

        Exporting a name matching a submodule makes that submodule
        unreachable through attribute access.
        """
        import orionis.auth as package

        for name in auth_exports:
            self.assertNotIsInstance(getattr(package, name), types.ModuleType)

    def testExportsAreSortedAndResolvable(self) -> None:
        """Validates the declared export list.

        Every advertised name must exist and the list stays ordered.
        """
        import orionis.auth as package

        self.assertEqual(list(auth_exports), sorted(auth_exports))
        for name in auth_exports:
            self.assertTrue(hasattr(package, name))

    def testHeavyServicesAreNotImportedByThePackage(self) -> None:
        """Validates the guard against a circular import.

        ``orionis.support.facades`` imports this package very early, so
        the manager, the provider and the guards must stay out of it.
        """
        for name in ("AuthManager", "AuthProvider", "SessionGuard", "TokenGuard"):
            self.assertNotIn(name, auth_exports)

    def testEveryContractDeclaresEmptySlots(self) -> None:
        """Validates that contracts never add an instance dictionary.

        An abstract base without ``__slots__`` silently gives one to
        every implementation, defeating their own declarations.
        """
        for name in contracts.__all__:
            contract = getattr(contracts, name)
            self.assertIn("__slots__", contract.__dict__, name)
            self.assertEqual(contract.__slots__, (), name)

class TestExceptions(TestCase):
    """Validate the exception hierarchy of the module."""

    def testEveryExceptionSharesTheModuleBase(self) -> None:
        """Validates that callers can catch the whole module at once.

        A single ``except AuthException`` must cover every failure.
        """
        for exception in _EXCEPTIONS:
            self.assertTrue(issubclass(exception, AuthException))
            self.assertTrue(issubclass(exception, Exception))

    def testExceptionsAreDistinct(self) -> None:
        """Validates that each failure has its own type.

        Callers need to tell an unauthenticated request from a forbidden
        one without parsing messages.
        """
        self.assertEqual(len(set(_EXCEPTIONS)), len(_EXCEPTIONS))
        self.assertFalse(
            issubclass(AuthorizationException, AuthenticationException),
        )

    def testTheModuleExposesItsExceptions(self) -> None:
        """Validates that the exception module is importable as a whole.

        Applications may want to register their own handlers.
        """
        self.assertIs(exceptions.AuthException, AuthException)

class TestHttpStatusMapping(TestCase):
    """Validate how authentication failures become HTTP responses."""

    def testUnauthenticatedRequestsMapToFourZeroOne(self) -> None:
        """Validates the semantics of a missing identity.

        ``401`` means "no valid authenticated identity".
        """
        status, _ = _HTTP_STATUS_MAP[AuthenticationException]
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)

    def testForbiddenRequestsMapToFourZeroThree(self) -> None:
        """Validates the semantics of a missing authorization.

        ``403`` means "authenticated but not allowed".
        """
        status, _ = _HTTP_STATUS_MAP[AuthorizationException]
        self.assertEqual(status, HTTPStatus.FORBIDDEN)

    def testTheTwoStatusesAreNeverConfused(self) -> None:
        """Validates that both failures stay distinguishable.

        Collapsing them would hide why a request was rejected.
        """
        self.assertNotEqual(
            _HTTP_STATUS_MAP[AuthenticationException],
            _HTTP_STATUS_MAP[AuthorizationException],
        )

class TestConcerns(TestCase):
    """Validate the mixins applications add to their identity model."""

    def testTheMixinsAreVirtualImplementationsOfTheContracts(self) -> None:
        """Validates the mixin registration strategy.

        Inheriting from the abstract base directly would clash with the
        metaclass of every Orionis model, so the mixins are registered as
        virtual subclasses instead.
        """
        self.assertTrue(
            issubclass(Authenticatable, contracts.IAuthenticatable),
        )
        self.assertTrue(issubclass(Authorizable, contracts.IAuthorizable))
        self.assertNotIn(
            contracts.IAuthenticatable, Authenticatable.__mro__,
        )

    def testTheMixinsStayDictionaryFree(self) -> None:
        """Validates that the mixins add no per instance dictionary.

        They are mixed into models declaring their own slots.
        """
        self.assertEqual(Authenticatable.__slots__, ())
        self.assertEqual(Authorizable.__slots__, ())

    def testAnswersTheAuthenticationContract(self) -> None:
        """Validates the values read by the guards.

        The identifier is stored in the session and the hash is compared
        by the hashing module.
        """
        identity = _Identity(7, "hashed")
        self.assertEqual(identity.getAuthIdentifierName(), "id")
        self.assertEqual(identity.getAuthIdentifier(), 7)
        self.assertEqual(identity.getAuthPassword(), "hashed")

    def testAnswersTheAuthorizationContract(self) -> None:
        """Validates the polymorphic pair stored in the pivot tables.

        The default type is derived from the class itself.
        """
        identity = _Identity(7, "hashed")
        self.assertEqual(identity.getAuthorizableId(), 7)
        self.assertTrue(identity.getAuthorizableType().endswith("_Identity"))

    def testHonoursAnExplicitPolymorphicType(self) -> None:
        """Validates the override used to keep rows stable.

        Renaming or moving a class must not orphan its permissions.
        """
        identity = _CustomKeyIdentity("abc")
        self.assertEqual(identity.getAuthorizableType(), "tests.CustomIdentity")

    def testHonoursACustomPrimaryKey(self) -> None:
        """Validates that the model metadata drives the identifier.

        Models are free to use a UUID or any other key name.
        """
        identity = _CustomKeyIdentity("abc")
        self.assertEqual(identity.getAuthIdentifierName(), "uuid")
        self.assertEqual(identity.getAuthIdentifier(), "abc")
        self.assertEqual(identity.getAuthorizableId(), "abc")

    def testAMissingPasswordNeverBreaksVerification(self) -> None:
        """Validates the defensive answer of the password accessor.

        The hashing module always receives a string.
        """
        identity = _Identity(7, None)
        self.assertEqual(identity.getAuthPassword(), "")

    def testThePrimaryKeyHelperFallsBackToId(self) -> None:
        """Validates the behaviour for objects without model metadata.

        Plain objects still work as identities.
        """
        self.assertEqual(model_primary_key(object()), "id")

    def testTheConcernsPackageExposesItsMembers(self) -> None:
        """Validates the public surface of the concerns package.

        Applications import the mixins from here.
        """
        self.assertIs(concerns.Authenticatable, Authenticatable)
        self.assertIs(concerns.Authorizable, Authorizable)

class TestEntities(TestCase):
    """Validate the value objects exchanged inside the module."""

    def testGuardResultStaysImmutableAndSlotted(self) -> None:
        """Validates the transport object returned by a guard.

        It is created once per request and never mutated.
        """
        result = GuardResult(identity=object(), guard="session")
        self.assertFalse(hasattr(result, "__dict__"))
        self.assertIsNone(result.abilities)
        self.assertIsNone(result.credential_id)
        with self.assertRaises(AttributeError):
            result.guard = "token"

    def testAccessTokenIsSerialisable(self) -> None:
        """Validates the metadata exposed for a stored token.

        Applications list the tokens of an identity from this entity.
        """
        token = AccessToken(
            id=1,
            tokenable_type="app.models.user.User",
            tokenable_id=7,
            name="ci",
        )
        payload = token.toDict()
        self.assertEqual(payload["name"], "ci")
        self.assertEqual(payload["tokenable_id"], 7)

    def testTheIssuedSecretIsExcludedFromTheRepresentation(self) -> None:
        """Validates that a freshly issued token never leaks in logs.

        The plain text is only meant for the response body.
        """
        issued = NewAccessToken(
            access_token=AccessToken(
                id=1,
                tokenable_type="app.models.user.User",
                tokenable_id=7,
                name="ci",
            ),
            plain_text="super-secret-value",
        )
        self.assertNotIn("super-secret-value", repr(issued))
        self.assertEqual(issued.plain_text, "super-secret-value")
