# ruff: noqa: ARG002, PT009, PT027, SLF001, TC001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Preserve fixture call signatures and runtime context dependency injection.

"""Verify authentication authorizer contracts and behavior."""

import asyncio
from orionis.auth.authorization.authorizer import Authorizer
from orionis.auth.authorization.policy import Policy
from orionis.auth.authorization.registry import PolicyRegistry
from orionis.auth.authorization.snapshot import AuthorizationSnapshot
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import bind_auth_context
from orionis.auth.contracts.policy import IPolicy
from orionis.auth.exceptions import PolicyNotFoundException
from orionis.container.container import Container
from orionis.container.context.manager import ScopeManager
from orionis.test import TestCase

from orionis.auth.contracts.context import IAuthenticationContext


class _Identity:
    """Identity double owning a fixed identifier."""

    __slots__ = ("identifier",)

    def __init__(self, identifier: int = 1) -> None:
        """Store the identifier answered by the contract method.

        Parameters
        ----------
        identifier : int
            Value supplied for ``identifier``.

        Returns
        -------
        None
            No return value.
        """
        self.identifier = identifier

    def getAuthIdentifierName(self) -> str:
        """Return the attribute holding the identifier.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "identifier"

    def getAuthIdentifier(self) -> object:
        """Return the identifier of this identity.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self.identifier

    def getAuthPassword(self) -> str:
        """Return an empty hash; credentials are irrelevant here.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return ""


class _StaticRepository:
    """Permission repository double returning a fixed authorization."""

    __slots__ = ("permissions", "roles")

    def __init__(
        self,
        permissions: tuple[str, ...] = (),
        roles: tuple[str, ...] = (),
    ) -> None:
        """Store the authorization every identity resolves to.

        Parameters
        ----------
        permissions : tuple[str, ...]
            Value supplied for ``permissions``.
        roles : tuple[str, ...]
            Value supplied for ``roles``.

        Returns
        -------
        None
            No return value.
        """
        self.permissions = permissions
        self.roles = roles

    async def loadFor(
        self,
        authorizable: object,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return the configured permissions and roles.

        Parameters
        ----------
        authorizable : object
            Value supplied for ``authorizable``.

        Returns
        -------
        tuple[frozenset[str], frozenset[str]]
            Value produced by the helper.
        """
        return frozenset(self.permissions), frozenset(self.roles)


class _StubApp:
    """Application double building policies without a real container."""

    __slots__ = ("built",)

    def __init__(self) -> None:
        """Start with an empty build journal.

        Returns
        -------
        None
            No return value.
        """
        self.built: list[type] = []

    async def build(self, target: type) -> object:
        """Instantiate the requested class and record the call.

        Parameters
        ----------
        target : type
            Value supplied for ``target``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        self.built.append(target)
        return target()


class _Post:
    """Resource double owned by an identifier."""

    __slots__ = ("owner_id",)

    def __init__(self, owner_id: int) -> None:
        """Store the identifier of the owner.

        Parameters
        ----------
        owner_id : int
            Value supplied for ``owner_id``.

        Returns
        -------
        None
            No return value.
        """
        self.owner_id = owner_id


class _Draft(_Post):
    """Resource subclass used to exercise inherited policies."""

    __slots__ = ()


class _PostPolicy(Policy):
    """Policy granting write access only to the owner of a post."""

    __slots__ = ()

    async def update(self, identity: object, post: _Post) -> bool:
        """Allow the update only when the identity owns the post.

        Parameters
        ----------
        identity : object
            Value supplied for ``identity``.
        post : _Post
            Value supplied for ``post``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return post.owner_id == identity.getAuthIdentifier()

    async def create(self, identity: object, resource: object) -> bool:
        """Allow creation for every authenticated identity.

        Parameters
        ----------
        identity : object
            Value supplied for ``identity``.
        resource : object
            Value supplied for ``resource``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True

    def archive(self, identity: object, post: _Post) -> bool:
        """Allow archiving through a synchronous ability.

        Parameters
        ----------
        identity : object
            Value supplied for ``identity``.
        post : _Post
            Value supplied for ``post``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True


