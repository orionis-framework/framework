import ast
import inspect
from pathlib import Path
from orionis.container.context.scope import ScopedContext
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.foundation.application import Application
from orionis.foundation.core_providers import CORE_PROVIDERS
from orionis.mail.composer import MailComposer
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.entities.address import Address
from orionis.mail.entities.attachment import Attachment
from orionis.mail.manager import MailManager
from orionis.mail.pending import PendingMail
from orionis.mail.provider import MailProvider
from orionis.support import facades as facades_package
from orionis.support.facades.mail import Mail
from orionis.test import TestCase

# Operations the facade stub publishes for application code.
_CONSUMER_SURFACE = frozenset({
    "attach",
    "bcc",
    "cc",
    "fromAddress",
    "html",
    "mailer",
    "raw",
    "replyTo",
    "send",
    "subject",
    "to",
})

class AlertService:
    """Consume the manager through constructor injection."""

    __slots__ = ("mail",)

    def __init__(self, mail: IMailManager) -> None:
        self.mail = mail

def stub_methods() -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """
    Parse the facade stub and return its declared methods.

    Returns
    -------
    list[ast.FunctionDef | ast.AsyncFunctionDef]
        Declarations found inside the stubbed facade class.
    """
    root = Path(__file__).resolve().parents[2]
    source = (root / "orionis/support/facades/mail.pyi").read_text(encoding="utf-8")
    facade = next(
        node for node in ast.parse(source).body if isinstance(node, ast.ClassDef)
    )
    return [
        node
        for node in facade.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

class TestMailProvider(TestCase):

    def testIsAnEagerCoreProvider(self) -> None:
        """
        Ship as an eager core provider instead of a deferred one.

        Validates that the facade is pinned during normal startup.
        """
        self.assertIn(MailProvider, CORE_PROVIDERS)
        self.assertFalse(issubclass(MailProvider, DeferrableProvider))
        self.assertTrue(inspect.iscoroutinefunction(MailProvider.boot))

    def testRegistersTheComposerAndTheManagerContract(self) -> None:
        """
        Bind the shared composer and the manager contract as singletons.

        Validates the wiring used by dependency injection.
        """
        recorded: list[tuple[object, object]] = []

        class RecordingApp:
            __slots__ = ()

            def singleton(self, abstract: object, concrete: object) -> None:
                """Record one binding without touching a real container."""
                recorded.append((abstract, concrete))

        MailProvider(RecordingApp()).register()
        self.assertEqual(
            recorded,
            [(MailComposer, MailComposer), (IMailManager, MailManager)],
        )

class TestMailFacade(TestCase):

    def setUp(self) -> None:
        """Keep test-time resolutions out of the ambient runner scope."""
        self.scope_token = ScopedContext.setCurrentScope(None)

    def tearDown(self) -> None:
        """Restore the runner scope after each resolution."""
        ScopedContext.reset(self.scope_token)

    async def testFacadeAndConstructorInjectionUseTheSameSingleton(self) -> None:
        """
        Resolve one manager for the facade and for injected consumers.

        Validates the wiring of the booted application.
        """
        app = Application()
        manager = await app.make(IMailManager)
        service = await app.build(AlertService)

        self.assertIsInstance(manager, MailManager)
        self.assertIs(service.mail, manager)
        self.assertIs(await Mail.resolve(), manager)
        self.assertIs(Mail._pinned_instance, manager)

    def testIsExportedByTheFacadesPackage(self) -> None:
        """
        Expose the facade from the shared facades package.

        Validates that consumers can import it like every other facade.
        """
        self.assertIn("Mail", facades_package.__all__)
        self.assertIs(facades_package.Mail, Mail)

    def testEveryFacadeEntryImmediatelyReturnsPendingMail(self) -> None:
        """
        Return a usable chain without an intermediate await.

        Validates that no deferred dispatcher reaches application code.
        """
        calls = (
            Mail.mailer("file"),
            Mail.fromAddress(Address("from@example.com")),
            Mail.to("to@example.com"),
            Mail.cc("cc@example.com"),
            Mail.bcc("bcc@example.com"),
            Mail.replyTo("reply@example.com"),
            Mail.subject("Notice"),
            Mail.attach(Attachment.fromStorage("guide.pdf")),
        )
        for pending in calls:
            self.assertIsInstance(pending, PendingMail)
            self.assertFalse(inspect.isawaitable(pending))

    def testRuntimeFacadeOnlyDeclaresItsAccessor(self) -> None:
        """
        Keep the runtime facade free of method stubs.

        Validates that the metaclass dispatch is never shadowed.
        """
        self.assertIs(Mail.getFacadeAccessor(), IMailManager)
        own_methods = {
            name
            for name, value in vars(Mail).items()
            if isinstance(value, (staticmethod, classmethod))
        }
        self.assertEqual(own_methods, {"getFacadeAccessor"})

class TestMailFacadeStub(TestCase):

    def testDeclaresOnlyTheConsumerSurface(self) -> None:
        """
        Publish composition and delivery operations only.

        Validates that registration and facade internals stay out.
        """
        declared = {method.name for method in stub_methods()}
        self.assertEqual(declared, _CONSUMER_SURFACE)
        self.assertNotIn("extend", declared)
        self.assertNotIn("getFacadeAccessor", declared)

    def testDeclaresEveryEntryAsAStaticMethod(self) -> None:
        """
        Declare each entry as a static method on the facade class.

        Validates that class-level calls type check for consumers.
        """
        for method in stub_methods():
            decorators = {
                node.id for node in method.decorator_list if isinstance(node, ast.Name)
            }
            self.assertIn("staticmethod", decorators, msg=method.name)

    def testTerminalOperationsAreDeclaredAsynchronous(self) -> None:
        """
        Mark only the terminal operations as coroutines in the stub.

        Validates that composition stays synchronous for consumers.
        """
        for method in stub_methods():
            self.assertEqual(
                isinstance(method, ast.AsyncFunctionDef),
                method.name in {"send", "raw", "html"},
                msg=method.name,
            )

    def testSendDeclaresItsThreeOverloads(self) -> None:
        """
        Publish the Mailable, view, and Content overloads of send.

        Validates the typed surface used by application code.
        """
        sends = [method for method in stub_methods() if method.name == "send"]
        self.assertEqual(len(sends), 3)
        self.assertEqual(
            [method.args.posonlyargs[0].arg for method in sends],
            ["mailable", "view", "content"],
        )

    def testSignaturesMatchTheImplementation(self) -> None:
        """
        Keep stub parameters, defaults, and returns aligned with the manager.

        Validates that autocompletion never advertises a wrong signature.
        """
        for method in stub_methods():
            if method.name == "send":
                continue

            implemented = inspect.signature(
                getattr(MailManager, method.name),
                annotation_format=inspect.Format.STRING,
            )
            parameters = list(implemented.parameters.values())[1:]

            self.assertEqual(
                [argument.arg for argument in method.args.args],
                [parameter.name for parameter in parameters],
                msg=method.name,
            )
            self.assertEqual(
                [ast.unparse(default) for default in method.args.defaults],
                [
                    repr(parameter.default)
                    for parameter in parameters
                    if parameter.default is not inspect.Parameter.empty
                ],
                msg=method.name,
            )
            self.assertEqual(
                ast.unparse(method.returns),
                implemented.return_annotation,
                msg=method.name,
            )
