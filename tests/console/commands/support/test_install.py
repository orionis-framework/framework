import argparse
import re
import sys
import tomllib
import venv
from asyncio import CancelledError, create_subprocess_exec, to_thread
from asyncio.subprocess import DEVNULL, PIPE, STDOUT
from base64 import urlsafe_b64encode
from csv import writer
from hashlib import sha256
from importlib.util import find_spec
from io import StringIO
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from zipfile import ZipFile
from rich.console import Console as RichConsole
from orionis.console.commands.support import install as install_module
from orionis.console.commands.support.install import InstallCommand
from orionis.console.core.commands import CORE_COMMANDS
from orionis.test import TestCase

_PROBE_NAME = "orionis_install_probe"

_MANIFEST = """\
[project]
name = "sample-app"
dependencies = ["rich>=15"]

[project.optional-dependencies]
s3 = ["boto3>=1", "boto3>=1"]
mysql = ["aiomysql>=0.3", "pymysql>=1"]

[dependency-groups]
lint = ["ruff>=0.16"]
dev = [{include-group = "lint"}, "pytest>=8", "ruff>=0.16"]

[tool.orionis.packages]
"extra:s3" = "Amazon S3 file storage."
"extra:mysql" = "MySQL and MariaDB connections."
"group:lint" = "Static code checks."
"group:dev" = "Development and quality checks."
"""

class _StubApp:
    """Expose the application root to the install command."""

    __slots__ = ("basePath",)

    def __init__(self, root: Path) -> None:
        """Store the application root.

        Parameters
        ----------
        root : Path
            Directory containing the application manifest.

        Returns
        -------
        None
            Initialize the root consumed by the command.
        """
        self.basePath = root

class _StubProcess:
    """Record child cleanup and provide deterministic installer results."""

    __slots__ = ("failure", "output", "returncode", "terminated", "waited")

    def __init__(self) -> None:
        """Prepare a successful installer response.

        Returns
        -------
        None
            Initialize output, status and child cleanup counters.
        """
        self.failure: BaseException | None = None
        self.output = b"Installed selected packages.\n"
        self.returncode: int | None = 0
        self.terminated = False
        self.waited = False

    async def communicate(self) -> tuple[bytes, None]:
        """Return output or raise the configured execution failure.

        Returns
        -------
        tuple[bytes, None]
            Captured output and the absent separate stderr stream.

        Raises
        ------
        BaseException
            If the test configures an execution failure.
        """
        if self.failure is not None:
            raise self.failure
        return self.output, None

    def terminate(self) -> None:
        """Record termination of the installer process.

        Returns
        -------
        None
            Mark the child as terminated.
        """
        self.terminated = True

    async def wait(self) -> int:
        """Record waiting for the installer process to exit.

        Returns
        -------
        int
            Simulated child exit code.
        """
        self.waited = True
        self.returncode = 130
        return self.returncode

class _RecordingInstaller:
    """Capture the executable, interpreter and arguments used to install."""

    __slots__ = ("calls", "failure", "process", "uv_path")

    def __init__(self) -> None:
        """Prepare a discoverable uv executable and a successful process.

        Returns
        -------
        None
            Initialize process creation and command argument recording.
        """
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []
        self.failure: OSError | None = None
        self.process = _StubProcess()
        self.uv_path: str | None = "uv-test-executable"

    def which(self, name: str) -> str | None:
        """Resolve only the uv executable used by the command.

        Parameters
        ----------
        name : str
            Executable requested by the command.

        Returns
        -------
        str | None
            Simulated uv path or None when unavailable.
        """
        return self.uv_path if name == "uv" else None

    async def createProcess(self, *args: str, **kwargs: object) -> _StubProcess:
        """Record process arguments and return the controlled child.

        Parameters
        ----------
        *args : str
            Executable and individual argument strings.
        **kwargs : object
            Working directory and standard stream settings.

        Returns
        -------
        _StubProcess
            Process used to report output, exit status or cancellation.

        Raises
        ------
        OSError
            If process creation is configured to fail.
        """
        self.calls.append((args, kwargs))
        if self.failure is not None:
            raise self.failure
        return self.process

