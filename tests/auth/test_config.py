from orionis.foundation.config.auth import (
    Auth,
    Guards,
    Identity,
    SessionAuth,
    Tokens,
)
from orionis.foundation.core_config import CORE_CONFIG
from orionis.test import TestCase

class TestGuardsEnum(TestCase):
    """Validate the guards shipped with the framework."""

    def testDeclaresExactlyTheImplementedGuards(self) -> None:
        """Validates the closed set of guards of this version.

        JWT, OAuth and the rest are deliberately out of scope.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(
            {member.value for member in Guards}, {"session", "token"},
        )

class TestIdentityConfiguration(TestCase):
    """Validate where the application identity is declared."""

    def testProvidesUsableDefaults(self) -> None:
        """Validates the out of the box configuration.

        A fresh application authenticates by email and password.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        identity = Identity()
        self.assertEqual(identity.username, "email")
        self.assertEqual(set(identity.toDict()), {"model", "username"})
        self.assertIn(".", identity.model)

    def testRejectsNonStringOptions(self) -> None:
        """Validates the type guards of the section.

        Every option names an attribute or a class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Identity(username=42)

    def testRejectsEmptyOptions(self) -> None:
        """Validates that no option may be blank.

        A blank attribute name would silently break every lookup.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Identity(username="   ")

    def testRejectsAModelWithoutADottedPath(self) -> None:
        """Validates the shape of the identity model path.

        The module and the class name must be separable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Identity(model="User")

class TestSessionAuthConfiguration(TestCase):
    """Validate the options of the session guard."""

    def testProvidesUsableDefaults(self) -> None:
        """Validates the default session key and redirect behaviour.

        Without an explicit target, guests get the standard error page.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        session = SessionAuth()
        self.assertEqual(session.key, "_auth_identifier")
        self.assertIsNone(session.redirect_to)
        self.assertEqual(session.home, "/home")

    def testAcceptsARedirectTarget(self) -> None:
        """Validates the browser friendly rejection setting.

        Applications with a login page point at it here.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(SessionAuth(redirect_to="/login").redirect_to, "/login")

    def testAcceptsAHomeTarget(self) -> None:
        """Validates the destination used once the login succeeds.

        Applications landing somewhere other than ``/home`` point at it here.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(SessionAuth(home="/dashboard").home, "/dashboard")

    def testRejectsInvalidOptions(self) -> None:
        """Validates the type and value guards of the section.

        Misconfiguration must fail at boot, not on the first request.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            SessionAuth(key=1)
        with self.assertRaises(ValueError):
            SessionAuth(key="")
        with self.assertRaises(TypeError):
            SessionAuth(redirect_to=1)
        with self.assertRaises(TypeError):
            SessionAuth(home=1)
        with self.assertRaises(ValueError):
            SessionAuth(home="")

class TestTokensConfiguration(TestCase):
    """Validate the options of the personal access token guard."""

    def testProvidesUsableDefaults(self) -> None:
        """Validates the default token settings.

        Tokens never expire on their own unless configured to.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        tokens = Tokens()
        self.assertEqual(tokens.table, "personal_access_tokens")
        self.assertIsNone(tokens.expiration)
        self.assertEqual(tokens.secret_bytes, 40)

    def testRejectsAnEmptyTable(self) -> None:
        """Validates that the token table must be named.

        An empty name would produce invalid SQL.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Tokens(table="  ")

    def testRejectsANonPositiveExpiration(self) -> None:
        """Validates the lifetime guard.

        A zero or negative lifetime would issue dead tokens.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Tokens(expiration=0)
        with self.assertRaises(TypeError):
            Tokens(expiration=True)

    def testRejectsAnUnsafeSecretLength(self) -> None:
        """Validates the entropy guard of generated secrets.

        Too little entropy would make tokens guessable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Tokens(secret_bytes=8)
        with self.assertRaises(ValueError):
            Tokens(secret_bytes=1024)

class TestAuthConfiguration(TestCase):
    """Validate the root authentication configuration entity."""

    def testProvidesUsableDefaults(self) -> None:
        """Validates the shape of a default configuration.

        Every section resolves to its typed entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        auth = Auth()
        self.assertEqual(auth.default, "session")
        self.assertIsInstance(auth.identity, Identity)
        self.assertIsInstance(auth.session, SessionAuth)
        self.assertIsInstance(auth.tokens, Tokens)

    def testNormalisesTheDefaultGuard(self) -> None:
        """Validates that guards may be named in several ways.

        Both the enum member and a case insensitive string are accepted.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Auth(default=Guards.TOKEN).default, "token")
        self.assertEqual(Auth(default="TOKEN").default, "token")
        self.assertEqual(Auth(default=" token ").default, "token")

    def testRejectsAnUnknownGuard(self) -> None:
        """Validates the guard whitelist.

        Naming a guard that does not exist must fail at boot.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Auth(default="jwt")
        with self.assertRaises(TypeError):
            Auth(default=1)

    def testCoercesDictionarySections(self) -> None:
        """Validates that plain dictionaries become typed entities.

        Configuration files are free to use dictionaries.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        auth = Auth(
            identity={"username": "login"},
            session={"key": "_uid"},
            tokens={"expiration": 30},
        )
        self.assertEqual(auth.identity.username, "login")
        self.assertEqual(auth.session.key, "_uid")
        self.assertEqual(auth.tokens.expiration, 30)

    def testRejectsSectionsOfTheWrongType(self) -> None:
        """Validates the type guard of every section.

        A misplaced value must not reach the services.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Auth(identity="app.models.user.User")

    def testIsSerialisable(self) -> None:
        """Validates that the entity can be flattened for the container.

        The application stores configuration as plain dictionaries.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = Auth().toDict()
        self.assertEqual(
            sorted(payload),
            ["default", "identity", "passwords", "remember", "session", "tokens"],
        )
        self.assertEqual(payload["tokens"]["table"], "personal_access_tokens")

    def testIsRegisteredInTheCoreConfiguration(self) -> None:
        """Validates that the section is available to every application.

        Services read their options through ``app.config('auth.*')``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("auth", CORE_CONFIG)
        self.assertIn("identity", CORE_CONFIG["auth"])
