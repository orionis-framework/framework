from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from orionis.foundation.config.hashing.entities.hashing import Hashing
from orionis.hashing.contracts.hash_manager import IHashManager
from orionis.hashing.contracts.hasher import IHasher
from orionis.hashing.exceptions import HashDriverNotSupportedException
from orionis.hashing.hash_manager import HashManager
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.test import TestCase

# Cheap cost parameters shared by every test in this module. Argon2
# requires memory_cost >= 8 * parallelism, so 32 KiB leaves room for the
# tests raising the parallelism to two lanes.
_ARGON2_OPTIONS: dict[str, int] = {"memory": 32, "threads": 1, "time": 1}
_BCRYPT_OPTIONS: dict[str, int] = {"rounds": 4}


class _StubApp:
    """Application double returning a fixed hashing configuration."""

    __slots__ = ("requested", "section")

    def __init__(self, section: object) -> None:
        """
        Store the configuration section handed to the manager.

        Parameters
        ----------
        section : object
            Value returned for the ``hashing`` configuration key.

        Returns
        -------
        None
        """
        self.section = section
        self.requested: list[str] = []

    def config(self, key: str) -> object:
        """
        Return the stored configuration section.

        Parameters
        ----------
        key : str
            Configuration key requested by the manager.

        Returns
        -------
        object
            The stored section, whatever key is requested.
        """
        self.requested.append(key)
        return self.section


def build_config(driver: str = "argon2") -> Hashing:
    """
    Build a hashing configuration entity with cheap cost parameters.

    Parameters
    ----------
    driver : str
        Default driver written into the configuration.

    Returns
    -------
    Hashing
        Configuration entity ready to be handed to the manager.
    """
    return Hashing(
        driver=driver,
        argon2=dict(_ARGON2_OPTIONS),
        bcrypt=dict(_BCRYPT_OPTIONS),
    )


def build_manager(driver: str = "argon2", *, as_entity: bool = False) -> HashManager:
    """
    Build a manager backed by the application double.

    Parameters
    ----------
    driver : str
        Default driver used by the manager.
    as_entity : bool
        Whether the application exposes the configuration as a typed
        entity instead of a plain dictionary.

    Returns
    -------
    HashManager
        Manager configured with cheap cost parameters.
    """
    config = build_config(driver)
    section = config if as_entity else asdict(config)
    return HashManager(_StubApp(section))  # type: ignore[arg-type]