class _RecordingPrompt:
    """Supply selection input without accessing the real terminal."""

    __slots__ = ("answer", "calls", "failure")

    def __init__(self) -> None:
        """Prepare a canceled selection and empty prompt history.

        Returns
        -------
        None
            Initialize the answer, failure and recorded prompt questions.
        """
        self.answer = "0"
        self.calls: list[str] = []
        self.failure: BaseException | None = None

    def ask(self, question: str, **_kwargs: object) -> str:
        """Record a selection question and supply controlled input.

        Parameters
        ----------
        question : str
            Selection prompt presented by the command.
        **_kwargs : object
            Rich console and default answer settings.

        Returns
        -------
        str
            Configured selection answer.

        Raises
        ------
        BaseException
            If input is configured to close or be interrupted.
        """
        self.calls.append(question)
        if self.failure is not None:
            raise self.failure
        return self.answer

class _RecordingConfirm:
    """Supply confirmation input without accessing the real terminal."""

    __slots__ = ("answer", "calls")

    def __init__(self) -> None:
        """Prepare an affirmative answer and empty confirmation history.

        Returns
        -------
        None
            Initialize the confirmation answer and recorded questions.
        """
        self.answer = True
        self.calls: list[str] = []

    def ask(self, question: str, **_kwargs: object) -> bool:
        """Record a confirmation question and return the configured answer.

        Parameters
        ----------
        question : str
            Installation confirmation presented by the command.
        **_kwargs : object
            Rich console and default confirmation settings.

        Returns
        -------
        bool
            Whether installation should proceed.
        """
        self.calls.append(question)
        return self.answer

