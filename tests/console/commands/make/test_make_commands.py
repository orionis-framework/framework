import ast
import importlib.util
from asyncio import gather
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import get_ident
from orionis.console.commands.make import database_migration as migration_module
from orionis.console.commands.make._base import MakeStubCommand
from orionis.console.commands.make.console import MakeConsoleCommand
from orionis.console.commands.make.console_listener import MakeConsoleListener
from orionis.console.commands.make.contract import MakeContract
from orionis.console.commands.make.database_migration import MakeDatabaseMigration
from orionis.console.commands.make.database_schema import MakeDatabaseSchema
from orionis.console.commands.make.database_seeder import MakeDatabaseSeeder
from orionis.console.commands.make.facade import MakeFacade
from orionis.console.commands.make.http_controller import MakeHttpController
from orionis.console.commands.make.http_middleware import MakeHttpMiddleware
from orionis.console.commands.make.http_schema import MakeHttpSchema
from orionis.console.commands.make.http_schema_rule import MakeHttpSchemaRule
from orionis.console.commands.make.mail import MakeMail
from orionis.console.commands.make.model import MakeModel
from orionis.console.commands.make.provider import MakeProvider
from orionis.console.commands.make.service import MakeService
from orionis.console.commands.make.test import MakeTest
from orionis.console.core.commands import CORE_COMMANDS
from orionis.database.contracts.migration import Migration
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.test import TestCase

class _RecordedMakeCommand(MakeStubCommand):
    """Record output and file creation while retaining each command's behavior."""

    __slots__ = ("creation_threads", "errors", "lines", "successes", "timestamps")

    def __init__(self) -> None:
        """Initialize command arguments and isolated output records.

        Returns
        -------
        None
            Create empty message and thread records and reset the line count.
        """
        super().__init__()
        self.creation_threads: list[int] = []
        self.errors: list[str] = []
        self.lines = 0
        self.successes: list[str] = []
        self.timestamps: list[bool] = []

    def newLine(self, count: int = 1) -> None:
        """Record requested blank lines without terminal output.

        Parameters
        ----------
        count : int, optional
            Number of blank lines to add to the total; defaults to one.

        Returns
        -------
        None
            Increment the recorded blank-line count.
        """
        self.lines += count

    def success(self, message: str, *, timestamp: bool = True) -> None:
        """Record a success message and its timestamp flag.

        Parameters
        ----------
        message : str
            Success notification to record without terminal output.
        timestamp : bool, optional
            Timestamp flag to record alongside the message; defaults to True.

        Returns
        -------
        None
            Append the message and timestamp flag to their respective records.
        """
        self.successes.append(message)
        self.timestamps.append(timestamp)

    def error(self, message: object, *, timestamp: bool = True) -> None:
        """Record a command error as text with its timestamp flag.

        Parameters
        ----------
        message : object
            Error value to convert to text without terminal output.
        timestamp : bool, optional
            Timestamp flag to record alongside the error; defaults to True.

        Returns
        -------
        None
            Append the error text and timestamp flag to their respective records.
        """
        self.errors.append(str(message))
        self.timestamps.append(timestamp)

    def createFile(
        self,
        app: IApplication,
        name: str,
        *,
        template_name: str | None = None,
        extension: str = "py",
        replacements: dict[str, str] | None = None,
    ) -> str:
        """Record the current thread and delegate stub file creation.

        Parameters
        ----------
        app : IApplication
            Application supplying output paths.
        name : str
            Requested class name or relative file path.
        template_name : str or None, optional
            Packaged template override, or None to use the command's default.
        extension : str, optional
            Output file extension; defaults to ``"py"``.
        replacements : dict of str to str or None, optional
            Placeholder values forwarded to the renderer, when provided.

        Returns
        -------
        str
            Application-relative path returned by the stub generator.
        """
        self.creation_threads.append(get_ident())
        return super().createFile(
            app, name, template_name=template_name,
            extension=extension, replacements=replacements,
        )

