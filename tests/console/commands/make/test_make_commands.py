import ast
import importlib.util
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
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

class _Application:
    """Resolve core application paths inside a temporary project directory."""

    __slots__ = ("basePath",)

    def __init__(self, base_path: Path) -> None:
        """Store the root used by the generated files.

        Parameters
        ----------
        base_path : Path
            Temporary application root.

        Returns
        -------
        None
            Store the application root.
        """
        self.basePath = base_path

    def path(self, key: str) -> Path:
        """Resolve a core application path key below the temporary root.

        Parameters
        ----------
        key : str
            Key declared in ``CORE_APP_PATHS``.

        Returns
        -------
        Path
            Absolute output directory for the requested key.
        """
        return self.basePath.joinpath(*CORE_APP_PATHS[key].split("/"))

    def config(self, key: str) -> object:
        """Return mail sender settings used by the generated Mailable.

        Parameters
        ----------
        key : str
            Dot-notated application configuration key.

        Returns
        -------
        object
            Configured sender address or display name, when requested.
        """
        return {
            "mail.from_address.address": "notifications@example.test",
            "mail.from_address.name": "Example Notifications",
        }.get(key)

class _Reactor:
    """Report that custom command signatures are available."""

    __slots__ = ("registered",)

    def __init__(self) -> None:
        """Initialize the isolated signature registry.

        Returns
        -------
        None
            Create an empty set of registered signatures.
        """
        self.registered: set[str] = set()

    async def hasCommand(self, signature: str) -> bool:
        """Check whether a command signature is already registered.

        Parameters
        ----------
        signature : str
            Command signature requested by the generated command.

        Returns
        -------
        bool
            Return whether the test registry contains the signature.
        """
        return signature in self.registered

def _get_python_sources(root: Path) -> set[Path]:
    """Collect Python source and stub files below a directory.

    Parameters
    ----------
    root : Path
        Directory containing generated files.

    Returns
    -------
    set[Path]
        Python source and interface stub paths.
    """
    return set(root.rglob("*.py")) | set(root.rglob("*.pyi"))

