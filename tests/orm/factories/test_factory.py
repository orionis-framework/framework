import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, ClassVar, Self
from faker import Faker
from faker.exceptions import UniquenessException
from app.models.user import User
from database.factories.user_factory import UserFactory as ApplicationUserFactory
from orionis.container.container import Container
from orionis.database.connection_manager import ConnectionManager
from orionis.database.exceptions import QueryException
from orionis.foundation.application import Application
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.orm import (
    Boolean,
    Integer,
    Model,
    StrictJson,
    StrictTimestamp,
    String,
)
from orionis.orm.exceptions import MassAssignmentException
from orionis.orm.factories import Factory, Sequence
from orionis.orm.factories.exceptions import (
    FactoryConcurrencyException,
    FactoryConfigurationException,
    FactoryDefinitionException,
    FactoryPersistenceException,
)
from orionis.orm.resolver import ConnectionResolver
from orionis.support.types.collection import Collection
from orionis.test import TestCase

class FactoryUser(Model):
    """Exercise real assignment, casts, defaults, timestamps, and persistence."""

    table = "factory_users"
    id = Integer().primary().autoIncrement()
    name = String()
    email = String().unique()
    active = Boolean()
    profile = StrictJson()
    tier = String().default("member")
    created_at = StrictTimestamp().nullable()
    updated_at = StrictTimestamp().nullable()

    fillable: ClassVar[list[str]] = ["name", "email", "active", "profile"]
    casts: ClassVar[dict[str, str]] = {"active": "bool", "profile": "json"}

    def setEmailAttribute(self, value: str) -> str:
        """Normalize the address through the existing model mutator.

        Parameters
        ----------
        value : str
            Raw email supplied by the factory or caller.

        Returns
        -------
        str
            Lowercase address without surrounding whitespace.
        """
        return value.strip().lower()

class UserFactory(Factory[FactoryUser]):
    """Provide an explicit definition suitable for every strategy."""

    model = FactoryUser

    def definition(self) -> dict[str, Any]:
        """Build fresh attributes using the instance's complete Faker API.

        Returns
        -------
        dict[str, Any]
            User values, excluding automatic database columns.
        """
        return {
            "name": self.fake.name(),
            "email": self.fake.unique.email(),
            "active": True,
            "profile": {"tags": []},
        }

    def inactive(self) -> Self:
        """Apply a named state through an ordinary Python method.

        Returns
        -------
        Self
            Current factory configured for inactive users.
        """
        return self.state({"active": False})

class _ConstantUniqueFactory(UserFactory):
    """Use a finite provider to expose unique lifecycle deterministically."""

    def definition(self) -> dict[str, Any]:
        """Generate an address whose finite domain can be exhausted.

        Returns
        -------
        dict[str, Any]
            User values with exactly one possible unique address.
        """
        values = super().definition()
        values["email"] = self.fake.unique.randomElement(
            elements=("only@example.test",),
        )
        return values

class _SharedDefinitionFactory(UserFactory):
    """Return an intentionally reused mapping to verify input isolation."""

    __slots__ = ("attributes", "calls")

    def __init__(self) -> None:
        """Keep the fixture's source mapping available for assertions.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        super().__init__(seed=42)
        self.calls = 0
        self.attributes = {
            "name": "Original",
            "email": "original@example.test",
            "active": True,
            "profile": {"tags": []},
        }

    def definition(self) -> dict[str, Any]:
        """Return the same input mapping on every invocation.

        Returns
        -------
        dict[str, Any]
            Source attributes that must never be mutated by generation.
        """
        self.calls += 1
        return self.attributes

class _MissingDefinitionFactory(Factory[FactoryUser]):
    """Leave the abstract definition unimplemented."""

    model = FactoryUser

class _CopyAwareMapping(dict[str, object]):
    """Expose a custom dictionary copy protocol without instance state."""

    __slots__ = ()

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        """Preserve the dictionary subclass's explicit copy protocol.

        Parameters
        ----------
        memo : dict of int to object
            Objects already detached by the current copy operation.

        Returns
        -------
        Self
            New mapping carrying a recognizable copy marker.
        """
        copied = type(self)({"copied": True})
        memo[id(self)] = copied
        return copied

class _AsyncDefinitionFactory(UserFactory):
    """Declare an invalid asynchronous definition."""

    async def definition(self) -> dict[str, Any]:
        """Return values asynchronously to exercise early validation.

        Returns
        -------
        dict[str, Any]
            Empty invalid definition fixture.
        """
        return {}

class _FactoryDependency:
    """Supply a concrete dependency through the native container."""

    __slots__ = ()

    def name(self) -> str:
        """Return a recognizable injected value.

        Returns
        -------
        str
            Name supplied by the dependency.
        """
        return "Injected dependency"

class _InjectedFactory(UserFactory):
    """Retain runtime constructor annotations used by Orionis DI."""

    __slots__ = ("dependency",)

    def __init__(
        self,
        dependency: _FactoryDependency,
        *,
        locale: str | None = None,
        seed: int | None = None,
    ) -> None:
        """Receive a native injected dependency and normal Faker options.

        Parameters
        ----------
        dependency : _FactoryDependency
            Service provided by the container.
        locale : str or None, optional
            Faker locale override, or the configured application locale.
        seed : int or None, optional
            Instance random seed.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        super().__init__(locale=locale, seed=seed)
        self.dependency = dependency

    def definition(self) -> dict[str, Any]:
        """Compose the definition using an injected service.

        Returns
        -------
        dict[str, Any]
            Faker data enriched by the dependency.
        """
        return {**super().definition(), "name": self.dependency.name()}