def _record_command(command_type: type[MakeStubCommand]) -> _RecordedMakeCommand:
    """Instantiate a recording subclass that preserves command overrides.

    Parameters
    ----------
    command_type : type of MakeStubCommand
        Command class to combine with the recording implementation.

    Returns
    -------
    _RecordedMakeCommand
        Fresh command that creates real files and records console notifications.
    """
    recorded_type = type(
        f"_Recorded{command_type.__name__}",
        (command_type, _RecordedMakeCommand),
        {"__slots__": ()},
    )
    return recorded_type()

class _Clock:
    """Supply successive fixed timestamps to the migration generator."""

    __slots__ = ("calls",)

    def __init__(self) -> None:
        """Reset the deterministic timestamp request counter.

        Returns
        -------
        None
            Set the number of observed timestamp requests to zero.
        """
        self.calls = 0

    def now(self) -> datetime:
        """Return a fixed UTC timestamp with the next sequential second.

        Returns
        -------
        datetime
            Timestamp on 2026-09-30 at 12:22 with the call count as its second.

        Raises
        ------
        ValueError
            If the incremented call count reaches 60 and is not a valid second.
        """
        self.calls += 1
        return datetime(2026, 9, 30, 12, 22, self.calls, tzinfo=UTC)

class _Application:
    """Resolve core application paths inside a temporary project directory."""

    __slots__ = ("basePath",)

    def __init__(self, base_path: Path) -> None:
        """Store the temporary project root for generated files.

        Parameters
        ----------
        base_path : Path
            Project root used to resolve application output paths.

        Returns
        -------
        None
            Assign the project root to ``basePath``.
        """
        self.basePath = base_path

    def path(self, key: str) -> Path:
        """Resolve a core application path relative to the project root.

        Parameters
        ----------
        key : str
            Key declared in ``CORE_APP_PATHS``.

        Returns
        -------
        Path
            Project root joined with the requested core path.

        Raises
        ------
        KeyError
            If the key is not declared in ``CORE_APP_PATHS``.
        """
        return self.basePath.joinpath(*CORE_APP_PATHS[key].split("/"))

    def config(self, key: str) -> object:
        """Look up a fixed mail sender setting by configuration key.

        Parameters
        ----------
        key : str
            Dot-notated application configuration key.

        Returns
        -------
        str or None
            Sender address or display name, or None for an unknown key.
        """
        return {
            "mail.from_address.address": "notifications@example.test",
            "mail.from_address.name": "Example Notifications",
        }.get(key)

class _Reactor:
    """Report that custom command signatures are available."""

    __slots__ = ("registered",)

    def __init__(self) -> None:
        """Create an isolated command signature registry.

        Returns
        -------
        None
            Initialize an empty set of registered command signatures.
        """
        self.registered: set[str] = set()

    async def hasCommand(self, signature: str) -> bool:
        """Check whether the test registry contains a command signature.

        Parameters
        ----------
        signature : str
            Command signature to look up in the registry.

        Returns
        -------
        bool
            True if the signature is registered, otherwise False.
        """
        return signature in self.registered

def _get_python_sources(root: Path) -> set[Path]:
    """Collect Python source and interface files recursively.

    Parameters
    ----------
    root : Path
        Directory containing generated files.

    Returns
    -------
    set of Path
        Paths matching ``*.py`` or ``*.pyi`` below the root.
    """
    return set(root.rglob("*.py")) | set(root.rglob("*.pyi"))