class TestMakeCommands(TestCase):
    """Verify built-in make command registration and file generation."""

    def testGeneratedStringLiteralsPreserveQuotedAndMultilineValues(self) -> None:
        """Generate valid Python for values containing quotes and newlines.

        Returns
        -------
        None
            Parsed literals retain the original command and facade values.
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
        """Prefix the final test filename once and preserve nested directories.

        Returns
        -------
        None
            Assertions verify generated names, syntax, and test inheritance.
        """
        for name in ("billing/invoice.py", "billing/test_invoice.py"):
            with TemporaryDirectory() as temporary:
                root = Path(temporary)
                command = MakeTest()
                command.setArguments({"name": name})

                with (
                    patch.object(command, "newLine"),
                    patch.object(command, "success") as success,
                    patch.object(command, "error") as error,
                ):
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
                self.assertTrue(success.called)
                error.assert_not_called()

    async def testMakeDatabaseMigrationTimestampsDiscoverableModules(self) -> None:
        """Timestamp migrations across nested directories for discovery.

        Returns
        -------
        None
            Assertions verify timestamped paths and migration methods.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            created_at = (
                datetime(2026, 9, 30, 12, 22, 1, tzinfo=UTC),
                datetime(2026, 9, 30, 12, 22, 2, tzinfo=UTC),
            )
            with patch(
                "orionis.console.commands.make.database_migration.DateTime.now",
                side_effect=created_at,
            ) as now:
                for name in ("create_accounts.py", "billing/create_invoices.py"):
                    command = MakeDatabaseMigration()
                    command.setArguments({"name": name})
                    with (
                        patch.object(command, "newLine"),
                        patch.object(command, "success"),
                        patch.object(command, "error") as error,
                    ):
                        await command.handle(app)
                    error.assert_not_called()
                self.assertEqual(now.call_count, 2)

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
        """Use the current timestamp despite existing numbered migrations.

        Returns
        -------
        None
            Assertions verify scaffold numbering does not affect the prefix.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            migration_root = root / "database" / "migrations"
            migration_root.mkdir(parents=True)
            (migration_root / "m0000000001_existing.py").write_text(
                "",
                encoding="utf-8",
            )
            command = MakeDatabaseMigration()
            command.setArguments({"name": "create_orders.py"})

            with (
                patch.object(command, "newLine"),
                patch.object(command, "success"),
                patch.object(command, "error") as error,
                patch(
                    "orionis.console.commands.make.database_migration.DateTime.now",
                    return_value=datetime(2026, 9, 30, 12, 22, 1, tzinfo=UTC),
                ),
            ):
                await command.handle(_Application(root))

            self.assertTrue(
                (migration_root / "m20260930122201_create_orders.py").is_file(),
            )
            error.assert_not_called()

    async def testMakeDatabaseSeederAndSchemaUseConfiguredPaths(self) -> None:
        """Generate reusable seeder and schema skeletons with one suffix.

        Returns
        -------
        None
            Assertions verify output paths, suffixes, and class names.
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
                command = command_type()
                command.setArguments({"name": name})
                with (
                    patch.object(command, "newLine"),
                    patch.object(command, "success"),
                    patch.object(command, "error") as error,
                ):
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
                error.assert_not_called()

    async def testMakeServiceCreatesNestedFileAfterRemovingExtension(self) -> None:
        """Generate a nested service from a name ending in ``.py``.

        Returns
        -------
        None
            Assertions verify the configured service path and class name.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            command = MakeService()
            command.setArguments({"name": "billing/invoice_service.py"})

            with (
                patch.object(command, "newLine"),
                patch.object(command, "success") as success,
                patch.object(command, "error") as error,
            ):
                await command.handle(app)

            target = root / "app" / "services" / "billing" / "invoice_service.py"
            self.assertTrue(target.is_file())
            self.assertIn("class InvoiceService", target.read_text(encoding="utf-8"))
            self.assertTrue(success.called)
            error.assert_not_called()

    async def testMakeControllerGeneratesAsyncApiResourceActions(self) -> None:
        """Generate all resource actions with explicit JSON response types.

        Returns
        -------
        None
            Assertions verify method names, async declarations, and syntax.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            command = MakeHttpController()
            command.setArguments({"name": "api/invoice.py", "api": True})

            with (
                patch.object(command, "newLine"),
                patch.object(command, "success"),
                patch.object(command, "error") as error,
            ):
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
            error.assert_not_called()

    async def testMakeControllerCanGenerateAnInvokableAction(self) -> None:
        """Generate a single asynchronous ``__call__`` controller action.

        Returns
        -------
        None
            Assertions verify invokable syntax and the HTML response type.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            command = MakeHttpController()
            command.setArguments({"name": "health", "invoke": True})

            with (
                patch.object(command, "newLine"),
                patch.object(command, "success"),
                patch.object(command, "error") as error,
            ):
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
            error.assert_not_called()

    async def testMakeProviderAddsProviderPostfixOnce(self) -> None:
        """Add the provider suffix to filenames and class names once.

        Returns
        -------
        None
            Assertions verify generated provider names with and without an
            explicitly supplied suffix.
        """
        for index, name in enumerate(("cache", "billing/cache_provider.py")):
            with TemporaryDirectory() as temporary:
                root = Path(temporary)
                app = _Application(root)
                command = MakeProvider()
                command.setArguments({"name": name})

                with (
                    patch.object(command, "newLine"),
                    patch.object(command, "success"),
                    patch.object(command, "error") as error,
                ):
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
                error.assert_not_called()

    async def testMakeModelAndMailUseTheirApplicationDirectories(self) -> None:
        """Generate model and reusable mail templates in configured paths.

        Returns
        -------
        None
            Assertions verify model defaults and application injection.
        """
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _Application(root)
            for command_type, name in (
                (MakeModel, "user"),
                (MakeMail, "welcome"),
            ):
                command = command_type()
                command.setArguments({"name": name})
                with (
                    patch.object(command, "newLine"),
                    patch.object(command, "success"),
                    patch.object(command, "error") as error,
                ):
                    await command.handle(app)
                error.assert_not_called()

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
        """Render each make template and verify generated documentation.

        Returns
        -------
        None
            Assertions verify generated modules parse and document every class
            and method.
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
                command = command_type()
                arguments = {
                    "name": f"generated/file_{index}.py",
                    **extra_arguments,
                }
                command.setArguments(arguments)
                before = _get_python_sources(root)
                with (
                    patch.object(command, "newLine"),
                    patch.object(command, "success"),
                    patch.object(command, "error") as error,
                ):
                    if isinstance(command, MakeConsoleCommand):
                        await command.handle(app, _Reactor())
                    else:
                        await command.handle(app)

                generated = _get_python_sources(root) - before
                self.assertTrue(generated, command.signature)
                error.assert_not_called()
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
        """Expose all planned make commands through the core command registry.

        Returns
        -------
        None
            Assertions verify every planned signature is registered.
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
