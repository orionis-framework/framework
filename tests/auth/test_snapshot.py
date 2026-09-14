from __future__ import annotations
from orionis.auth.authorization.snapshot import (
    EMPTY_SNAPSHOT,
    AuthorizationSnapshot,
)
from orionis.auth.contracts.snapshot import IAuthorizationSnapshot
from orionis.test import TestCase

class TestAuthorizationSnapshot(TestCase):
    """Validate the immutable authorization picture of a request."""

    def testImplementsTheContract(self) -> None:
        """Validates the declared contract of the snapshot.

        The rest of the module depends on the interface, never on the
        concrete class.
        """
        snapshot = AuthorizationSnapshot(permissions=(), roles=())
        self.assertIsInstance(snapshot, IAuthorizationSnapshot)

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """Validates that the snapshot stays dictionary free.

        One snapshot is built per authenticated request, so it must not
        pay for a per instance dictionary.
        """
        snapshot = AuthorizationSnapshot(permissions=(), roles=())
        self.assertFalse(hasattr(snapshot, "__dict__"))

    def testNormalisesEveryCollectionToAFrozenSet(self) -> None:
        """Validates that the snapshot cannot be mutated after creation.

        Sharing a mutable set between coroutines would break the
        guarantee that the picture never changes mid request.
        """
        snapshot = AuthorizationSnapshot(
            permissions=["users.view", "users.view"],
            roles=["admin"],
            abilities=["users.view"],
        )
        self.assertEqual(snapshot.permissions, frozenset({"users.view"}))
        self.assertEqual(snapshot.roles, frozenset({"admin"}))
        self.assertEqual(snapshot.abilities, frozenset({"users.view"}))

    def testGrantsAPermissionTheIdentityOwns(self) -> None:
        """Validates the basic permission check.

        A permission present in the snapshot must be granted.
        """
        snapshot = AuthorizationSnapshot(
            permissions=("users.view",), roles=(),
        )
        self.assertTrue(snapshot.can("users.view"))

    def testDeniesAPermissionTheIdentityDoesNotOwn(self) -> None:
        """Validates that unknown permissions are denied.

        Authorization defaults to deny.
        """
        snapshot = AuthorizationSnapshot(
            permissions=("users.view",), roles=(),
        )
        self.assertFalse(snapshot.can("users.delete"))
        self.assertFalse(snapshot.can("does.not.exist"))

    def testUnrestrictedCredentialsKeepEveryPermission(self) -> None:
        """Validates that a credential without abilities narrows nothing.

        Session authentication carries no abilities at all.
        """
        snapshot = AuthorizationSnapshot(
            permissions=("users.view", "users.delete"), roles=(),
        )
        self.assertIsNone(snapshot.abilities)
        self.assertTrue(snapshot.can("users.view"))
        self.assertTrue(snapshot.can("users.delete"))

    def testAbilitiesIntersectTheIdentityPermissions(self) -> None:
        """Validates that a token can only narrow the authorization.

        The effective set is the intersection of what the identity owns
        and what the token is allowed to use.
        """
        snapshot = AuthorizationSnapshot(
            permissions=("users.view", "users.create", "users.delete"),
            roles=(),
            abilities=("users.view",),
        )
        self.assertTrue(snapshot.can("users.view"))
        self.assertFalse(snapshot.can("users.create"))
        self.assertFalse(snapshot.can("users.delete"))

    def testAbilitiesNeverElevateTheIdentityPermissions(self) -> None:
        """Validates the core security invariant of token abilities.

        An ability the identity does not own must stay denied, otherwise
        a token could grant more than its owner.
        """
        snapshot = AuthorizationSnapshot(
            permissions=("users.view",),
            roles=(),
            abilities=("users.view", "users.delete"),
        )
        self.assertTrue(snapshot.can("users.view"))
        self.assertFalse(snapshot.can("users.delete"))

    def testAnEmptyAbilitySetDeniesEverything(self) -> None:
        """Validates that a token with no ability is powerless.

        An empty tuple is a real restriction, unlike ``None``.
        """
        snapshot = AuthorizationSnapshot(
            permissions=("users.view",), roles=(), abilities=(),
        )
        self.assertEqual(snapshot.abilities, frozenset())
        self.assertFalse(snapshot.can("users.view"))

    def testReportsTheRolesOfTheIdentity(self) -> None:
        """Validates role membership lookups.

        Roles are answered from the same immutable picture.
        """
        snapshot = AuthorizationSnapshot(
            permissions=(), roles=("admin", "editor"),
        )
        self.assertTrue(snapshot.hasRole("admin"))
        self.assertTrue(snapshot.hasRole("editor"))
        self.assertFalse(snapshot.hasRole("owner"))

    def testAbilitiesNeverRestrictRoles(self) -> None:
        """Validates that abilities only apply to permissions.

        Roles describe who the identity is, not what the credential may
        do on this request.
        """
        snapshot = AuthorizationSnapshot(
            permissions=(), roles=("admin",), abilities=(),
        )
        self.assertTrue(snapshot.hasRole("admin"))

    def testTheSharedEmptySnapshotDeniesEverything(self) -> None:
        """Validates the snapshot handed to guest requests.

        Guests must never resolve permissions from the database.
        """
        self.assertEqual(EMPTY_SNAPSHOT.permissions, frozenset())
        self.assertEqual(EMPTY_SNAPSHOT.roles, frozenset())
        self.assertIsNone(EMPTY_SNAPSHOT.abilities)
        self.assertFalse(EMPTY_SNAPSHOT.can("users.view"))
        self.assertFalse(EMPTY_SNAPSHOT.hasRole("admin"))

    def testRepresentationNeverLeaksPermissionNames(self) -> None:
        """Validates that debugging output stays free of authorization data.

        A snapshot may end up in a log line, so it only reports sizes.
        """
        snapshot = AuthorizationSnapshot(
            permissions=("users.view",), roles=("admin",), abilities=(),
        )
        text = repr(snapshot)
        self.assertNotIn("users.view", text)
        self.assertIn("permissions=1", text)
        self.assertIn("roles=1", text)
        self.assertIn("abilities=0", text)

    def testRepresentationMarksUnrestrictedCredentials(self) -> None:
        """Validates that an unrestricted credential is recognisable.

        ``None`` and an empty set mean opposite things.
        """
        snapshot = AuthorizationSnapshot(permissions=(), roles=())
        self.assertIn("abilities=unrestricted", repr(snapshot))