class _SuperPolicy(Policy):
    """Policy granting everything through the ``before`` hook."""

    __slots__ = ()

    async def before(self, identity: object, ability: str) -> bool | None:
        """Grant every ability without running the ability method.

        Parameters
        ----------
        identity : object
            Value supplied for ``identity``.
        ability : str
            Value supplied for ``ability``.

        Returns
        -------
        bool | None
            Value produced by the helper.
        """
        return True


class _DenyingPolicy(Policy):
    """Policy denying everything through the ``before`` hook."""

    __slots__ = ()

    async def before(self, identity: object, ability: str) -> bool | None:
        """Deny every ability without running the ability method.

        Parameters
        ----------
        identity : object
            Value supplied for ``identity``.
        ability : str
            Value supplied for ``ability``.

        Returns
        -------
        bool | None
            Value produced by the helper.
        """
        return False

    async def update(self, identity: object, post: _Post) -> bool:
        """Return an unused grant behind the denying hook.

        Parameters
        ----------
        identity : object
            Value supplied for ``identity``.
        post : _Post
            Value supplied for ``post``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True


class _UnclearPolicy(Policy):
    """Return a truthy non-boolean to exercise fail-closed evaluation."""

    __slots__ = ()

    def update(self, identity: object, post: _Post) -> str:
        """Return a value that must not grant authorization.

        Parameters
        ----------
        identity : object
            Value supplied for ``identity``.
        post : _Post
            Value supplied for ``post``.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "denied"


class _InjectedPolicy(Policy):
    """Verify that a policy's dependencies belong to its current request."""

    __slots__ = ("context",)

    def __init__(self, context: IAuthenticationContext) -> None:
        """Retain the context supplied by real constructor injection.

        Parameters
        ----------
        context : IAuthenticationContext
            Value supplied for ``context``.

        Returns
        -------
        None
            No return value.
        """
        self.context = context

    def update(self, identity: object, post: _Post) -> bool:
        """Grant only when both explicit and injected identity own the resource.

        Parameters
        ----------
        identity : object
            Value supplied for ``identity``.
        post : _Post
            Value supplied for ``post``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return (
            self.context.identifier() == post.owner_id
            and identity.getAuthIdentifier() == post.owner_id
        )


def authenticated(
    permissions: tuple[str, ...] = (),
    roles: tuple[str, ...] = (),
    abilities: tuple[str, ...] | None = None,
) -> AuthenticationContext:
    """Build an authenticated context backed by a static repository.

    Parameters
    ----------
    permissions : tuple[str, ...]
        Value supplied for ``permissions``.
    roles : tuple[str, ...]
        Value supplied for ``roles``.
    abilities : tuple[str, ...] | None
        Value supplied for ``abilities``.

    Returns
    -------
    AuthenticationContext
        Value produced by the helper.
    """
    return AuthenticationContext(
        identity=_Identity(),
        guard="session",
        abilities=abilities,
        repository=_StaticRepository(permissions, roles),
    )


class TestPolicyRegistry(TestCase):
    """Validate how policies are bound to resource classes."""

    def testReturnsNoneForAnUnknownResource(self) -> None:
        """Validate the answer when nothing is registered.

        The authorizer turns this into an explicit error.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNone(PolicyRegistry().policyFor(_Post))

    def testResolvesTheRegisteredPolicy(self) -> None:
        """Validate the direct binding of a resource class.

        This is the common case for a one-to-one mapping.

        Returns
        -------
        None
            No return value.
        """
        registry = PolicyRegistry()
        registry.register(_Post, _PostPolicy)
        self.assertIs(registry.policyFor(_Post), _PostPolicy)

    def testResolvesAPolicyInheritedFromAnAncestor(self) -> None:
        """Validate the method resolution order walk.

        A subclass without its own policy must reuse the parent one.

        Returns
        -------
        None
            No return value.
        """
        registry = PolicyRegistry()
        registry.register(_Post, _PostPolicy)
        self.assertIs(registry.policyFor(_Draft), _PostPolicy)

    def testPrefersTheMostSpecificPolicy(self) -> None:
        """Validate that a subclass may override the inherited policy.

        The nearest ancestor in the resolution order wins.

        Returns
        -------
        None
            No return value.
        """
        registry = PolicyRegistry()
        registry.register(_Post, _PostPolicy)
        registry.register(_Draft, _SuperPolicy)
        self.assertIs(registry.policyFor(_Draft), _SuperPolicy)
        self.assertIs(registry.policyFor(_Post), _PostPolicy)

    def testInvalidatesTheLookupCacheOnRegistration(self) -> None:
        """Validate that a late registration is taken into account.

        A cached miss must not survive a new binding.

        Returns
        -------
        None
            No return value.
        """
        registry = PolicyRegistry()
        self.assertIsNone(registry.policyFor(_Draft))
        registry.register(_Draft, _PostPolicy)
        self.assertIs(registry.policyFor(_Draft), _PostPolicy)

    def testRejectsNonClassArguments(self) -> None:
        """Validate the input guards of the registry.

        Registering an instance would fail much later, at lookup time.

        Returns
        -------
        None
            No return value.
        """
        registry = PolicyRegistry()
        with self.assertRaises(TypeError):
            registry.register(_Post(1), _PostPolicy)
        with self.assertRaises(TypeError):
            registry.register(_Post, _PostPolicy())
        with self.assertRaises(TypeError):
            registry.register(_Post, object)

    def testExposesACopyOfItsBindings(self) -> None:
        """Validate that callers cannot mutate the registry.

        The returned mapping is a snapshot, not the live state.

        Returns
        -------
        None
            No return value.
        """
        registry = PolicyRegistry()
        registry.register(_Post, _PostPolicy)
        bindings = registry.bindings()
        bindings.clear()
        self.assertIs(registry.policyFor(_Post), _PostPolicy)