class _DatabaseConfig:
    """Supply only the configuration interface needed by ConnectionManager."""

    __slots__ = ("database",)

    def __init__(self, database: str) -> None:
        """Store the private SQLite file path.

        Parameters
        ----------
        database : str
            File shared by the test's independent database connections.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.database = database

    def config(self, key: str) -> dict[str, Any]:  # noqa: ARG002
        """Return the file-backed database configuration.

        Parameters
        ----------
        key : str
            Configuration key requested by ConnectionManager.

        Returns
        -------
        dict[str, Any]
            Real SQLite connection settings.
        """
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {"driver": "sqlite", "database": self.database},
            },
        }

class _LifecycleObserver:
    """Observe the model's existing event lifecycle without replacing save."""

    __slots__ = ("events",)

    def __init__(self) -> None:
        """Prepare event observations owned by this test instance.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.events: list[tuple[str, bool]] = []

    def saving(self, user: FactoryUser) -> None:
        """Record the pre-save event.

        Parameters
        ----------
        user : FactoryUser
            Model emitted by the native event dispatcher.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.events.append(("saving", user._exists))

    async def creating(self, user: FactoryUser) -> None:
        """Apply an asynchronous before-create event mutation.

        Parameters
        ----------
        user : FactoryUser
            Model emitted by the native event dispatcher.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        await asyncio.sleep(0)
        self.events.append(("creating", user._exists))
        user.name = "Created by observer"

    async def created(self, user: FactoryUser) -> None:
        """Record an asynchronous post-insert event.

        Parameters
        ----------
        user : FactoryUser
            Persisted model emitted by the native event dispatcher.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        await asyncio.sleep(0)
        self.events.append(("created", user._exists))

    def saved(self, user: FactoryUser) -> None:
        """Record the completed model lifecycle.

        Parameters
        ----------
        user : FactoryUser
            Persisted model emitted by the native event dispatcher.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.events.append(("saved", user._exists))

class _PauseObserver:
    """Hold a genuine save event so concurrent access can be tested."""

    __slots__ = ("entered", "release")

    def __init__(self) -> None:
        """Create task-local coordination events.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def saving(self, user: FactoryUser) -> None:  # noqa: ARG002
        """Pause a write inside the model's ordinary event pipeline.

        Parameters
        ----------
        user : FactoryUser
            Model about to persist.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.entered.set()
        await self.release.wait()

def _indexed_email(index: int) -> dict[str, Any]:
    """Generate addresses from the factory-local sequence index.

    Parameters
    ----------
    index : int
        Zero-based position across generation calls.

    Returns
    -------
    dict[str, Any]
        Deterministic email for this position.
    """
    return {"email": f"user{index + 1}@example.test"}

def _mutating_state(attributes: dict[str, Any]) -> dict[str, Any]:
    """Mutate only the callback's defensive copy of current attributes.

    Parameters
    ----------
    attributes : dict[str, Any]
        Isolated values supplied to the state callback.

    Returns
    -------
    dict[str, Any]
        Name update; incidental input mutations are deliberately omitted.
    """
    attributes["profile"]["tags"].append("incidental")
    return {"name": f"{attributes['name']} changed"}

def _run_locale_probe(mode: str) -> dict[str, object]:
    """Check factory construction before app startup in a fresh interpreter.

    Parameters
    ----------
    mode : str
        Whether the process has no application or an unconfigured application.

    Returns
    -------
    dict[str, object]
        Provider locale and the application's lifecycle observations.
    """
    source = """