class TestInstallCommand(TestCase):
    """Verify the catalog, selection and interpreter-scoped installation."""

    def setUp(self) -> None:
        """Create an isolated project and substitute interactive boundaries.

        Returns
        -------
        None
            Capture output and isolate installer and terminal interactions.
        """
        temporary = TemporaryDirectory(prefix="orionis install ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = _StubApp(self.root)
        self.package_manifest = (
            self.root / "site-packages" / "orionis" / "pyproject.toml"
        )
        self.source_manifest = self.root / "framework" / "pyproject.toml"
        self.output = StringIO()
        self.command = InstallCommand()
        self.command._console = RichConsole(file=self.output, width=120)
        self.command.setArguments({"list": True})
        self.installer = _RecordingInstaller()
        self.prompt = _RecordingPrompt()
        self.confirm = _RecordingConfirm()
        self.original_bindings = {
            name: getattr(install_module, name)
            for name in (
                "which", "create_subprocess_exec", "Prompt", "Confirm",
                "_PACKAGE_MANIFEST", "_SOURCE_MANIFEST",
            )
        }
        install_module.__dict__.update(
            which=self.installer.which,
            create_subprocess_exec=self.installer.createProcess,
            Prompt=self.prompt,
            Confirm=self.confirm,
            _PACKAGE_MANIFEST=self.package_manifest,
            _SOURCE_MANIFEST=self.source_manifest,
        )

    def tearDown(self) -> None:
        """Restore installer and prompt bindings after each scenario.

        Returns
        -------
        None
            Restore the real module globals for subsequent tests.
        """
        install_module.__dict__.update(self.original_bindings)

    def _writeManifest(self, content: str = _MANIFEST) -> None:
        """Write the project manifest for a test scenario.

        Parameters
        ----------
        content : str, optional
            TOML declarations to expose to the command.

        Returns
        -------
        None
            Create the manifest in the temporary application root.
        """
        (self.root / "pyproject.toml").write_text(content, encoding="utf-8")

    def _setSelection(
        self,
        *names: str,
        confirmed: bool = True,
        interactive: bool = False,
    ) -> None:
        """Configure selected options and terminal confirmation behavior.

        Parameters
        ----------
        *names : str
            Explicit CLI selections.
        confirmed : bool, optional
            Whether the command receives the --yes flag.
        interactive : bool, optional
            Whether the captured Rich console accepts prompts.

        Returns
        -------
        None
            Set command arguments and the simulated terminal capability.
        """
        self.command.setArguments({
            "list": False, "options": list(names), "yes": confirmed,
        })
        self.command._console.is_interactive = interactive

    async def testFallsBackToTheApplicationManifest(self) -> None:
        """List declared options without exposing base dependencies as extras.

        Returns
        -------
        None
            Assertions verify the purposes and manifest path without requirements.
        """
        self._writeManifest()

        self.assertEqual(await self.command.handle(self.app), 0)
        rendered = self.output.getvalue()
        for expected in (
            "s3", "mysql", "dev", "lint", "Amazon S3 file storage",
            "MySQL and MariaDB connections", "Development and quality checks",
            str(self.root / "pyproject.toml"),
        ):
            self.assertIn(expected, rendered)
        for requirement in ("rich>=15", "boto3>=1", "pymysql>=1", "pytest>=8"):
            self.assertNotIn(requirement, rendered)
        self.assertEqual(self.installer.calls, [])
        self.assertEqual(self.prompt.calls, [])
        self.assertEqual(self.confirm.calls, [])

    async def testPrefersTheBundledFrameworkManifest(self) -> None:
        """Ignore application extras when the installed framework has its manifest.

        Returns
        -------
        None
            The catalog and installer use only the package-owned declarations.
        """
        self._writeManifest('[project.optional-dependencies]\napplication = ["demo"]\n')
        self.package_manifest.parent.mkdir(parents=True)
        self.package_manifest.write_text(_MANIFEST, encoding="utf-8")
        self.source_manifest.parent.mkdir(parents=True)
        self.source_manifest.write_text(
            '[project.optional-dependencies]\nsource = ["another-demo"]\n',
            encoding="utf-8",
        )
        self._setSelection("s3")

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(self.installer.calls[0][0][6:], ("boto3>=1",))
        self.assertEqual(
            self.installer.calls[0][1]["cwd"], self.package_manifest.parent,
        )
        rendered = self.output.getvalue()
        self.assertIn("Amazon S3 file storage", rendered)
        self.assertNotIn("application", rendered)
        self.assertNotIn("another-demo", rendered)

    async def testUsesTheFrameworkSourceManifestBeforeTheApplication(self) -> None:
        """Use the canonical checkout manifest during editable development.

        Returns
        -------
        None
            The source manifest remains preferred without a bundled package copy.
        """
        self._writeManifest('[project.optional-dependencies]\napplication = ["demo"]\n')
        self.source_manifest.parent.mkdir(parents=True)
        self.source_manifest.write_text(_MANIFEST, encoding="utf-8")
        self._setSelection("mysql")

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(
            self.installer.calls[0][0][6:], ("aiomysql>=0.3", "pymysql>=1"),
        )
        self.assertEqual(self.installer.calls[0][1]["cwd"], self.source_manifest.parent)

    async def testReportsInvalidFrameworkTomlWithoutFallingBack(self) -> None:
        """Keep a broken package manifest visible instead of reading application extras.

        Returns
        -------
        None
            Invalid bundled TOML fails before any installer is invoked.
        """
        self._writeManifest()
        self.package_manifest.parent.mkdir(parents=True)
        self.package_manifest.write_text("[project\n", encoding="utf-8")

        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertEqual(self.installer.calls, [])
        self.assertNotIn("ORIONIS", self.output.getvalue())

    def testEveryFrameworkOptionHasAPurpose(self) -> None:
        """Keep human-readable purposes aligned with all framework extras and groups.

        Returns
        -------
        None
            Every declared installation option has nonempty purpose metadata.
        """
        project_path = Path(__file__).resolve().parents[4] / "pyproject.toml"
        manifest = tomllib.loads(project_path.read_text(encoding="utf-8"))
        expected = {
            f"extra:{name}" for name in manifest["project"]["optional-dependencies"]
        } | {f"group:{name}" for name in manifest["dependency-groups"]}
        purposes = manifest["tool"]["orionis"]["packages"]
        self.assertEqual(set(purposes), expected)
        for purpose in purposes.values():
            self.assertIsInstance(purpose, str)
            self.assertTrue(purpose.strip())

    def testCatalogKeepsOneRowPerOptionAcrossTerminalWidths(self) -> None:
        """Keep bundles compact and numbered without exceeding terminal width.

        Returns
        -------
        None
            Assertions verify purposes, row counts and width constraints.
        """
        options = {
            "extra:storage": tuple(
                f"cloud-driver-{index}>=1.0" for index in range(7)
            ),
            "group:dev": ("ruff>=0.16", "pytest>=8"),
            "extra:empty": (),
        }
        self.command._purposes = {
            "extra:storage": "Cloud file storage.",
            "group:dev": "Development tools.",
            "extra:empty": "Unused feature.",
        }
        for width in (40, 80, 120):
            self.output.seek(0)
            self.output.truncate()
            self.command._console = RichConsole(file=self.output, width=width)

            self.command._InstallCommand__renderOptions(
                self.root / "pyproject.toml", options,
            )

            lines = self.output.getvalue().splitlines()
            rows = [line for line in lines if re.match(r"^\s*\d+\s+", line)]
            self.assertEqual([int(row.split()[0]) for row in rows], [1, 2, 3])
            self.assertIn("storage", rows[0])
            self.assertIn("group:dev", rows[1])
            self.assertIn("Unused feature.", rows[2])
            self.assertNotIn("cloud-driver", self.output.getvalue())
            self.assertNotIn("pytest", self.output.getvalue())
            self.assertLessEqual(len(lines), len(options) + 7)
            for line in lines:
                self.assertLessEqual(len(line), width)

    def testExpandsGroupIncludesAndDeduplicatesRequirements(self) -> None:
        """Resolve included groups in declaration order without duplicates.

        Returns
        -------
        None
            Assertions verify expanded extras and development requirements.
        """
        self._writeManifest()

        options = self.command._InstallCommand__loadOptions(
            self.root / "pyproject.toml",
        )

        self.assertEqual(options["extra:s3"], ("boto3>=1",))
        self.assertEqual(options["group:dev"], ("ruff>=0.16", "pytest>=8"))

    async def testReportsAMissingManifest(self) -> None:
        """Fail clearly when the application manifest does not exist.

        Returns
        -------
        None
            Assertions verify a nonzero status and the missing file path.
        """
        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertIn("pyproject.toml", self.output.getvalue())

    async def testReportsInvalidToml(self) -> None:
        """Reject malformed TOML instead of displaying a partial catalog.

        Returns
        -------
        None
            Assertions verify parsing errors return a failure status.
        """
        self._writeManifest("[project\n")

        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertNotIn("ORIONIS", self.output.getvalue())

    async def testRejectsInvalidDependencyTables(self) -> None:
        """Reject dependency sections that are not TOML tables.

        Returns
        -------
        None
            Assertions verify project, extras and group table validation.
        """
        for content in (
            "project = []\n",
            "[project]\noptional-dependencies = []\n",
            "dependency-groups = []\n",
        ):
            self._writeManifest(content)
            self.assertEqual(await self.command.handle(self.app), 1)
        self.assertIn("must be a TOML table", self.output.getvalue())

    async def testRejectsInvalidPackageRequirements(self) -> None:
        """Reject non-list declarations and invalid requirement values.

        Returns
        -------
        None
            Assertions verify requirements must be nonempty strings.
        """
        for value in ('"boto3"', "[42]", '["   "]'):
            self._writeManifest(f"[project.optional-dependencies]\ns3 = {value}\n")
            self.assertEqual(await self.command.handle(self.app), 1)
        self.assertIn("package requirements", self.output.getvalue())

    async def testRejectsCyclicGroupIncludes(self) -> None:
        """Report cycles rather than recursively expanding groups forever.

        Returns
        -------
        None
            Assertions verify a cyclic group inclusion returns failure.
        """
        self._writeManifest(
            '[dependency-groups]\na = [{include-group = "b"}]\n'
            'b = [{include-group = "a"}]\n',
        )

        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertIn("Cyclic dependency group", self.output.getvalue())

    async def testRejectsMissingIncludedGroups(self) -> None:
        """Reject includes referring to an undeclared dependency group.

        Returns
        -------
        None
            Assertions verify the missing group is identified.
        """
        self._writeManifest(
            '[dependency-groups]\ndev = [{include-group = "missing"}]\n',
        )

        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertIn("'missing' does not exist", self.output.getvalue())

    async def testRejectsMalformedGroupEntries(self) -> None:
        """Reject invalid group lists, requirements and include directives.

        Returns
        -------
        None
            Assertions verify malformed group entries return failure.
        """
        for value in ('"ruff"', "[42]", "[{include-group = 42}]", "[{other = 1}]"):
            self._writeManifest(f"[dependency-groups]\ndev = {value}\n")
            self.assertEqual(await self.command.handle(self.app), 1)

    async def testAcceptsAProjectWithoutOptionalDependencies(self) -> None:
        """Display an empty catalog for a project without extras or groups.

        Returns
        -------
        None
            Assertions verify a harmless empty catalog succeeds.
        """
        self._writeManifest('[project]\nname = "sample-app"\n')

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertIn("No optional dependencies", self.output.getvalue())

    def testRegistersTheCommandInTheCoreCatalog(self) -> None:
        """Expose packages to the same loader used by Reactor.

        Returns
        -------
        None
            Assertions verify the command is registered exactly once.
        """
        self.assertEqual(CORE_COMMANDS.count(InstallCommand), 1)
        self.assertEqual(InstallCommand.signature, "packages")

    def testParsesNamesAndAutomationFlags(self) -> None:
        """Parse multiple option names and the confirmation flag with argparse.

        Returns
        -------
        None
            Assertions verify CLI defaults and explicit option selections.
        """
        parser = argparse.ArgumentParser()
        for argument in InstallCommand.arguments:
            argument.addToParser(parser)

        parsed = parser.parse_args(["s3", "group:dev", "--yes"])

        self.assertEqual(parsed.options, ["s3", "group:dev"])
        self.assertTrue(parsed.yes)
        self.assertFalse(parsed.list)
        self.assertEqual(parser.parse_args([]).options, [])
        self.assertTrue(parser.parse_args(["--list"]).list)

    async def testInstallsExtrasIntoTheRunningInterpreter(self) -> None:
        """Target the exact Reactor interpreter and preserve argument boundaries.

        Returns
        -------
        None
            Assertions verify uv, Python, cwd and individual requirements.
        """
        self._writeManifest()
        self._setSelection("s3", "mysql")

        self.assertEqual(await self.command.handle(self.app), 0)

        args, kwargs = self.installer.calls[0]
        self.assertEqual(args, (
            "uv-test-executable", "pip", "install", "--python", sys.executable,
            "--", "boto3>=1", "aiomysql>=0.3", "pymysql>=1",
        ))
        self.assertEqual(kwargs, {
            "cwd": self.root, "stdin": DEVNULL, "stdout": PIPE, "stderr": STDOUT,
        })
        self.assertIn("Packages installed successfully", self.output.getvalue())
        self.assertEqual(self.prompt.calls, [])
        self.assertEqual(self.confirm.calls, [])

    async def testInstallsAnExpandedDependencyGroup(self) -> None:
        """Install requirements supplied by a group and its includes.

        Returns
        -------
        None
            Assertions verify group references resolve to installable packages.
        """
        self._writeManifest()
        self._setSelection("group:dev")

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(
            self.installer.calls[0][0][-2:], ("ruff>=0.16", "pytest>=8"),
        )

    async def testAcceptsInteractiveNumbersAndCommaSeparatedSelections(self) -> None:
        """Select multiple catalog rows and confirm using Rich prompts.

        Returns
        -------
        None
            Assertions verify prompts and the matching package installation.
        """
        self._writeManifest()
        self._setSelection(confirmed=False, interactive=True)
        self.prompt.answer = "1, 2"

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(len(self.prompt.calls), 1)
        self.assertEqual(len(self.confirm.calls), 1)
        self.assertEqual(self.installer.calls[0][0][-3:], (
            "boto3>=1", "aiomysql>=0.3", "pymysql>=1",
        ))

    async def testDeduplicatesRepeatedOptionsAndOverlappingGroups(self) -> None:
        """Install each identical requirement only once across selected options.

        Returns
        -------
        None
            Assertions verify repeated keys and shared requirements are folded.
        """
        self._writeManifest()
        self._setSelection("dev", "group:dev", "lint")

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(len(self.installer.calls), 1)
        self.assertEqual(
            self.installer.calls[0][0][6:], ("ruff>=0.16", "pytest>=8"),
        )

    async def testRejectsUnknownNamesAndOutOfRangeNumbers(self) -> None:
        """Reject selections outside the catalog before invoking uv.

        Returns
        -------
        None
            Assertions verify invalid selections fail without side effects.
        """
        self._writeManifest()
        for name in ("missing", "999", "-1"):
            self._setSelection(name)
            self.assertEqual(await self.command.handle(self.app), 1)
        self.assertEqual(self.installer.calls, [])
        self.assertIn("Unknown installation option", self.output.getvalue())

    async def testRequiresNamespacedKeysForAmbiguousNames(self) -> None:
        """Disambiguate an extra and a dependency group sharing one name.

        Returns
        -------
        None
            Assertions verify a bare name fails and an explicit key succeeds.
        """
        self._writeManifest(
            '[project.optional-dependencies]\ndev = ["pytest"]\n'
            '[dependency-groups]\ndev = ["ruff"]\n',
        )
        self._setSelection("dev")

        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertEqual(self.installer.calls, [])
        self.assertIn("Ambiguous option", self.output.getvalue())

        self._setSelection("extra:dev")
        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(self.installer.calls[0][0][-1], "pytest")

    async def testPreservesExtrasAndEnvironmentMarkersAsOneArgument(self) -> None:
        """Leave requirement extras and markers intact for uv to evaluate.

        Returns
        -------
        None
            Assertions verify one argument contains the complete requirement.
        """
        requirement = "demo[cloud]>=1; sys_platform == 'win32'"
        self._writeManifest(
            f'[project.optional-dependencies]\ncloud = ["{requirement}"]\n',
        )
        self._setSelection("cloud")

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(self.installer.calls[0][0][6:], (requirement,))
        self.assertNotIn("demo[cloud]", self.output.getvalue())

    async def testKeepsManifestValuesOutsideInstallerFlags(self) -> None:
        """Separate untrusted dependency values from uv's command options.

        Returns
        -------
        None
            Assertions verify a manifest value cannot become an installer flag.
        """
        self._writeManifest(
            '[project.optional-dependencies]\ninvalid = ["--target=elsewhere"]\n',
        )
        self._setSelection("invalid")

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(
            self.installer.calls[0][0][5:], ("--", "--target=elsewhere"),
        )

    async def testDeclinedConfirmationDoesNotInstall(self) -> None:
        """Cancel installation when the user declines the confirmation.

        Returns
        -------
        None
            Assertions verify cancellation succeeds without launching uv.
        """
        self._writeManifest()
        self._setSelection("s3", confirmed=False, interactive=True)
        self.confirm.answer = False

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(self.installer.calls, [])
        self.assertIn("Installation canceled", self.output.getvalue())

    async def testZeroCancelsTheInteractiveSelection(self) -> None:
        """Cancel before confirmation when the selection prompt returns zero.

        Returns
        -------
        None
            Assertions verify no confirmation or installation is attempted.
        """
        self._writeManifest()
        self._setSelection(confirmed=False, interactive=True)

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(self.installer.calls, [])
        self.assertEqual(self.confirm.calls, [])

    async def testOnlyListsOptionsWhenTheTerminalIsNotInteractive(self) -> None:
        """Display the catalog without attempting to prompt a closed terminal.

        Returns
        -------
        None
            Assertions verify listing succeeds without reading stdin.
        """
        self._writeManifest()
        self._setSelection(confirmed=False)

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(self.prompt.calls, [])
        self.assertEqual(self.installer.calls, [])
        self.assertIn("Pass option names and --yes", self.output.getvalue())

    async def testRequiresConfirmationForNonInteractiveInstallation(self) -> None:
        """Require --yes when installing through a non-interactive invocation.

        Returns
        -------
        None
            Assertions verify no process is launched without consent.
        """
        self._writeManifest()
        self._setSelection("s3", confirmed=False)

        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertEqual(self.confirm.calls, [])
        self.assertEqual(self.installer.calls, [])
        self.assertIn("Confirmation required", self.output.getvalue())

    async def testClosedOrInterruptedPromptsReturnAnInterruptionStatus(self) -> None:
        """Translate closed input and user interruption to status 130.

        Returns
        -------
        None
            Assertions verify neither prompt failure starts an installation.
        """
        self._writeManifest()
        self._setSelection(confirmed=False, interactive=True)
        for failure in (EOFError(), KeyboardInterrupt()):
            self.prompt.failure = failure
            self.assertEqual(await self.command.handle(self.app), 130)
        self.assertEqual(self.installer.calls, [])

    async def testEmptyExtrasDoNotInvokeTheInstaller(self) -> None:
        """Skip process creation for an option declaring no packages.

        Returns
        -------
        None
            Assertions verify an empty selection remains a harmless no-op.
        """
        self._writeManifest("[project.optional-dependencies]\nempty = []\n")
        self._setSelection("empty")

        self.assertEqual(await self.command.handle(self.app), 0)
        self.assertEqual(self.installer.calls, [])
        self.assertIn("contains no packages", self.output.getvalue())

    async def testReportsAMissingUvExecutable(self) -> None:
        """Report the required package manager when uv is unavailable.

        Returns
        -------
        None
            Assertions verify missing uv fails without launching a child.
        """
        self._writeManifest()
        self._setSelection("s3")
        self.installer.uv_path = None

        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertIn("uv is required", self.output.getvalue())
        self.assertEqual(self.installer.calls, [])

    async def testReportsInstallerStartupFailures(self) -> None:
        """Return a clear failure when the uv process cannot be started.

        Returns
        -------
        None
            Assertions verify the original startup error is reported.
        """
        self._writeManifest()
        self._setSelection("s3")
        self.installer.failure = OSError("installer startup failed")

        self.assertEqual(await self.command.handle(self.app), 1)
        self.assertIn("installer startup failed", self.output.getvalue())
        self.assertNotIn("Packages installed successfully", self.output.getvalue())

    async def testPropagatesInstallerFailuresAndPreservesItsOutput(self) -> None:
        """Return uv's positive failure status and display its diagnostic output.

        Returns
        -------
        None
            Assertions verify failures are not reported as successful installs.
        """
        self._writeManifest()
        self._setSelection("s3")
        self.installer.process.returncode = 7
        self.installer.process.output = b"Dependency resolution failed.\xff"

        self.assertEqual(await self.command.handle(self.app), 7)
        self.assertIn("Dependency resolution failed", self.output.getvalue())
        self.assertNotIn("Packages installed successfully", self.output.getvalue())

    async def testMapsSignalTerminationToAFailureStatus(self) -> None:
        """Convert negative child return codes into a portable CLI failure.

        Returns
        -------
        None
            Assertions verify signal termination never returns success.
        """
        self._writeManifest()
        self._setSelection("s3")
        self.installer.process.returncode = -9
        self.installer.process.output = b""

        self.assertEqual(await self.command.handle(self.app), 1)

    async def testStopsAndReapsTheChildWhenInstallationIsCanceled(self) -> None:
        """Terminate and wait for the installer before reporting interruption.

        Returns
        -------
        None
            Assertions verify cancellation does not leave a child running.
        """
        self._writeManifest()
        self._setSelection("s3")
        self.installer.process.returncode = None
        self.installer.process.failure = CancelledError()

        self.assertEqual(await self.command.handle(self.app), 130)
        self.assertTrue(self.installer.process.terminated)
        self.assertTrue(self.installer.process.waited)

    async def testRejectsInvalidOptionPurposes(self) -> None:
        """Reject malformed purpose metadata instead of printing package names.

        Returns
        -------
        None
            Invalid tables and descriptions fail without invoking the installer.
        """
        for value in ('"invalid"', '{"extra:s3" = 42}', '{"extra:s3" = "   "}'):
            self._writeManifest(f"[tool.orionis]\npackages = {value}\n")
            self.assertEqual(await self.command.handle(self.app), 1)
        self.assertEqual(self.installer.calls, [])

class TestInstallIntegration(TestCase):
    """Exercise real uv installation without network access or project mutation."""

    def setUp(self) -> None:
        """Create a pip-free target environment and a local wheel fixture.

        Returns
        -------
        None
            Prepare an isolated installation target and application manifest.
        """
        if which("uv") is None:
            self.skipTest("uv is required for the offline installation test.")
        temporary = TemporaryDirectory(prefix="orionis install probe ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = self.root / "venv"
        venv.EnvBuilder(with_pip=False).create(environment)
        executable = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
        self.python_path = environment / executable
        wheel_path = self._createWheel()
        self.manifest_path = self.root / "pyproject.toml"
        self.manifest_content = (
            '[project]\nname = "install-probe-app"\n'
            '[project.optional-dependencies]\n'
            f'probe = ["{_PROBE_NAME} @ {wheel_path.as_uri()}"]\n'
        )
        self.manifest_path.write_text(self.manifest_content, encoding="utf-8")
        self.app = _StubApp(self.root)
        self.output = StringIO()
        self.command = InstallCommand()
        self.command._console = RichConsole(file=self.output, width=120)
        self.command.setArguments({"options": ["probe"], "yes": True})
        self.original_sys = install_module.sys
        self.original_manifests = {
            name: getattr(install_module, name)
            for name in ("_PACKAGE_MANIFEST", "_SOURCE_MANIFEST")
        }
        install_module.__dict__["sys"] = SimpleNamespace(
            executable=str(self.python_path),
        )
        install_module.__dict__.update(
            _PACKAGE_MANIFEST=self.root / "missing-package" / "pyproject.toml",
            _SOURCE_MANIFEST=self.root / "missing-source" / "pyproject.toml",
        )

    def tearDown(self) -> None:
        """Restore the install command's interpreter module reference.

        Returns
        -------
        None
            Restore production interpreter selection before project cleanup.
        """
        install_module.__dict__["sys"] = self.original_sys
        install_module.__dict__.update(self.original_manifests)

    def _createWheel(self) -> Path:
        """Build a valid dependency-free wheel using standard library writers.

        Returns
        -------
        Path
            Wheel fixture containing the probe module and distribution metadata.

        Raises
        ------
        OSError
            If the wheel cannot be written to the temporary project.
        """
        dist_info = f"{_PROBE_NAME}-0.0.1.dist-info"
        contents = {
            f"{_PROBE_NAME}/__init__.py": "VALUE = 'isolated installation'\n",
            f"{dist_info}/METADATA": (
                "Metadata-Version: 2.1\n"
                f"Name: {_PROBE_NAME}\nVersion: 0.0.1\n"
            ),
            f"{dist_info}/WHEEL": (
                "Wheel-Version: 1.0\nGenerator: orionis-test\n"
                "Root-Is-Purelib: true\nTag: py3-none-any\n"
            ),
        }
        records = StringIO(newline="")
        record_writer = writer(records)
        for name, content in contents.items():
            data = content.encode("utf-8")
            digest = (
                urlsafe_b64encode(sha256(data).digest()).decode("ascii").rstrip("=")
            )
            record_writer.writerow((name, f"sha256={digest}", len(data)))
        record_name = f"{dist_info}/RECORD"
        record_writer.writerow((record_name, "", ""))

        wheel_path = self.root / f"{_PROBE_NAME}-0.0.1-py3-none-any.whl"
        with ZipFile(wheel_path, "w") as wheel:
            for name, content in contents.items():
                wheel.writestr(name, content)
            wheel.writestr(record_name, records.getvalue())
        return wheel_path

    async def testInstallsALocalWheelIntoOnlyTheSelectedEnvironment(self) -> None:
        """Install a local package into a pip-free venv and verify its import.

        Returns
        -------
        None
            Assertions verify the package, interpreter and unchanged manifest.
        """
        self.assertEqual(
            await self.command.handle(self.app), 0, self.output.getvalue(),
        )
        process = await create_subprocess_exec(
            str(self.python_path), "-I", "-B", "-c",
            f"import {_PROBE_NAME}; print({_PROBE_NAME}.VALUE)",
            stdout=PIPE, stderr=STDOUT,
        )
        output, _ = await process.communicate()

        self.assertEqual(process.returncode, 0, output.decode("utf-8"))
        self.assertEqual(output.decode("utf-8").strip(), "isolated installation")
        self.assertIsNone(find_spec(_PROBE_NAME))
        self.assertEqual(
            await to_thread(self.manifest_path.read_text, encoding="utf-8"),
            self.manifest_content,
        )
        self.assertFalse((self.root / "uv.lock").exists())

    async def testRejectsARequirementThatLooksLikeAnInstallerFlag(self) -> None:
        """Reject a malformed requirement without treating it as a uv option.

        Returns
        -------
        None
            Assertions verify no installation target can be injected.
        """
        await to_thread(
            self.manifest_path.write_text,
            '[project.optional-dependencies]\nprobe = ["--target=elsewhere"]\n',
            encoding="utf-8",
        )

        self.assertGreater(await self.command.handle(self.app), 0)
        self.assertIn("--target=elsewhere", self.output.getvalue())
        self.assertFalse((self.root / "elsewhere").exists())
        self.assertNotIn("Packages installed successfully", self.output.getvalue())