class TestPolicyBase(TestCase):
    """Validate the base class shared by every policy."""

    def testImplementsTheContract(self) -> None:
        """Validate that policies satisfy the declared interface.

        The authorizer only depends on the contract.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(_PostPolicy(), IPolicy)

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """Validate that policies stay dictionary free.

        Each evaluation builds a policy, so its slotted layout avoids
        an instance dictionary.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(hasattr(_PostPolicy(), "__dict__"))

    async def testTheDefaultHookNeverShortCircuits(self) -> None:
        """Validate the neutral default of the ``before`` hook.

        Without an override the ability method decides the outcome.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsNone(await _PostPolicy().before(_Identity(), "update"))


class TestAuthorizer(TestCase):
    """Validate permission, role and policy evaluation."""

    def setUp(self) -> None:
        """Build an authorizer over an application double.

        Returns
        -------
        None
            No return value.
        """
        self.app = _StubApp()
        self.authorizer = Authorizer(self.app)

    async def testGuestsAreDeniedWithoutTouchingTheSnapshot(self) -> None:
        """Validate the fast path for anonymous requests.

        A guest owns nothing, so no query may be issued.

        Returns
        -------
        None
            No return value.
        """
        guest = AuthenticationContext()
        self.assertFalse(await self.authorizer.can(guest, "users.view"))
        self.assertFalse(await self.authorizer.canAny(guest, ["users.view"]))
        self.assertFalse(await self.authorizer.canAll(guest, ["users.view"]))
        self.assertFalse(await self.authorizer.hasRole(guest, "admin"))
        self.assertFalse(await self.authorizer.allows(guest, "update", _Post(1)))

    async def testGrantsAPermissionOwnedByTheIdentity(self) -> None:
        """Validate the direct permission path.

        The snapshot is the single source of truth.

        Returns
        -------
        None
            No return value.
        """
        context = authenticated(permissions=("users.view",))
        self.assertTrue(await self.authorizer.can(context, "users.view"))
        self.assertFalse(await self.authorizer.can(context, "users.delete"))

    async def testEvaluatesAnyAndAllCombinations(self) -> None:
        """Validate the combined permission checks.

        ``canAny`` is a union test while ``canAll`` is an intersection.

        Returns
        -------
        None
            No return value.
        """
        context = authenticated(permissions=("users.view",))
        wanted = ["users.view", "users.delete"]
        self.assertTrue(await self.authorizer.canAny(context, wanted))
        self.assertFalse(await self.authorizer.canAll(context, wanted))
        self.assertTrue(
            await self.authorizer.canAll(context, ["users.view"]),
        )

    async def testReportsTheRolesOfTheIdentity(self) -> None:
        """Validate role membership through the authorizer.

        Roles come from the same snapshot as the permissions.

        Returns
        -------
        None
            No return value.
        """
        context = authenticated(roles=("admin",))
        self.assertTrue(await self.authorizer.hasRole(context, "admin"))
        self.assertFalse(await self.authorizer.hasRole(context, "editor"))

    async def testTokenAbilitiesNarrowThePermissions(self) -> None:
        """Validate the intersection rule at the authorizer level.

        A token must never widen the authorization of its owner.

        Returns
        -------
        None
            No return value.
        """
        context = authenticated(
            permissions=("users.view", "users.delete"),
            abilities=("users.view",),
        )
        self.assertTrue(await self.authorizer.can(context, "users.view"))
        self.assertFalse(await self.authorizer.can(context, "users.delete"))

    async def testRunsThePolicyAbilityForTheResource(self) -> None:
        """Validate the resource aware authorization path.

        The policy receives the identity and the resource instance.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _PostPolicy)
        context = authenticated()

        self.assertTrue(
            await self.authorizer.allows(context, "update", _Post(1)),
        )
        self.assertFalse(
            await self.authorizer.allows(context, "update", _Post(2)),
        )

    async def testSupportsSynchronousAbilities(self) -> None:
        """Validate that a policy may declare a synchronous ability.

        Not every rule needs to await something.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _PostPolicy)
        context = authenticated()
        self.assertTrue(
            await self.authorizer.allows(context, "archive", _Post(9)),
        )

    async def testEvaluatesAbilitiesAgainstTheResourceClass(self) -> None:
        """Validate the gate used by the policy middleware.

        Abilities such as ``create`` have no instance to inspect.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _PostPolicy)
        context = authenticated()
        self.assertTrue(await self.authorizer.allows(context, "create", _Post))

    async def testTheBeforeHookCanGrantEverything(self) -> None:
        """Validate the super administrator escape hatch.

        An explicit True hook answer skips the ability method entirely.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _SuperPolicy)
        context = authenticated()
        self.assertTrue(
            await self.authorizer.allows(context, "anything", _Post(1)),
        )

    async def testTheBeforeHookCanDenyEverything(self) -> None:
        """Validate that the hook also short circuits a denial.

        The ability method must not be able to override it.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _DenyingPolicy)
        context = authenticated()
        self.assertFalse(
            await self.authorizer.allows(context, "update", _Post(1)),
        )

    async def testFailsWhenTheResourceHasNoPolicy(self) -> None:
        """Validate the error raised for an unprotected resource.

        Answering ``False`` would hide a configuration mistake.

        Returns
        -------
        None
            No return value.
        """
        context = authenticated()
        with self.assertRaises(PolicyNotFoundException):
            await self.authorizer.allows(context, "update", _Post(1))

    async def testFailsWhenThePolicyLacksTheAbility(self) -> None:
        """Validate the error raised for a misspelled ability.

        A silent denial would be very hard to debug.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _PostPolicy)
        context = authenticated()
        with self.assertRaises(PolicyNotFoundException):
            await self.authorizer.allows(context, "publish", _Post(1))

    async def testNeverRetainsPolicyInstancesBetweenEvaluations(self) -> None:
        """Build policies per evaluation without capturing scoped dependencies.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _PostPolicy)
        context = authenticated()

        await self.authorizer.allows(context, "update", _Post(1))
        await self.authorizer.allows(context, "update", _Post(1))

        self.assertEqual(self.app.built, [_PostPolicy, _PostPolicy])

    async def testPolicyAbilitiesCannotBypassTokenRestrictions(self) -> None:
        """Intersect a policy decision with the credential's exact abilities.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _PostPolicy)
        restricted = authenticated(abilities=("create",))
        allowed = authenticated(abilities=("update",))

        self.assertFalse(
            await self.authorizer.allows(restricted, "update", _Post(1)),
        )
        self.assertTrue(await self.authorizer.allows(allowed, "update", _Post(1)))
        self.assertFalse(await self.authorizer.allows(allowed, "update", _Post(2)))

    async def testBeforeHookCannotElevateARestrictedToken(self) -> None:
        """Apply credential restrictions before the policy's granting hook.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _SuperPolicy)
        context = authenticated(abilities=())

        self.assertFalse(await self.authorizer.allows(context, "update", _Post(1)))
        self.assertEqual(self.app.built, [])

    async def testTruthyNonBooleanPolicyResultIsDenied(self) -> None:
        """Require an explicit True instead of arbitrary truthy values.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _UnclearPolicy)
        self.assertFalse(
            await self.authorizer.allows(authenticated(), "update", _Post(1)),
        )

    async def testPolicyInternalsAreNotPublicAbilities(self) -> None:
        """Deny reserved hooks and private attributes before policy dispatch.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _SuperPolicy)
        context = authenticated()
        for ability in ("before", "__class__", "_private", ""):
            self.assertFalse(
                await self.authorizer.allows(context, ability, _Post(1)),
            )

    def testExposesItsRegistry(self) -> None:
        """Validate that the registry is reachable for inspection.

        Applications may want to list every protected resource.

        Returns
        -------
        None
            No return value.
        """
        self.authorizer.registerPolicy(_Post, _PostPolicy)
        self.assertIs(self.authorizer.registry().policyFor(_Post), _PostPolicy)

    async def testSnapshotStaysStableAcrossChecks(self) -> None:
        """Validate that repeated checks reuse the same picture.

        Authorization must not change halfway through a request.

        Returns
        -------
        None
            No return value.
        """
        context = authenticated(permissions=("users.view",))
        await self.authorizer.can(context, "users.view")
        snapshot = await context.authorization()
        self.assertIsInstance(snapshot, AuthorizationSnapshot)
        self.assertIs(snapshot, await context.authorization())

    async def testPolicyDependenciesStayRequestLocalUnderConcurrency(self) -> None:
        """Build policy dependencies from the right scope across concurrent calls.

        Returns
        -------
        None
            No return value.
        """
        container = type("PolicyTestContainer", (Container,), {})()
        authorizer = Authorizer(container)
        authorizer.registerPolicy(_Post, _InjectedPolicy)
        barrier = asyncio.Barrier(2)

        async def handle(identifier: int) -> None:
            """Handle a request in the isolated test scope.

            Parameters
            ----------
            identifier : int
                Value supplied for ``identifier``.

            Returns
            -------
            None
                No return value.
            """
            async with ScopeManager():
                context = AuthenticationContext(identity=_Identity(identifier))
                bind_auth_context(context)
                self.assertTrue(
                    await authorizer.allows(context, "update", _Post(identifier)),
                )
                await barrier.wait()
                self.assertTrue(
                    await authorizer.allows(context, "update", _Post(identifier)),
                )

        try:
            await asyncio.wait_for(asyncio.gather(handle(1), handle(2)), timeout=5)
        finally:
            Container._instances.pop(type(container), None)