import json
import sys
from pathlib import Path
from database.factories.user_factory import UserFactory
from orionis.foundation.application import Application

app = None
if sys.argv[1] == "unconfigured":
    app = Application(base_path=Path.cwd())
before = Application.current()
factory = UserFactory(seed=42)
after = Application.current()
print(json.dumps({
    "locales": factory.fake.locales,
    "before_missing": before is None,
    "after_missing": after is None,
    "same_instance": before is after,
    "booted": after.isBooted if after is not None else False,
}))
"""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-B", "-c", source, mode],
        cwd=Path(__file__).resolve().parents[3],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return json.loads(result.stdout)

class TestFactoryGeneration(TestCase):
    """Test public generation without requiring database resolution."""

    def testApplicationFactoryMakesTheRealSkeletonUser(self) -> None:
        """Generate active and named inactive users with the shipped factory.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = ApplicationUserFactory(seed=42)
        user = factory.make()
        self.assertIsInstance(user, User)
        self.assertTrue(user.active)
        self.assertFalse(user._exists)
        self.assertIsNone(user.password)
        self.assertFalse(factory.inactive().make().active)

    def testDefinitionUsesFakerAndOmitsAutomaticColumns(self) -> None:
        """Keep explicit definitions independent of database metadata defaults.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        attributes = UserFactory(seed=42).definition()
        self.assertIsInstance(attributes["name"], str)
        self.assertIn("@", attributes["email"])
        self.assertEqual(
            set(attributes),
            {"name", "email", "active", "profile"},
        )

    def testMakeReturnsUnsavedModelWithCastsAndMutators(self) -> None:
        """Use Model's supported constructor and normal assignment pipeline.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        user = UserFactory().make(
            email="  OVERRIDE@EXAMPLE.TEST  ",
            active="false",
            profile='{"tags": ["cast"]}',
        )
        self.assertIsInstance(user, FactoryUser)
        self.assertFalse(user._exists)
        self.assertIsNone(user.id)
        self.assertIsNone(user.created_at)
        self.assertIsNone(user.tier)
        self.assertEqual(user.email, "override@example.test")
        self.assertIs(user.active, False)
        self.assertEqual(user.profile, {"tags": ["cast"]})

    def testCountReturnsFrameworkCollectionForMultipleModels(self) -> None:
        """Return a single model for one and Orionis Collection otherwise.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = UserFactory(seed=42)
        self.assertIs(factory.count(3), factory)
        users = factory.make()
        self.assertIsInstance(users, Collection)
        self.assertEqual(len(users), 3)
        self.assertTrue(all(isinstance(user, FactoryUser) for user in users))
        self.assertIsInstance(factory.count(1).make(), FactoryUser)

    def testZeroCountSkipsDefinitionsAndReturnsEmptyCollection(self) -> None:
        """Avoid generating values for an explicitly empty batch.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = _SharedDefinitionFactory().count(0)
        users = factory.make()
        self.assertIsInstance(users, Collection)
        self.assertEqual(len(users), 0)
        self.assertEqual(factory.calls, 0)

    def testStatesAndSequencesHaveDocumentedOverridePrecedence(self) -> None:
        """Apply definition, ordered states, sequence, then explicit values.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = (
            _SharedDefinitionFactory()
            .state({"name": "state one", "active": False})
            .state(lambda values: {"name": f"{values['name']} state two"})
            .sequence(Sequence({"name": "sequence"}))
        )
        self.assertEqual(factory.make().name, "sequence")
        self.assertEqual(factory.make(name="explicit").name, "explicit")
        self.assertFalse(factory.make().active)
        self.assertEqual(factory.attributes["name"], "Original")

    def testCallableStatesObservePreviouslyAppliedStates(self) -> None:
        """Expose the current attributes to each state in registration order.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        user = (
            UserFactory()
            .state({"name": "First"})
            .state(lambda values: {"name": f"{values['name']} Second"})
            .make()
        )
        self.assertEqual(user.name, "First Second")

    def testNamedStatesUseOrdinaryFluentMethods(self) -> None:
        """Allow reusable domain names without a decorator or registry.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = UserFactory()
        self.assertIs(factory.inactive(), factory)
        self.assertFalse(factory.make().active)
        self.assertTrue(UserFactory().make().active)

    def testNestedStateMappingsAreIsolatedFromCallersAndModels(self) -> None:
        """Snapshot input state and copy nested values for every generated model.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        state = {"profile": {"tags": ["original"]}}
        factory = UserFactory().state(state).count(2)
        state["profile"]["tags"].append("outside")
        users = factory.make()
        users[0].profile["tags"].append("first model")
        self.assertEqual(users[1].profile, {"tags": ["original"]})
        self.assertEqual(
            factory.count(1).make().profile,
            {"tags": ["original"]},
        )

    def testDefinitionAndCallableStateInputsCannotLeakMutations(self) -> None:
        """Protect shared definition mappings from callbacks and result models.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = _SharedDefinitionFactory().state(_mutating_state)
        user = factory.make()
        self.assertEqual(user.name, "Original changed")
        self.assertEqual(factory.attributes["profile"], {"tags": []})
        self.assertEqual(user.profile, {"tags": []})
        user.profile["tags"].append("model")
        self.assertEqual(factory.make().profile, {"tags": []})

    def testOverrideMappingsRemainIndependentAcrossBatchItems(self) -> None:
        """Copy explicit nested overrides separately for every generated item.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        profile = {"tags": ["input"]}
        users = UserFactory().count(2).make(profile=profile)
        users[0].profile["tags"].append("changed")
        self.assertEqual(profile, {"tags": ["input"]})
        self.assertEqual(users[1].profile, profile)

    def testFlatDefinitionsRemainDetachedFromCallersAndModels(self) -> None:
        """Detach reused scalar-only definitions without retaining item changes.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = _SharedDefinitionFactory().count(2)
        factory.attributes = {
            "name": "Original",
            "email": "flat@example.test",
            "active": True,
        }
        users = factory.make()
        users[0].name = "Changed"
        self.assertEqual(users[1].name, "Original")
        self.assertEqual(factory.attributes["name"], "Original")

    def testNestedCyclesAndAliasesRemainIndependentBetweenItems(self) -> None:
        """Preserve cyclic graphs and shared references inside each copied item.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        shared = []
        profile = {"first": shared, "second": shared}
        profile["self"] = profile
        users = _SharedDefinitionFactory().count(2).make(profile=profile)
        for user in users:
            self.assertIs(user.profile["self"], user.profile)
            self.assertIs(user.profile["first"], user.profile["second"])
        users[0].profile["first"].append("changed")
        self.assertEqual(shared, [])
        self.assertEqual(users[1].profile["first"], [])

    def testOverridesDoNotPersistIntoLaterCalls(self) -> None:
        """Scope explicit overrides to a single generation call.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = _SharedDefinitionFactory()
        self.assertEqual(factory.make(name="temporary").name, "temporary")
        self.assertEqual(factory.make().name, "Original")

    def testIterMakeGeneratesOnlyConsumedItems(self) -> None:
        """Generate progressively and release the instance when closed early.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = _SharedDefinitionFactory().count(10000)
        iterator = factory.iterMake()
        self.assertEqual(factory.calls, 0)
        self.assertIsInstance(next(iterator), FactoryUser)
        self.assertEqual(factory.calls, 1)
        iterator.close()
        self.assertIsInstance(factory.count(1).make(), FactoryUser)
        self.assertEqual(factory.calls, 2)

    def testPartiallyConsumedIteratorGuardsMutableConfiguration(self) -> None:
        """Reject operations sharing active mutable generation state.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = UserFactory().count(2)
        iterator = factory.iterMake()
        next(iterator)
        try:
            operations = (
                factory.make,
                lambda: factory.count(1),
                lambda: factory.state({"active": False}),
                lambda: factory.sequence(Sequence(_indexed_email)),
                factory.clearUnique,
            )
            for operation in operations:
                with (
                    self.subTest(operation=operation),
                    self.assertRaises(FactoryConcurrencyException),
                ):
                    operation()
        finally:
            iterator.close()
        self.assertIsInstance(factory.count(1).make(), FactoryUser)

    def testSeedReproducesIndependentFactoryStreams(self) -> None:
        """Keep same-seed factories deterministic when consumption interleaves.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        first = UserFactory(seed=42)
        second = UserFactory(seed=42)
        noise = UserFactory(seed=17)
        for _ in range(5):
            expected = first.definition()
            noise.definition()
            self.assertEqual(second.definition(), expected)
        self.assertIsNot(first.fake, second.fake)
        self.assertIsNot(first.fake.random, second.fake.random)

    def testDifferentSeedsProduceDifferentStreams(self) -> None:
        """Distinguish seeds without depending on version-specific Faker values.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        first = UserFactory(seed=42).count(5).make()
        second = UserFactory(seed=43).count(5).make()
        self.assertNotEqual(
            [user.email for user in first],
            [user.email for user in second],
        )

    def testExplicitLocaleMatchesFakersInstanceConfiguration(self) -> None:
        """Honor explicitly supported provider locales and seeded values.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        for locale in ("en_US", "es_CO"):
            with self.subTest(locale=locale):
                provider = Faker(locale)
                provider.seed_instance(42)
                factory = UserFactory(locale=locale, seed=42)
                self.assertEqual(factory.fake.locales, [locale])
                self.assertEqual(factory.make().name, provider.name())

    def testUniquePersistsAcrossBatchesAndCanBeCleared(self) -> None:
        """Retain unique history until the caller explicitly clears it.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = _ConstantUniqueFactory(seed=42)
        self.assertEqual(factory.make().email, "only@example.test")
        with self.assertRaises(UniquenessException):
            factory.make()
        factory.clearUnique()
        self.assertEqual(factory.make().email, "only@example.test")

    def testUniqueStateIsIndependentBetweenFactories(self) -> None:
        """Allow independent unique domains and uniqueness within one batch.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        first = _ConstantUniqueFactory(seed=42).make()
        second = _ConstantUniqueFactory(seed=42).make()
        self.assertEqual(first.email, second.email)
        users = UserFactory(seed=42).count(100).make()
        self.assertEqual(len({user.email for user in users}), 100)

    def testMassAssignmentPreservesFillableAndInternalProtection(self) -> None:
        """Reject guarded fields, arbitrary columns, and ORM internals.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = UserFactory()
        for field in ("tier", "id", "created_at", "_exists", "unknown"):
            with (
                self.subTest(field=field),
                self.assertRaises(MassAssignmentException),
            ):
                factory.make(**{field: "forbidden"})
        self.assertIsInstance(factory.make(), FactoryUser)

    async def testNativeContainerInjectsConstructorDependencies(self) -> None:
        """Build factories through the same DI primitive as seeders.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        container = object.__new__(Container)
        Container.__init__(container)
        service = _FactoryDependency()
        container.instance(None, service)
        factory = await container.build(_InjectedFactory, seed=42)
        self.assertIs(factory.dependency, service)
        user = factory.make()
        self.assertEqual(user.name, "Injected dependency")
        self.assertEqual(user.email, UserFactory(seed=42).make().email)