class TestMakeCommands(TestCase):
    """Verify built-in make command registration and file generation."""

    def setUp(self) -> None:
        """Install a deterministic migration clock and register its restoration.

        Returns
        -------
        None
            Bind a fresh clock and schedule restoration of the original DateTime.
        """
        self.clock = _Clock()
        self.addCleanup(
            setattr, migration_module, "DateTime", migration_module.DateTime,
        )
        migration_module.DateTime = self.clock

    async def testConsoleHandleCreatesFilesOnAWorkerThread(self) -> None:
        """Verify console file creation runs on a worker thread.

        Returns
        -------
        None
            Assert one worker write, one success, no errors, and two blank lines.
        """
        with TemporaryDirectory() as temporary:
            command = _record_command(MakeConsoleCommand)
            command.setArguments({
                "name": "worker", "signature": "generated:worker",
            })
            await command.handle(_Application(Path(temporary)), _Reactor())
            self.assertEqual(len(command.creation_threads), 1)
            self.assertNotEqual(command.creation_threads[0], get_ident())
            self.assertEqual(len(command.successes), 1)
            self.assertEqual(command.errors, [])
            self.assertEqual(command.lines, 2)

    async def testConsoleRejectsInvalidOrRegisteredSignaturesBeforeWriting(
        self,
    ) -> None:
        """Verify invalid, missing, or registered signatures prevent file writes.

        Returns
        -------
        None
            Assert each rejection records an error without creating any files.
        """
        with TemporaryDirectory() as temporary:
            app = _Application(Path(temporary))
            reactor = _Reactor()
            reactor.registered.add("generated:taken")
            for signature in ("INVALID", "generated:taken", None):
                command = _record_command(MakeConsoleCommand)
                command.setArguments({"name": "rejected", "signature": signature})
                await command.handle(app, reactor)
                self.assertEqual(command.creation_threads, [])
                self.assertEqual(command.successes, [])
                self.assertEqual(len(command.errors), 1)
            self.assertEqual(_get_python_sources(app.basePath), set())

    async def testIndependentGeneratorsCreateTheirOwnFilesConcurrently(
        self,
    ) -> None:
        """Verify concurrent service generators keep their output independent.

        Returns
        -------
        None
            Assert each file contains its own class and reports error-free success.
        """
        with TemporaryDirectory() as temporary:
            app = _Application(Path(temporary))
            commands = [_record_command(MakeService) for _ in range(8)]
            for index, command in enumerate(commands):
                command.setArguments({"name": f"worker_{index}"})
            await gather(*(command.handle(app) for command in commands))
            for index, command in enumerate(commands):
                target = app.basePath / f"app/services/worker_{index}.py"
                self.assertIn(
                    f"class Worker{index}", target.read_text(encoding="utf-8"),
                )
                self.assertEqual(len(command.successes), 1)
                self.assertEqual(command.errors, [])

    def testGeneratedStringLiteralsPreserveQuotedAndMultilineValues(self) -> None:
        """Verify generated literals preserve quoted and multiline values.

        Returns
        -------
        None
            Assert command metadata and facade accessors round-trip unchanged.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            description = 'A "quoted" command.\nAnother\\line'
            accessor = 'services."mailer"\nnext\\segment'

            command = MakeConsoleCommand()
            command.setArguments(
                {"signature": "reports:show", "description": description},
            )
            command_source = root / command.createFile(app, "report_command")
            command_class = next(
                node
                for node in ast.parse(
                    command_source.read_text(encoding="utf-8"),
                ).body
                if isinstance(node, ast.ClassDef)
            )
            assignments = {
                node.target.id: ast.literal_eval(node.value)
                for node in command_class.body
                if isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id in {"signature", "description"}
            }
            self.assertEqual(assignments["signature"], "reports:show")
            self.assertEqual(assignments["description"], description)

            facade = MakeFacade()
            facade.setArguments({"accessor": accessor})
            facade_source = root / facade.createFile(app, "report_facade")
            facade_class = next(
                node
                for node in ast.parse(
                    facade_source.read_text(encoding="utf-8"),
                ).body
                if isinstance(node, ast.ClassDef)
            )
            accessor_method = next(
                node
                for node in facade_class.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "getFacadeAccessor"
            )
            accessor_return = next(
                node for node in accessor_method.body if isinstance(node, ast.Return)
            )
            self.assertEqual(ast.literal_eval(accessor_return.value), accessor)

    async def testMakeTestCreatesDiscoverableNestedModule(self) -> None:
        """Verify nested test modules use a single discovery prefix.

        Returns
        -------
        None
            Assert paths, class names, inheritance, and async method documentation.
        """
        for name in ("billing/invoice.py", "billing/test_invoice.py"):
            with TemporaryDirectory() as temporary:
                root = Path(temporary)
                command = _record_command(MakeTest)
                command.setArguments({"name": name})

                await command.handle(_Application(root))

                target = root / "tests" / "billing" / "test_invoice.py"
                self.assertTrue(target.is_file())
                self.assertEqual(list((root / "tests").rglob("test_*.py")), [target])
                module = ast.parse(target.read_text(encoding="utf-8"))
                test_case = next(
                    node for node in module.body if isinstance(node, ast.ClassDef)
                )
                self.assertEqual(test_case.name, "TestInvoice")
                self.assertEqual([base.id for base in test_case.bases], ["TestCase"])
                test_method = next(
                    node
                    for node in test_case.body
                    if isinstance(node, ast.AsyncFunctionDef)
                )
                self.assertEqual(test_method.name, "testExample")
                self.assertIsNotNone(ast.get_docstring(test_method))
                self.assertEqual(len(command.successes), 1)
                self.assertEqual(command.errors, [])

    async def testMakeDatabaseMigrationTimestampsDiscoverableModules(self) -> None:
        """Verify timestamped migrations remain importable in nested directories.

        Returns
        -------
        None
            Assert file paths, class names, async methods, and Migration inheritance.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            for name in ("create_accounts.py", "billing/create_invoices.py"):
                command = _record_command(MakeDatabaseMigration)
                command.setArguments({"name": name})
                await command.handle(app)
                self.assertEqual(command.errors, [])
            self.assertEqual(self.clock.calls, 2)

            migration_root = root / "database" / "migrations"
            expected = (
                (
                    migration_root / "m20260930122201_create_accounts.py",
                    "CreateAccounts",
                ),
                (
                    migration_root / "billing" / "m20260930122202_create_invoices.py",
                    "CreateInvoices",
                ),
            )
            for target, expected_class in expected:
                self.assertTrue(target.is_file())
                module = ast.parse(target.read_text(encoding="utf-8"))
                migration = next(
                    node for node in module.body if isinstance(node, ast.ClassDef)
                )
                self.assertEqual(migration.name, expected_class)
                self.assertEqual([base.id for base in migration.bases], ["Migration"])
                methods = {
                    node.name
                    for node in migration.body
                    if isinstance(node, ast.AsyncFunctionDef)
                }
                self.assertEqual(methods, {"up", "down"})
                spec = importlib.util.spec_from_file_location(
                    f"generated_{target.stem}",
                    target,
                )
                module_instance = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module_instance)
                self.assertTrue(
                    issubclass(getattr(module_instance, expected_class), Migration),
                )

    async def testMakeDatabaseMigrationIgnoresScaffoldSequence(self) -> None:
        """Verify existing migration numbering does not alter timestamp prefixes.

        Returns
        -------
        None
            Assert the generated filename uses the deterministic clock's timestamp.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            migration_root = root / "database" / "migrations"
            migration_root.mkdir(parents=True)
            (migration_root / "m0000000001_existing.py").write_text(
                "",
                encoding="utf-8",
            )
            command = _record_command(MakeDatabaseMigration)
            command.setArguments({"name": "create_orders.py"})

            await command.handle(_Application(root))

            self.assertTrue(
                (migration_root / "m20260930122201_create_orders.py").is_file(),
            )
            self.assertEqual(command.errors, [])

    async def testMakeDatabaseSeederAndSchemaUseConfiguredPaths(self) -> None:
        """Verify seeders and schemas use configured paths and single suffixes.

        Returns
        -------
        None
            Assert generated class names, base classes, and template defaults.
        """
        cases = (
            (
                MakeDatabaseSeeder,
                "sales/account.py",
                Path("database/seeders/sales/account_seeder.py"),
                "AccountSeeder",
            ),
            (
                MakeDatabaseSeeder,
                "sales/account_seeder.py",
                Path("database/seeders/sales/account_seeder.py"),
                "AccountSeeder",
            ),
            (
                MakeDatabaseSchema,
                "sales/account_schema.py",
                Path("database/schemas/sales/account_schema.py"),
                "AccountSchema",
            ),
        )
        for command_type, name, relative_path, expected_class in cases:
            with TemporaryDirectory() as temporary:
                root = Path(temporary)
                command = _record_command(command_type)
                command.setArguments({"name": name})
                await command.handle(_Application(root))

                target = root / relative_path
                self.assertTrue(target.is_file())
                module = ast.parse(target.read_text(encoding="utf-8"))
                generated_class = next(
                    node for node in module.body if isinstance(node, ast.ClassDef)
                )
                self.assertEqual(generated_class.name, expected_class)
                if command_type is MakeDatabaseSeeder:
                    self.assertEqual(
                        [ast.unparse(base) for base in generated_class.bases],
                        ["Seeder"],
                    )
                    self.assertIn(
                        "from orionis.database.seeders.seeder import Seeder",
                        target.read_text(encoding="utf-8"),
                    )
                if command_type is MakeDatabaseSchema:
                    self.assertIn(
                        "table_definition", target.read_text(encoding="utf-8"),
                    )
                    spec = importlib.util.spec_from_file_location(
                        "generated_database_schema",
                        target,
                    )
                    module_instance = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module_instance)
                    self.assertIsNone(
                        getattr(module_instance, expected_class).table_definition,
                    )
                else:
                    self.assertTrue(
                        any(
                            isinstance(node, ast.AsyncFunctionDef)
                            and node.name == "run"
                            for node in generated_class.body
                        ),
                    )
                self.assertEqual(command.errors, [])

    async def testMakeServiceCreatesNestedFileAfterRemovingExtension(self) -> None:
        """Verify service generation strips extensions and preserves nested paths.

        Returns
        -------
        None
            Assert the service path, class name, and successful command output.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            command = _record_command(MakeService)
            command.setArguments({"name": "billing/invoice_service.py"})

            await command.handle(app)

            target = root / "app" / "services" / "billing" / "invoice_service.py"
            self.assertTrue(target.is_file())
            self.assertIn("class InvoiceService", target.read_text(encoding="utf-8"))
            self.assertEqual(len(command.successes), 1)
            self.assertEqual(command.errors, [])

    async def testMakeControllerGeneratesAsyncApiResourceActions(self) -> None:
        """Verify API controllers declare documented async resource actions.

        Returns
        -------
        None
            Assert JSON return types, method spacing, and docstring-only bodies.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            command = _record_command(MakeHttpController)
            command.setArguments({"name": "api/invoice.py", "api": True})

            await command.handle(app)

            target = (
                root / "app" / "http" / "controllers" / "api"
                / "invoice_controller.py"
            )
            content = target.read_text(encoding="utf-8")
            module = ast.parse(content)
            controller_class = next(
                node for node in module.body if isinstance(node, ast.ClassDef)
            )
            methods = {
                node.name: node
                for node in controller_class.body
                if isinstance(node, ast.AsyncFunctionDef)
            }

            self.assertEqual(
                set(methods),
                {"index", "create", "store", "show", "edit", "update", "destroy"},
            )
            self.assertTrue(
                all(
                    "JSONResponse" in ast.unparse(method.returns)
                    for method in methods.values()
                ),
            )
            ordered_methods = sorted(
                methods.values(),
                key=lambda method: method.lineno,
            )
            self.assertTrue(
                all(
                    next_method.lineno - method.end_lineno >= 2
                    for method, next_method in pairwise(ordered_methods)
                ),
            )
            self.assertTrue(
                all(
                    len(method.body) == 1
                    and isinstance(method.body[0], ast.Expr)
                    and isinstance(method.body[0].value, ast.Constant)
                    and isinstance(method.body[0].value.value, str)
                    for method in methods.values()
                ),
            )
            self.assertNotIn("return ", content)
            self.assertEqual(command.errors, [])

    async def testMakeControllerCanGenerateAnInvokableAction(self) -> None:
        """Verify invokable controllers declare a single async ``__call__`` action.

        Returns
        -------
        None
            Assert the action name, HttpResponse import, and absence of return code.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            command = _record_command(MakeHttpController)
            command.setArguments({"name": "health", "invoke": True})

            await command.handle(app)

            target = root / "app" / "http" / "controllers" / "health_controller.py"
            content = target.read_text(encoding="utf-8")
            module = ast.parse(content)
            controller_class = next(
                node for node in module.body if isinstance(node, ast.ClassDef)
            )
            methods = [
                node.name
                for node in controller_class.body
                if isinstance(node, ast.AsyncFunctionDef)
            ]

            self.assertEqual(methods, ["__call__"])
            self.assertIn("HttpResponse", content)
            self.assertNotIn("return ", content)
            self.assertEqual(command.errors, [])

    async def testMakeProviderAddsProviderPostfixOnce(self) -> None:
        """Verify provider filenames and class names receive one suffix.

        Returns
        -------
        None
            Assert flat and nested paths retain the expected provider class name.
        """
        for index, name in enumerate(("cache", "billing/cache_provider.py")):
            with TemporaryDirectory() as temporary:
                root = Path(temporary)
                app = _Application(root)
                command = _record_command(MakeProvider)
                command.setArguments({"name": name})

                await command.handle(app)

                relative_path = (
                    Path("app") / "providers" / "cache_provider.py"
                )
                if index:
                    relative_path = (
                        Path("app") / "providers" / "billing"
                        / "cache_provider.py"
                    )
                content = (root / relative_path).read_text(encoding="utf-8")
                self.assertIn("class CacheProvider", content)
                self.assertEqual(command.errors, [])

    async def testMakeModelAndMailUseTheirApplicationDirectories(self) -> None:
        """Verify model and mail templates use their configured directories.

        Returns
        -------
        None
            Assert model defaults, runtime application typing, and mail senders.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            for command_type, name in (
                (MakeModel, "user"),
                (MakeMail, "welcome"),
            ):
                command = _record_command(command_type)
                command.setArguments({"name": name})
                await command.handle(app)
                self.assertEqual(command.errors, [])

            model = (root / "app" / "models" / "user.py").read_text(encoding="utf-8")
            mail = (root / "app" / "notifications" / "welcome_mail.py").read_text(
                encoding="utf-8",
            )
            self.assertIn("fillable: ClassVar[list[str]] = []", model)
            self.assertIn("casts: ClassVar[dict[str, str]] = {}", model)
            self.assertIn(
                "table_definition: ClassVar[TableDefinition | None] = None",
                model,
            )
            self.assertIn("def __init__(self, application: IApplication)", mail)
            self.assertIn("class WelcomeMail(Mailable)", mail)
            self.assertIn(
                'self.application.config("mail.from_address.address")',
                mail,
            )
            mail_path = root / "app" / "notifications" / "welcome_mail.py"
            spec = importlib.util.spec_from_file_location(
                "generated_welcome_mail",
                mail_path,
            )
            mail_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mail_module)
            self.assertIs(
                mail_module.WelcomeMail.__init__.__annotations__["application"],
                IApplication,
            )
            sender = mail_module.WelcomeMail(app).envelope().from_address
            self.assertIsNotNone(sender)
            self.assertEqual(sender.address, "notifications@example.test")
            self.assertEqual(sender.name, "Example Notifications")

    async def testEveryMakeStubProducesDocumentedPython(self) -> None:
        """Verify every make template renders documented Python declarations.

        Returns
        -------
        None
            Assert syntax, runtime imports, and class and method documentation.
        """
        cases = (
            (
                MakeConsoleCommand,
                {"signature": "generated:command", "description": None},
            ),
            (MakeConsoleListener, {}),
            (MakeContract, {}),
            (MakeFacade, {"accessor": "generated.service"}),
            (MakeProvider, {}),
            (MakeProvider, {"deferred": True}),
            (MakeService, {}),
            (MakeModel, {}),
            (MakeMail, {}),
            (MakeHttpController, {}),
            (MakeHttpMiddleware, {}),
            (MakeHttpSchema, {}),
            (MakeHttpSchemaRule, {}),
            (MakeTest, {}),
            (MakeDatabaseMigration, {}),
            (MakeDatabaseSeeder, {}),
            (MakeDatabaseSchema, {}),
        )
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            for index, (command_type, extra_arguments) in enumerate(cases):
                command = _record_command(command_type)
                arguments = {
                    "name": f"generated/file_{index}.py",
                    **extra_arguments,
                }
                command.setArguments(arguments)
                before = _get_python_sources(root)
                if isinstance(command, MakeConsoleCommand):
                    await command.handle(app, _Reactor())
                else:
                    await command.handle(app)

                generated = _get_python_sources(root) - before
                self.assertTrue(generated, command.signature)
                self.assertEqual(command.errors, [])
                for file_path in generated:
                    content = file_path.read_text(encoding="utf-8")
                    if command_type is MakeHttpMiddleware:
                        self.assertNotIn("del request", content)
                    self.assertNotIn(
                        "from __future__ import annotations",
                        content,
                    )
                    self.assertNotIn("TYPE_CHECKING", content)
                    module = ast.parse(content)
                    classes = [
                        node
                        for node in module.body
                        if isinstance(node, ast.ClassDef)
                    ]
                    self.assertTrue(classes, str(file_path))
                    for class_node in classes:
                        if file_path.suffix == ".pyi":
                            self.assertIn(
                                "# This interface pairs with the facade implementation",
                                content,
                            )
                        else:
                            self.assertIsNotNone(
                                ast.get_docstring(class_node),
                                f"{file_path}:{class_node.name}",
                            )
                        methods = [
                            node
                            for node in class_node.body
                            if isinstance(
                                node,
                                ast.FunctionDef | ast.AsyncFunctionDef,
                            )
                        ]
                        for method in methods:
                            self.assertIsNotNone(
                                ast.get_docstring(method),
                                f"{file_path}:{class_node.name}.{method.name}",
                            )

    def testRegistersEveryPlannedMakeCommand(self) -> None:
        """Verify all planned make commands appear in the core registry.

        Returns
        -------
        None
            Assert signature coverage, uniqueness, and canonical seeder spelling.
        """
        signatures = {command.signature for command in CORE_COMMANDS}

        expected = {
            "make:console-command",
            "make:console-listener",
            "make:contract",
            "make:facade",
            "make:provider",
            "make:service",
            "make:model",
            "make:mail",
            "make:http-controller",
            "make:http-middleware",
            "make:http-schema",
            "make:http-schema-rule",
            "make:test",
            "make:database-migration",
            "make:database-seeder",
            "make:database-schema",
        }
        self.assertTrue(expected.issubset(signatures))
        self.assertEqual(len(signatures), len(CORE_COMMANDS))
        self.assertNotIn("make:database-seader", signatures)
        seeder_count = sum(
            command.signature == "make:database-seeder"
            for command in CORE_COMMANDS
        )
        self.assertEqual(seeder_count, 1)