class TestHashManagerLayout(TestCase):

    def testImplementsTheManagerContract(self) -> None:
        """
        Register the manager as an implementation of its contract.

        Validates the binding resolved through the Hash facade.
        """
        self.assertIsInstance(build_manager(), IHashManager)

    def testDeclaresTheExpectedSlots(self) -> None:
        """
        Declare the state of the manager as explicit slots.

        Validates the memory layout required by the framework
        conventions.
        """
        self.assertEqual(
            HashManager.__dict__.get("__slots__"),
            ("_config", "_default", "_drivers"),
        )

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep instances free of an attribute dictionary.

        Validates that the empty slots of the contracts propagate to the
        manager.
        """
        self.assertFalse(hasattr(build_manager(), "__dict__"))


class TestHashManagerConstruction(TestCase):

    def testReadsOnlyTheHashingSection(self) -> None:
        """
        Read the hashing section from the application configuration.

        Validates that the manager never reaches for unrelated keys.
        """
        app = _StubApp(asdict(build_config()))
        HashManager(app)  # type: ignore[arg-type]
        self.assertEqual(app.requested, ["hashing"])

    def testAcceptsAConfigurationDictionary(self) -> None:
        """
        Accept a plain dictionary and convert it into an entity.

        Validates the branch taken when the configuration comes from the
        compiled application state.
        """
        manager = build_manager()
        self.assertEqual(manager.getDefaultDriver(), "argon2")
        self.assertIsInstance(manager.driver(), Argon2Hasher)

    def testAcceptsAnAlreadyBuiltConfigurationEntity(self) -> None:
        """
        Accept a typed entity without rebuilding it.

        Validates the branch taken when the application exposes the
        configuration as an entity.
        """
        manager = build_manager(as_entity=True)
        self.assertEqual(manager.getDefaultDriver(), "argon2")
        self.assertIsInstance(manager.driver(), Argon2Hasher)

    def testUsesTheConfiguredDriverAsDefault(self) -> None:
        """
        Promote the configured driver to the default one.

        Validates that the application chooses the algorithm without
        touching any call site.
        """
        manager = build_manager("bcrypt")
        self.assertEqual(manager.getDefaultDriver(), "bcrypt")
        self.assertIsInstance(manager.driver(), BcryptHasher)

    def testMissingSectionFallsBackToTheEntityDefaults(self) -> None:
        """
        Fall back to the entity defaults when the section is absent.

        Validates the guard covering an application whose configuration
        does not declare a hashing section, since `config()` resolves an
        unknown key to None.
        """
        expected = str(Hashing().driver)
        for section in (None, {}):
            manager = HashManager(_StubApp(section))  # type: ignore[arg-type]
            self.assertEqual(manager.getDefaultDriver(), expected)
            self.assertIsInstance(manager.driver(), IHasher)


class TestHashManagerDriverResolution(TestCase):

    def testResolvesTheDefaultDriverWhenNoNameIsGiven(self) -> None:
        """
        Resolve the configured driver when no name is provided.

        Validates the resolution used by every delegated operation.
        """
        self.assertIsInstance(build_manager().driver(), Argon2Hasher)

    def testResolvesADriverByName(self) -> None:
        """
        Resolve a named driver regardless of the configured default.

        Validates the escape hatch used to verify legacy hashes.
        """
        self.assertIsInstance(build_manager().driver("bcrypt"), BcryptHasher)

    def testFallsBackToTheDefaultForAnEmptyName(self) -> None:
        """
        Treat an empty name as a request for the default driver.

        Validates the guard covering an unset configuration value.
        """
        manager = build_manager()
        self.assertIs(manager.driver(""), manager.driver())

    def testCachesEveryResolvedDriver(self) -> None:
        """
        Return the same instance for repeated resolutions.

        Validates that drivers are built once and reused afterwards.
        """
        manager = build_manager()
        self.assertIs(manager.driver(), manager.driver("argon2"))

    def testKeepsOneInstancePerDriverName(self) -> None:
        """
        Keep a separate instance for every requested driver.

        Validates that the cache is keyed by driver name.
        """
        manager = build_manager()
        self.assertIsNot(manager.driver("argon2"), manager.driver("bcrypt"))

    def testRejectsAnUnsupportedDriver(self) -> None:
        """
        Reject a driver name without an implementation.

        Validates that a typo never degrades password storage silently.
        """
        with self.assertRaises(HashDriverNotSupportedException):
            build_manager().driver("md5")

    def testUnsupportedDriverErrorListsTheSupportedOnes(self) -> None:
        """
        Report the rejected name and the supported alternatives.

        Validates that the failure is actionable without a traceback.
        """
        with self.assertRaises(HashDriverNotSupportedException) as captured:
            build_manager().driver("md5")
        message = str(captured.exception)
        self.assertIn("md5", message)
        self.assertIn("argon2", message)
        self.assertIn("bcrypt", message)

    def testAppliesTheConfiguredArgon2Costs(self) -> None:
        """
        Hand the configured Argon2id costs to the driver.

        Validates that the configuration reaches the produced hash.
        """
        hashed = build_manager().make("secret")
        self.assertIn("m=32", hashed)
        self.assertIn("t=1", hashed)
        self.assertIn("p=1", hashed)

    def testAppliesTheConfiguredBcryptRounds(self) -> None:
        """
        Hand the configured bcrypt cost factor to the driver.

        Validates that the configuration reaches the produced hash.
        """
        hashed = build_manager("bcrypt").make("secret")
        self.assertTrue(hashed.startswith("$2b$04$"))


class TestHashManagerDelegation(TestCase):

    def testMakeUsesTheDefaultDriver(self) -> None:
        """
        Produce hashes with the configured default driver.

        Validates that application code never picks an algorithm.
        """
        self.assertTrue(build_manager().make("secret").startswith("$argon2id$"))

    def testMakeAndCheckRoundTrip(self) -> None:
        """
        Verify a value against the hash the manager produced.

        Validates the round trip application code depends on.
        """
        manager = build_manager()
        hashed = manager.make("my-secret-password")
        self.assertTrue(manager.check("my-secret-password", hashed))

    def testCheckRejectsAnotherValue(self) -> None:
        """
        Reject a value that does not match the stored hash.

        Validates that verification is delegated without weakening it.
        """
        manager = build_manager()
        hashed = manager.make("my-secret-password")
        self.assertFalse(manager.check("wrong-password", hashed))

    def testMakeForwardsTheRoundsOverride(self) -> None:
        """
        Forward the per-call cost override to the active driver.

        Validates the tuning hook exposed by the shared contract.
        """
        self.assertIn("t=2", build_manager().make("secret", rounds=2))

    def testMakeForwardsTheMemoryOverride(self) -> None:
        """
        Forward the per-call memory override to the active driver.

        Validates the tuning hook exposed by the shared contract.
        """
        self.assertIn("m=16", build_manager().make("secret", memory=16))

    def testMakeForwardsTheThreadsOverride(self) -> None:
        """
        Forward the per-call parallelism override to the active driver.

        Validates the tuning hook exposed by the shared contract.
        """
        self.assertIn("p=2", build_manager().make("secret", threads=2))

    def testGetAlgorithmReportsTheDefaultDriver(self) -> None:
        """
        Report the algorithm of the configured default driver.

        Validates the identifier surfaced to application code.
        """
        self.assertEqual(build_manager().getAlgorithm(), "argon2id")
        self.assertEqual(build_manager("bcrypt").getAlgorithm(), "bcrypt")

    def testNeedsRehashFollowsTheConfiguration(self) -> None:
        """
        Report a freshly produced hash as up to date.

        Validates that no needless rehash is triggered on login.
        """
        manager = build_manager()
        self.assertFalse(manager.needsRehash(manager.make("secret")))

    def testNeedsRehashDetectsAForeignAlgorithm(self) -> None:
        """
        Report a hash from another driver as outdated.

        Validates the migration path between the shipped drivers.
        """
        manager = build_manager()
        legacy = manager.driver("bcrypt").make("secret")
        self.assertTrue(manager.needsRehash(legacy))

    def testSetRoundsReturnsTheManager(self) -> None:
        """
        Return the manager itself from the fluent setter.

        Validates the chaining style advertised by the contract.
        """
        manager = build_manager()
        self.assertIs(manager.setRounds(2), manager)

    def testSetRoundsUpdatesTheDefaultDriver(self) -> None:
        """
        Apply the new cost to the default driver of the manager.

        Validates that the fluent configuration is delegated.
        """
        manager = build_manager()
        manager.setRounds(2)
        self.assertIn("t=2", manager.make("secret"))

    def testSetRoundsMarksEarlierHashesForRehash(self) -> None:
        """
        Flag hashes produced before the change for regeneration.

        Validates that raising the cost never invalidates stored
        credentials.
        """
        manager = build_manager()
        hashed = manager.make("secret")
        manager.setRounds(2)
        self.assertTrue(manager.needsRehash(hashed))
        self.assertTrue(manager.check("secret", hashed))


class TestHashManagerConcurrency(TestCase):

    def testConcurrentHashingProducesVerifiableHashes(self) -> None:
        """
        Hash from several threads without corrupting the shared cache.

        Validates the concurrency contract declared by the manager: the
        driver cache is written on first resolution and every later
        operation only reads it.
        """
        manager = build_manager()

        def round_trip(index: int) -> bool:
            value = f"secret-{index}"
            return manager.check(value, manager.make(value))

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(round_trip, range(16)))

        self.assertEqual(results, [True] * 16)