class TestFactoryLocale(TestCase):
    """Resolve the application locale without changing its startup lifecycle."""

    def setUp(self) -> None:
        """Restore the real application's locale after each test.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.app = Application.current()
        self.assertIsNotNone(self.app)
        self.addCleanup(self.app.config, "app.locale", self.app.config("app.locale"))

    def testDefaultUsesCurrentApplicationLocaleAtConstruction(self) -> None:
        """Read current config for new factories and retain existing providers.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.app.config("app.locale", "es_CO")
        first = UserFactory(seed=42)
        self.assertEqual(first.fake.locales, ["es_CO"])
        self.assertEqual(UserFactory(locale=None).fake.locales, ["es_CO"])
        self.app.config("app.locale", "fr_FR")
        self.assertEqual(UserFactory().fake.locales, ["fr_FR"])
        self.assertEqual(first.fake.locales, ["es_CO"])

    def testApplicationLocaleAcceptsLanguageAndRegionalForms(self) -> None:
        """Normalize application language codes, hyphens, and encoding suffixes.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        for locale, expected in (
            ("en", "en_US"),
            ("es", "es_ES"),
            ("es-CO", "es_CO"),
            ("es_CO.UTF-8", "es_CO"),
        ):
            with self.subTest(locale=locale):
                self.app.config("app.locale", locale)
                self.assertEqual(UserFactory().fake.locales, [expected])

    def testUnsupportedOrMissingApplicationLocaleFallsBackToEnglish(self) -> None:
        """Use English even when the translation fallback is another language.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.addCleanup(
            self.app.config,
            "app.fallback_locale",
            self.app.config("app.fallback_locale"),
        )
        self.app.config("app.fallback_locale", "fr_FR")
        for locale in ("not_a_real_locale", None, "", " ", [], 1):
            with self.subTest(locale=locale):
                self.app.config("app.locale", locale)
                factory = UserFactory(seed=42)
                self.assertEqual(factory.fake.locales, ["en_US"])
                self.assertEqual(
                    factory.definition(),
                    UserFactory(locale="en_US", seed=42).definition(),
                )

    def testExplicitLocaleTakesPriorityOverApplicationConfiguration(self) -> None:
        """Allow a caller to select a supported locale for one factory.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.app.config("app.locale", "es_CO")
        factory = UserFactory(locale="fr_FR", seed=42)
        self.assertEqual(factory.fake.locales, ["fr_FR"])
        self.assertEqual(self.app.config("app.locale"), "es_CO")

    def testUnsupportedExplicitLocalePreservesSeedWithEnglishFallback(self) -> None:
        """Fallback without using the app locale or changing seeded streams.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.app.config("app.locale", "es_CO")
        factory = UserFactory(locale="not_a_real_locale", seed=42)
        expected = UserFactory(locale="en_US", seed=42)
        self.assertEqual(factory.fake.locales, ["en_US"])
        for _ in range(5):
            self.assertEqual(factory.definition(), expected.definition())

    def testStandaloneFactoryDoesNotInstantiateAnApplication(self) -> None:
        """Keep standalone generation from claiming the application's base path.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        result = _run_locale_probe("absent")
        self.assertEqual(result["locales"], ["en_US"])
        self.assertTrue(result["before_missing"])
        self.assertTrue(result["after_missing"])
        self.assertFalse(result["booted"])

    def testUnconfiguredApplicationIsNotBootedOrReplaced(self) -> None:
        """Keep an existing application's initialization under caller control.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        result = _run_locale_probe("unconfigured")
        self.assertEqual(result["locales"], ["en_US"])
        self.assertFalse(result["before_missing"])
        self.assertFalse(result["after_missing"])
        self.assertTrue(result["same_instance"])
        self.assertFalse(result["booted"])

    async def testApplicationBuildUsesConfiguredLocale(self) -> None:
        """Use identical locale resolution through native container construction.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.app.config("app.locale", "es_CO")
        factory = await self.app.build(UserFactory, seed=42)
        self.assertEqual(factory.fake.locales, ["es_CO"])
        self.assertEqual(factory.definition(), UserFactory(seed=42).definition())

class TestFactoryValidation(TestCase):
    """Verify deliberate configuration errors and diagnostic boundaries."""

    def testAbstractAndInvalidModelsFailEarly(self) -> None:
        """Require a concrete Orionis model with compiled metadata.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        with self.assertRaises(FactoryConfigurationException):
            Factory()
        for model in (None, Model, object, str, FactoryUser({})):
            factory_type = type(
                "InvalidModelFactory",
                (UserFactory,),
                {
                    "model": model,
                },
            )
            with (
                self.subTest(model=model),
                self.assertRaises(FactoryConfigurationException),
            ):
                factory_type()

    def testMissingAsyncAndNoncallableDefinitionsFailEarly(self) -> None:
        """Reject unsupported definition methods during construction.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        noncallable_type = type(
            "NoncallableFactory",
            (UserFactory,),
            {
                "definition": None,
            },
        )
        for factory_type in (
            _MissingDefinitionFactory,
            _AsyncDefinitionFactory,
            noncallable_type,
        ):
            with (
                self.subTest(factory_type=factory_type),
                self.assertRaises(FactoryDefinitionException),
            ):
                factory_type()

    def testDefinitionMustReturnDictionaryWithStringKeys(self) -> None:
        """Reject invalid raw definition shapes before model construction.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = _SharedDefinitionFactory()
        for value in (None, [], "attributes", {1: "non-string key"}):
            factory.attributes = value
            with (
                self.subTest(value=value),
                self.assertRaises(FactoryDefinitionException),
            ):
                factory.make()

    def testCountRejectsNegativeBooleanAndNonIntegerValues(self) -> None:
        """Keep count's integer contract explicit even for Python booleans.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        for count in (-1, True, False, 1.5, "2", None):
            with (
                self.subTest(count=count),
                self.assertRaises(FactoryConfigurationException),
            ):
                UserFactory().count(count)

    def testLocaleAndSeedValidationProvideFactoryErrors(self) -> None:
        """Reject invalid explicit locale types, empty strings, and seed values.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        for locale in ("", " ", [], 1):
            with (
                self.subTest(locale=locale),
                self.assertRaises(FactoryConfigurationException),
            ):
                UserFactory(locale=locale)
        for seed in (True, 1.5, "42", []):
            with (
                self.subTest(seed=seed),
                self.assertRaises(FactoryConfigurationException),
            ):
                UserFactory(seed=seed)

    def testInvalidStatesAndSequencesFailAtRegistration(self) -> None:
        """Validate configuration before a potentially large generation run.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        for state in (None, [], "state", 42):
            with (
                self.subTest(state=state),
                self.assertRaises(FactoryConfigurationException),
            ):
                UserFactory().state(state)
        for entries in ((), (None,), ([],), ("state",)):
            with (
                self.subTest(entries=entries),
                self.assertRaises(FactoryConfigurationException),
            ):
                Sequence(*entries)
        with self.assertRaises(FactoryConfigurationException):
            UserFactory().sequence({"name": "invalid"})

    def testInvalidStateAndSequenceResultsRaiseDefinitionErrors(self) -> None:
        """Reject callable results before they reach mass assignment.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = UserFactory().state(lambda _attributes: [])
        with self.assertRaises(FactoryDefinitionException):
            factory.make()
        factory = UserFactory().sequence(Sequence(lambda _index: {1: "value"}))
        with self.assertRaises(FactoryDefinitionException):
            factory.make()

