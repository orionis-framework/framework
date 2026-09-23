import asyncio
from email import policy
from email.parser import BytesParser
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, cast
from orionis.foundation.config.mail.entities.file import File
from orionis.foundation.config.mail.entities.mail import Mail as MailConfig
from orionis.foundation.config.mail.entities.mailers import Mailers
from orionis.foundation.config.mail.entities.smtp import Smtp
from orionis.mail.composer import MailComposer
from orionis.mail.entities.content import Content
from orionis.mail.exceptions import MailCompositionException, MailConfigurationException
from orionis.mail.manager import MailManager
from orionis.test import TestCase
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment
from tests.mail.fixtures.doubles import (
    MailApplication,
    MemoryStorage,
    RecordingFactory,
    RecordingTransport,
)

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication
    from orionis.storage.contracts.manager import IStorageManager

class TestMailManager(TestCase):

    def setUp(self) -> None:
        """Construct a manager with real views and memory-backed storage."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.settings = {
            "default": "archive",
            "mailers": {
                "archive": {"driver": "file", "path": "stored"},
                "file": {"path": "default-file"},
                "smtp": {"host": "", "username": "", "password": ""},
            },
        }
        self.app = MailApplication(self.root, self.settings)
        self.storage = MemoryStorage()
        view = Jinja2Engine(ViewEnvironment(cast("IApplication", self.app)))
        composer = MailComposer(view, cast("IStorageManager", self.storage))
        self.manager = MailManager(cast("IApplication", self.app), composer)
        self.base = self.manager.fromAddress("sender@example.com").to("ana@example.com")

    async def testNamedDefaultAndExplicitFileMailerStoreRealMime(self) -> None:
        """
        Resolve the default and an explicit mailer by configuration name.

        Validates that an unused empty SMTP entry blocks nothing.
        """
        result = await self.base.subject("Notice").raw("Hello")
        explicit = await self.base.mailer("file").html("<p>Hello</p>")

        self.assertEqual(
            (result.mailer, result.driver, result.status),
            ("archive", "file", "stored"),
        )
        self.assertEqual(result.file_path.parent, self.root / "stored")
        self.assertEqual(explicit.file_path.parent, self.root / "default-file")

        parsed = BytesParser(policy=policy.default).parsebytes(
            result.file_path.read_bytes(),
        )
        self.assertEqual(parsed["Subject"], "Notice")
        self.assertEqual(parsed["Message-ID"], result.message_id)
        self.assertEqual(result.accepted_recipients, ())
        self.assertEqual(dict(result.rejected_recipients), {})
        self.assertNotIn("driver", self.settings["mailers"]["file"])

    async def testConventionalEntitiesRemainUsable(self) -> None:
        """
        Consume the frozen configuration entities without rebuilding them.

        Validates backwards compatibility with the shipped bootstrap.
        """
        self.app.mail_config = MailConfig(
            default="file",
            mailers=Mailers(
                smtp=Smtp(host="", username="", password=""),
                file=File(path="entity"),
            ),
        )
        result = await self.base.raw("")
        self.assertEqual(result.file_path.parent, self.root / "entity")

    async def testRealExtensionUsesConfigFactoryAndContainer(self) -> None:
        """
        Register a custom driver and send through its normal resolution.

        Validates that the factory receives a detached configuration.
        """
        self.settings["mailers"]["archive"] = {"driver": "recording", "options": [1, 2]}
        factory = RecordingFactory()
        self.manager.extend("recording", factory)

        result = await self.base.send(Content(text="record me"))

        self.assertEqual(result.driver, "recording")
        self.assertEqual(self.app.resolved, [RecordingTransport])
        self.assertEqual(factory.configs[0]["options"], (1, 2))
        self.assertEqual(factory.configs[0]["driver"], "recording")
        with self.assertRaises(TypeError):
            factory.configs[0]["driver"] = "changed"
        self.assertEqual(len(factory.transports[0].messages), 1)

    def testExtensionRejectsDuplicatesAndInvalidRegistrations(self) -> None:
        """
        Reject duplicate drivers and malformed registrations.

        Validates that a built-in driver is never silently replaced.
        """
        factory = RecordingFactory()
        self.manager.extend("recording", factory)

        for driver in ("recording", "file", "smtp", "", "   ", None, 7):
            with self.assertRaises(MailConfigurationException):
                self.manager.extend(driver, factory)
        with self.assertRaises(MailConfigurationException):
            self.manager.extend("other", "not-callable")

    async def testUnknownNamesAndDriversFailWithoutFallback(self) -> None:
        """
        Report unknown mailers and drivers instead of falling back.

        Validates that a driver may be registered before its first use.
        """
        with self.assertRaises(MailConfigurationException):
            await self.base.mailer("missing").raw("text")

        self.settings["mailers"]["archive"] = {"driver": "late"}
        with self.assertRaises(MailConfigurationException):
            await self.base.raw("text")

        self.manager.extend("late", RecordingFactory())
        result = await self.base.raw("text")
        self.assertEqual(result.driver, "late")
        self.assertFalse((self.root / "stored").exists())

    async def testInvalidSelectedConfigurationNeverFallsBack(self) -> None:
        """
        Validate the section, default, and selected entry only on send.

        Validates that each malformed shape produces a clear failure.
        """
        cases = (
            None,
            {},
            {"default": 1, "mailers": {}},
            {"default": "x", "mailers": {"x": {"path": "out"}}},
            {"default": "x", "mailers": {"x": {"driver": False}}},
            {"default": "x", "mailers": {"x": None}},
        )
        for config in cases:
            self.app.mail_config = config
            pending = self.manager.fromAddress("a@b").to("b@c")
            with self.assertRaises(MailConfigurationException):
                await pending.raw("text")
        self.assertFalse((self.root / "stored").exists())

    async def testInvalidFactoryResultsAreRejected(self) -> None:
        """
        Reject a factory that does not return the transport contract.

        Validates that only IMailTransport instances are used.
        """
        def invalid_factory(_app: object, _config: object) -> None:
            return None

        self.settings["mailers"]["archive"] = {"driver": "invalid"}
        self.manager.extend("invalid", invalid_factory)

        with self.assertRaises(MailConfigurationException):
            await self.base.raw("text")

    async def testPreparationFailuresNeverCreateFinalFiles(self) -> None:
        """
        Stop publication when a view or final envelope is invalid.

        Validates that transports run only after successful preparation.
        """
        with self.assertRaises(MailCompositionException):
            await self.base.send("missing")
        with self.assertRaises(MailCompositionException):
            await self.manager.to("a@b").raw("missing sender")
        self.assertFalse((self.root / "stored").exists())

    async def testConcurrentFileSendsHaveIndependentMimeAndUniqueNames(self) -> None:
        """
        Publish unique complete files without mixing operation state.

        Validates that the shared manager caches nothing per operation.
        """
        base = self.manager.fromAddress("sender@example.com").subject("Notice")
        results = await asyncio.gather(
            *(
                base.to(f"user{index}@example.com").raw(f"body {index}")
                for index in range(20)
            ),
        )

        self.assertEqual(len({result.file_path for result in results}), 20)
        self.assertEqual(list((self.root / "stored").glob("*.tmp")), [])
        for index, result in enumerate(results):
            parsed = BytesParser(policy=policy.default).parsebytes(
                result.file_path.read_bytes(),
            )
            self.assertEqual(str(parsed["To"]), f"user{index}@example.com")
            self.assertEqual(parsed.get_content().strip(), f"body {index}")
