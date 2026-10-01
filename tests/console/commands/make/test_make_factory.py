import argparse
import ast
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import get_ident
from typing import TYPE_CHECKING
from app.models.user import User
from orionis.console.commands.make.factory import MakeFactory
from orionis.console.core.commands import CORE_COMMANDS
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.support.types.sentinel import MISSING
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

class _Application:
    """Resolve the generator's configured directories without application boot."""

    __slots__ = ("_models_path", "basePath")

    def __init__(self, root: Path, models_path: str = "app/models") -> None:
        """Store the temporary project and model package paths.

        Parameters
        ----------
        root : Path
            Temporary application root directory.
        models_path : str, optional
            Model package relative to the root.
        """
        self.basePath = root
        self._models_path = models_path

    def path(self, key: str) -> Path:
        """Resolve a configured application directory.

        Parameters
        ----------
        key : str
            Core application path key.

        Returns
        -------
        Path
            Directory within the temporary application root.
        """
        relative = (
            self._models_path if key == "app_models" else CORE_APP_PATHS[key]
        )
        return self.basePath / relative

class _RecordedFactory(MakeFactory):
    """Capture command output with an explicit console test double."""

    def __init__(self) -> None:
        """Initialize independent argument and output collections."""
        super().__init__()
        self.successes: list[str] = []
        self.errors: list[str] = []
        self.timestamps: list[bool] = []

    def newLine(self, count: int = 1) -> None:
        """Consume visual spacing without writing terminal output.

        Parameters
        ----------
        count : int, optional
            Number of blank lines requested by the command.
        """

    def success(self, message: str, *, timestamp: bool = True) -> None:
        """Collect a command success message.

        Parameters
        ----------
        message : str
            User-facing command output.
        timestamp : bool, optional
            Console timestamp flag.
        """
        self.successes.append(message)
        self.timestamps.append(timestamp)

    def error(self, message: object, *, timestamp: bool = True) -> None:
        """Collect a command error message.

        Parameters
        ----------
        message : object
            Validation error or user-facing command output.
        timestamp : bool, optional
            Console timestamp flag.
        """
        self.errors.append(str(message))
        self.timestamps.append(timestamp)

class _ThreadRecordedFactory(_RecordedFactory):
    """Record the thread that owns stub rendering and file creation."""

    def createFiles(
        self,
        app: IApplication,
        name: str,
    ) -> tuple[tuple[str, str], ...]:
        """Record the worker identity before creating the requested factory.

        Parameters
        ----------
        app : IApplication
            Application resolving the generated file's paths.
        name : str
            Factory class or nested file name.

        Returns
        -------
        tuple of tuple of str and str
            Generated file label and application-relative path.
        """
        self.creation_thread = get_ident()
        return super().createFiles(app, name)

