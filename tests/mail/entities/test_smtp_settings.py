from dataclasses import asdict
from orionis.foundation.config.mail.entities.smtp import Smtp
from orionis.mail.entities.smtp_settings import SmtpSettings
from orionis.mail.enums.encryption import MailEncryption
from orionis.mail.exceptions import MailConfigurationException
from orionis.test import TestCase

_CREDENTIAL = "p@ss:word"

class TestSmtpSettings(TestCase):

    def testEmptyUrlUsesFieldsAndDoesNotMutateConfig(self) -> None:
        """
        Resolve the standalone fields when no URL was configured.

        Validates that the supplied configuration is left untouched.
        """
        original = {
            "url": "",
            "host": "smtp.example.com",
            "port": 2525,
            "encryption": "tLs",
            "username": "",
            "password": "",
            "timeout": None,
        }
        settings = SmtpSettings.fromConfig(original)
        self.assertEqual(settings.host, "smtp.example.com")
        self.assertEqual(settings.port, 2525)
        self.assertIs(settings.encryption, MailEncryption.TLS)
        self.assertIsNone(settings.timeout)
        self.assertEqual(original["encryption"], "tLs")

    def testDefaultsToTlsOnThePortUsedForSubmission(self) -> None:
        """
        Apply the submission defaults when only a host is configured.

        Validates that mandatory STARTTLS is the default mode.
        """
        settings = SmtpSettings.fromConfig({"host": "smtp.example.com"})
        self.assertEqual(settings.port, 587)
        self.assertIs(settings.encryption, MailEncryption.TLS)
        self.assertEqual(settings.username, "")
        self.assertIsNone(settings.timeout)

    def testSmtpUrlOverridesHostAndCredentialsAsAUnit(self) -> None:
        """
        Let the URL replace the host and both credentials together.

        Validates that percent-encoded credentials are decoded.
        """
        settings = SmtpSettings.fromConfig(
            {
                "url": "smtp://user%40example.com:p%40ss%3Aword@url.example.com:2526",
                "host": "unused.example.com",
                "port": 587,
                "encryption": "SSL",
                "username": "old",
                "password": "old",
                "timeout": 12,
            },
        )
        self.assertEqual(settings.host, "url.example.com")
        self.assertEqual(settings.port, 2526)
        self.assertIs(settings.encryption, MailEncryption.SSL)
        self.assertEqual(settings.username, "user@example.com")
        self.assertEqual(settings.password, _CREDENTIAL)
        self.assertEqual(settings.timeout, 12)
        self.assertNotIn(_CREDENTIAL, repr(settings))

    def testUrlCredentialsReplaceUnsetIndividualFields(self) -> None:
        """
        Ignore unused field credentials once the URL supplies a pair.

        Validates that the replaced fields are no longer validated.
        """
        settings = SmtpSettings.fromConfig({
            "url": "smtp://user:encoded%40value@smtp.example.com",
            "username": None,
            "password": None,
        })
        self.assertEqual(settings.username, "user")
        self.assertEqual(settings.password, "encoded@value")

    def testSmtpsForcesImplicitTlsAndItsDefaultPort(self) -> None:
        """
        Force implicit TLS and port 465 for an smtps URL.

        Validates that an explicit URL port still wins.
        """
        config = {
            "url": "smtps://mail.example.com",
            "port": 25,
            "encryption": "none",
            "username": "user",
            "password": _CREDENTIAL,
        }
        settings = SmtpSettings.fromConfig(config)
        self.assertEqual(settings.port, 465)
        self.assertIs(settings.encryption, MailEncryption.SSL)
        self.assertEqual(settings.password, _CREDENTIAL)

        custom = SmtpSettings.fromConfig(
            {**config, "url": "smtps://mail.example.com:8465"},
        )
        self.assertEqual(custom.port, 8465)

    def testSmtpUrlKeepsConfiguredPortAndEncryption(self) -> None:
        """
        Keep the configured port and mode for a plain smtp URL.

        Validates both spellings of an explicit plaintext connection.
        """
        for encryption in ("", "NoNe"):
            settings = SmtpSettings.fromConfig(
                {
                    "url": "smtp://mail.example.com",
                    "port": 2525,
                    "encryption": encryption,
                },
            )
            self.assertEqual(settings.port, 2525)
            self.assertIs(settings.encryption, MailEncryption.NONE)

    def testSensitiveValuesCoverEveryCredentialSpelling(self) -> None:
        """
        Collect the credentials that a server response could echo.

        Validates the redaction material used by transport diagnostics.
        """
        settings = SmtpSettings.fromConfig({
            "url": "smtp://user:url%40secret@smtp.example.com",
            "username": "field-user",
            "password": "field-secret",
        })
        self.assertIn("url@secret", settings.sensitive)
        self.assertIn("field-secret", settings.sensitive)
        self.assertNotIn(None, settings.sensitive)

    def testRejectsUnsupportedAndMalformedUrls(self) -> None:
        """
        Reject unsupported schemes, extra components, and invalid ports.

        Validates that no unknown URL option is silently interpreted.
        """
        for url in (
            "https://mail.example.com",
            "smtp:///",
            "smtp://host/path",
            "smtp://host?timeout=3",
            "smtp://host#part",
            "smtp://host:invalid",
            "smtp://host:65536",
            "smtp://[invalid",
            "smtp://ho\nst",
        ):
            with self.assertRaises(MailConfigurationException):
                SmtpSettings.fromConfig({"url": url})

    def testRejectsIncompleteAuthAndInvalidEffectiveSettings(self) -> None:
        """
        Reject invalid effective options without leaking credentials.

        Validates ranges, types, and incomplete authentication pairs.
        """
        cases = (
            {"username": "user"},
            {"password": _CREDENTIAL},
            {"url": "smtp://user@host", "password": _CREDENTIAL},
            {"encryption": None},
            {"encryption": "automatic"},
            {"port": 0},
            {"port": True},
            {"port": 65536},
            {"port": "587"},
            {"timeout": 0},
            {"timeout": -1},
            {"timeout": 1.5},
            {"timeout": True},
            {"host": ""},
            {"host": "smtp example.com"},
            {"host": "user@smtp.example.com"},
        )
        for settings in cases:
            with self.assertRaises(MailConfigurationException) as failure:
                SmtpSettings.fromConfig({"host": "smtp.example.com", **settings})
            self.assertNotIn(_CREDENTIAL, str(failure.exception))

    def testEntityDefersOperationalRangesUntilTransportSelection(self) -> None:
        """
        Keep an unused SMTP entity inert until the transport is selected.

        Validates that only the effective options are range checked.
        """
        settings = Smtp(host="smtp.example.com", port=-1, timeout=-1)
        with self.assertRaises(MailConfigurationException):
            SmtpSettings.fromConfig(asdict(settings))

        overridden = Smtp(url="smtps://smtp.example.com", port=-1, timeout=None)
        self.assertEqual(SmtpSettings.fromConfig(asdict(overridden)).port, 465)