class TestFactoryPersistence(TestCase):
    """Exercise saves and concurrent factories against a real SQLite file."""

    async def asyncSetUp(self) -> None:
        """Create private file-backed database state for each test.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        self.directory = TemporaryDirectory(prefix="orionis-factories-")
        self.addCleanup(self.directory.cleanup)
        database = str(Path(self.directory.name) / "factories.sqlite")
        self.manager = ConnectionManager(_DatabaseConfig(database))
        self.previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager)
        self.addAsyncCleanup(self.manager.disconnect)
        self.addCleanup(ConnectionResolver.setManager, self.previous_manager)
        self.addCleanup(FactoryUser.flushEvents)
        await self.manager.connection().createTable(FactoryUser.__meta__.table)

    async def testApplicationFactoryPersistsUserWithAnExplicitPasswordHash(
        self,
    ) -> None:
        """Use the shipped User schema and Orionis hasher without bypasses.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        await self.manager.connection().createTable(User.__meta__.table)
        hasher = Argon2Hasher(memory=8, threads=1, time=1)
        password_hash = await hasher.make("factory-fixture-password")
        user = (
            await ApplicationUserFactory(seed=42)
            .inactive()
            .create(
                password=password_hash,
            )
        )
        stored = await User.find(user.id)
        self.assertIsInstance(stored, User)
        self.assertTrue(user._exists)
        self.assertFalse(stored.active)
        self.assertEqual(stored.email, user.email)
        self.assertEqual(stored.password, password_hash)
        self.assertTrue(
            await hasher.check("factory-fixture-password", stored.password),
        )
        self.assertIsInstance(stored.created_at, datetime)
        self.assertNotIn("password", stored.toDict())

    async def testCreatePersistsUsingModelSave(self) -> None:
        """Assign keys and timestamps while leaving server defaults to SQL.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        user = await UserFactory(seed=42).create(
            name="Persisted",
            email="  PERSISTED@EXAMPLE.TEST  ",
        )
        self.assertIsInstance(user, FactoryUser)
        self.assertTrue(user._exists)
        self.assertIsInstance(user.id, int)
        self.assertIsInstance(user.created_at, datetime)
        self.assertIsInstance(user.updated_at, datetime)
        stored = await FactoryUser.find(user.id)
        self.assertEqual(stored.name, "Persisted")
        self.assertEqual(stored.email, "persisted@example.test")
        self.assertEqual(stored.tier, "member")
        self.assertTrue(stored.active)
        self.assertEqual(stored.profile, {"tags": []})

    async def testMakeDoesNotWriteOrFirePersistenceEvents(self) -> None:
        """Leave persistence events and the database untouched when making.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        observer = _LifecycleObserver()
        FactoryUser.observe(observer)
        UserFactory().count(3).make()
        self.assertEqual(await FactoryUser.query().count(), 0)
        self.assertEqual(observer.events, [])

    async def testCreateRunsNativeSyncAndAsyncModelEvents(self) -> None:
        """Preserve model event ordering and before-save mutations.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        observer = _LifecycleObserver()
        FactoryUser.observe(observer)
        user = await UserFactory().create()
        self.assertEqual(
            observer.events,
            [
                ("saving", False),
                ("creating", False),
                ("created", True),
                ("saved", True),
            ],
        )
        stored = await FactoryUser.find(user.id)
        self.assertEqual(stored.name, "Created by observer")

    async def testCreateBatchReturnsCollectionAndRespectsCount(self) -> None:
        """Persist every item through normal per-model semantics.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        users = await UserFactory().count(3).sequence(Sequence(_indexed_email)).create()
        self.assertIsInstance(users, Collection)
        self.assertEqual(len(users), 3)
        self.assertTrue(all(user._exists for user in users))
        self.assertEqual(await FactoryUser.query().count(), 3)

    async def testEmptyCreateSkipsDefinitionsAndWrites(self) -> None:
        """Return an empty framework collection for zero persistence count.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = _SharedDefinitionFactory().count(0)
        users = await factory.create()
        self.assertIsInstance(users, Collection)
        self.assertEqual(len(users), 0)
        self.assertEqual(factory.calls, 0)
        self.assertEqual(await FactoryUser.query().count(), 0)

    async def testIterCreatePersistsOnlyConsumedModels(self) -> None:
        """Allow large datasets to be produced without an eager model list.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = UserFactory().count(10000)
        iterator = factory.iterCreate()
        self.assertEqual(await FactoryUser.query().count(), 0)
        user = await anext(iterator)
        self.assertTrue(user._exists)
        self.assertEqual(await FactoryUser.query().count(), 1)
        await iterator.aclose()
        await factory.count(1).create()
        self.assertEqual(await FactoryUser.query().count(), 2)

    async def testEventVetoRaisesFactoryPersistenceError(self) -> None:
        """Surface a false save instead of reporting an unsaved model as created.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        FactoryUser.registerEvent("creating", lambda _user: False)
        factory = UserFactory()
        with self.assertRaises(FactoryPersistenceException):
            await factory.create()
        self.assertEqual(await FactoryUser.query().count(), 0)
        FactoryUser.flushEvents()
        self.assertTrue((await factory.create())._exists)

    async def testDatabaseErrorsPreserveOrmExceptionAndReleaseFactory(self) -> None:
        """Retain native persistence diagnostics and allow subsequent reuse.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = UserFactory()
        await factory.create(email="duplicate@example.test")
        with self.assertRaises(QueryException):
            await factory.create(email="duplicate@example.test")
        await factory.create(email="recovered@example.test")
        self.assertEqual(await FactoryUser.query().count(), 2)

    async def testBatchDoesNotSilentlyAddAnImplicitTransaction(self) -> None:
        """Keep successful prior saves when a later batch item fails.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        factory = (
            UserFactory()
            .count(2)
            .sequence(
                Sequence(
                    {
                        "email": "same@example.test",
                    },
                ),
            )
        )
        with self.assertRaises(QueryException):
            await factory.create()
        self.assertEqual(await FactoryUser.query().count(), 1)

    async def testCallerTransactionCanRollBackFactoryBatch(self) -> None:
        """Participate in the ORM's existing transaction ownership context.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        connection = self.manager.connection()
        await connection.begin()
        try:
            await UserFactory().count(3).create()
        finally:
            await connection.rollback()
        self.assertEqual(await FactoryUser.query().count(), 0)

    async def testIndependentFactoriesPersistConcurrentlyWithoutSeedInterference(
        self,
    ) -> None:
        """Keep each seeded stream deterministic across interleaved async saves.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        first = UserFactory(seed=42).count(5)
        second = UserFactory(seed=42).count(5)
        first.sequence(
            Sequence(
                lambda index: {
                    "email": f"first{index}@example.test",
                },
            ),
        )
        second.sequence(
            Sequence(
                lambda index: {
                    "email": f"second{index}@example.test",
                },
            ),
        )
        first_users, second_users = await asyncio.gather(
            first.create(),
            second.create(),
        )
        expected = UserFactory(seed=42).count(5).make()
        self.assertEqual(
            [user.name for user in first_users],
            [user.name for user in expected],
        )
        self.assertEqual(
            [user.name for user in second_users],
            [user.name for user in expected],
        )
        self.assertEqual(await FactoryUser.query().count(), 10)

    async def testSharedFactoryRejectsConcurrentCallsDuringSave(self) -> None:
        """Acquire the shared-instance guard before the first model save await.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        observer = _PauseObserver()
        FactoryUser.observe(observer)
        factory = UserFactory(seed=42)
        task = asyncio.create_task(factory.create())
        try:
            await asyncio.wait_for(observer.entered.wait(), timeout=5)
            with self.assertRaises(FactoryConcurrencyException):
                await factory.create()
            with self.assertRaises(FactoryConcurrencyException):
                factory.make()
            with self.assertRaises(FactoryConcurrencyException):
                factory.state({"name": "changed during save"})
        finally:
            observer.release.set()
            await task
        await factory.create()
        self.assertEqual(await FactoryUser.query().count(), 2)

    async def testCancelledCreateReleasesSharedInstanceGuard(self) -> None:
        """Restore generation availability even when an awaited save is cancelled.

        Returns
        -------
        None
            Verify the behavior described above.
        """
        observer = _PauseObserver()
        FactoryUser.observe(observer)
        factory = UserFactory(seed=42)
        task = asyncio.create_task(factory.create())
        try:
            await asyncio.wait_for(observer.entered.wait(), timeout=5)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        finally:
            observer.release.set()
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(await FactoryUser.query().count(), 0)
        self.assertTrue((await factory.create())._exists)