class TestMakeFactory(TestCase):
    """Verify factory generation, import conventions, and CLI registration."""

    async def testAsyncHandleCreatesFilesOutsideTheEventLoopThread(self) -> None:
        """Run stub rendering and writes in a worker without changing output."""
        with TemporaryDirectory() as temporary:
            command = _ThreadRecordedFactory()
            command.setArguments({"name": "UserFactory"})
            await command.handle(_Application(Path(temporary)))
            self.assertNotEqual(command.creation_thread, get_ident())
            self.assertEqual(len(command.successes), 1)
            self.assertEqual(command.errors, [])

    def testRegistersCommandAndParsesOptionalModel(self) -> None:
        """Register one factory command and parse the standard argument forms."""
        self.assertEqual(
            sum(command.signature == "make:factory" for command in CORE_COMMANDS),
            1,
        )
        parser = argparse.ArgumentParser()
        for argument in MakeFactory.arguments:
            argument.addToParser(parser)
        for flags in ([], ["--model=User"], ["-m", "User"]):
            parsed = parser.parse_args(["UserFactory", *flags])
            self.assertEqual(parsed.name, "UserFactory")
            self.assertEqual(parsed.model, "User" if flags else MISSING)

    async def testInfersModelAndCreatesSnakeCaseFile(self) -> None:
        """Infer User and generate a minimal, documented Python factory."""
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = _RecordedFactory()
            command.setArguments({"name": "UserFactory"})
            await command.handle(_Application(root))

            target = root / "database/factories/user_factory.py"
            content = target.read_text(encoding="utf-8")
            self.assertIn("from app.models.user import User", content)
            self.assertIn("from orionis.orm.factories import Factory", content)
            self.assertIn("class UserFactory(Factory[User]):", content)
            self.assertIn("model = User", content)
            self.assertIn("def definition(self) -> dict[str, Any]:", content)
            self.assertNotIn("{{", content)
            module = ast.parse(content)
            generated_class = next(
                node for node in module.body if isinstance(node, ast.ClassDef)
            )
            definition = next(
                node for node in generated_class.body
                if isinstance(node, ast.FunctionDef)
            )
            self.assertIsNotNone(ast.get_docstring(generated_class))
            self.assertIsNotNone(ast.get_docstring(definition))
            self.assertEqual(ast.literal_eval(definition.body[-1].value), {})
            self.assertEqual(len(command.successes), 1)
            self.assertEqual(command.errors, [])

    def testExplicitModelOverridesInference(self) -> None:
        """Generate a named scenario factory for an explicit application model."""
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = MakeFactory()
            command.setArguments({"model": "User"})
            command.createFiles(_Application(root), "AdminFactory")
            content = (root / "database/factories/admin_factory.py").read_text(
                encoding="utf-8",
            )
            self.assertIn("class AdminFactory(Factory[User]):", content)
            self.assertIn("from app.models.user import User", content)

    def testGeneratedFactoryImportsAndMakesTheRealModel(self) -> None:
        """Execute the generated skeleton against the real application model."""
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            MakeFactory().createFiles(_Application(root), "UserFactory")
            target = root / "database/factories/user_factory.py"
            spec = importlib.util.spec_from_file_location("generated_factory", target)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            factory = module.UserFactory(seed=42)
            user = factory.make(name="Factory user", email="factory@example.test")
            self.assertIsInstance(user, User)
            self.assertEqual(user.name, "Factory user")
            self.assertEqual(user.email, "factory@example.test")
            self.assertIsNone(user.id)

    def testNestedNamesAndSuffixesFollowPythonConventions(self) -> None:
        """Preserve nested packages and add the factory suffix exactly once."""
        for name in (
            "sales/OrderFactory",
            "sales/order_factory.py",
            "sales/Order",
            "sales\\order.py",
        ):
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                root = Path(temporary)
                MakeFactory().createFiles(_Application(root), name)
                target = root / "database/factories/sales/order_factory.py"
                content = target.read_text(encoding="utf-8")
                self.assertIn("class OrderFactory(Factory[Order]):", content)
                self.assertIn("from app.models.sales.order import Order", content)

    def testExplicitNestedModelUsesConfiguredPackage(self) -> None:
        """Resolve the import from the actual configured models directory."""
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = MakeFactory()
            command.setArguments({"model": "billing/Invoice"})
            command.createFiles(_Application(root, "domain/models"), "PaidInvoice")
            content = (
                root / "database/factories/paid_invoice_factory.py"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "from domain.models.billing.invoice import Invoice",
                content,
            )
            self.assertIn("class PaidInvoiceFactory(Factory[Invoice]):", content)

    def testAcronymsRetainTheirClassName(self) -> None:
        """Keep explicit acronym class names while producing snake case files."""
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            MakeFactory().createFiles(_Application(root), "APIKeyFactory")
            content = (root / "database/factories/api_key_factory.py").read_text(
                encoding="utf-8",
            )
            self.assertIn("class APIKeyFactory(Factory[APIKey]):", content)
            self.assertIn("from app.models.api_key import APIKey", content)

    async def testExistingFactoryIsNeverOverwritten(self) -> None:
        """Report a duplicate target without replacing application code."""
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "database/factories/user_factory.py"
            target.parent.mkdir(parents=True)
            target.write_text("# User-owned factory\n", encoding="utf-8")
            command = _RecordedFactory()
            command.setArguments({"name": "UserFactory"})
            await command.handle(_Application(root))
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                "# User-owned factory\n",
            )
            self.assertEqual(command.successes, [])
            self.assertEqual(len(command.errors), 1)
            self.assertIn("already exists", command.errors[0])

    def testUnsafeNamesFailBeforeWriting(self) -> None:
        """Reject traversals, invalid identifiers, and empty inferred models."""
        for name in (
            "../User", "/User", "C:/User", "a//User", "Factory", "class",
            "Us\u00e9r", "User\u0661",
        ):
            with self.subTest(name=name), TemporaryDirectory() as temporary:
                root = Path(temporary)
                with self.assertRaises(ValueError):
                    MakeFactory().createFiles(_Application(root), name)
                self.assertEqual(list(root.rglob("*.py")), [])

    def testInvalidModelNamesFailBeforeWriting(self) -> None:
        """Reject model names that could create invalid or injected imports."""
        for model in (
            "", "../User", "User; pass", "user\nimport os", "class", "False", 1,
            "Us\u00e9r", "User\u0661",
        ):
            with self.subTest(model=model), TemporaryDirectory() as temporary:
                root = Path(temporary)
                command = MakeFactory()
                command.setArguments({"model": model})
                with self.assertRaises((TypeError, ValueError)):
                    command.createFiles(_Application(root), "UserFactory")
                self.assertEqual(list(root.rglob("*.py")), [])

    async def testMissingNameUsesTheStandardCommandErrorFlow(self) -> None:
        """Report missing positional input through inherited generator output."""
        with TemporaryDirectory() as temporary:
            command = _RecordedFactory()
            await command.handle(_Application(Path(temporary)))
            self.assertEqual(command.errors, ["The 'name' argument is required."])
            self.assertEqual(command.successes, [])
