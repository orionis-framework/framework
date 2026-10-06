import json
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from orionis.test import TestCase

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENTRY_POINT = (
    "import os, sys; "
    "sys.path[:] = [path for path in sys.path if path]; "
    "os.environ['ORIONIS_CLI_TEST_PID'] = str(os.getpid()); "
    "from orionis.console.cli import main; "
    "sys.dont_write_bytecode = False; "
    "raise SystemExit(main())"
)
_BOOTSTRAP_SOURCE = """import json
import os
import subprocess
import sys
from pathlib import Path
from orionis.console.stdio import protocol_stdout

print("bootstrap diagnostic")
_BYTECODE_DISABLED = sys.dont_write_bytecode

class Application:
    async def handleCommand(self, arguments: list[str]) -> int:
        print("command diagnostic")
        sys.stderr.write("application stderr\\n")
        child_bytecode_disabled = None
        if "spawn-child" in arguments[1:]:
            child_bytecode_disabled = bool(int(subprocess.check_output(
                [sys.executable, "-c", (
                    "import sys; import orionis_cli_child; "
                    "print(int(sys.dont_write_bytecode))"
                )],
                text=True,
                timeout=5,
            )))
        payload = json.dumps({
            "argv": arguments,
            "bytecode_disabled": _BYTECODE_DISABLED,
            "bytecode_environment": os.environ.get("PYTHONDONTWRITEBYTECODE"),
            "child_bytecode_disabled": child_bytecode_disabled,
            "cwd": str(Path.cwd()),
            "executable": sys.executable,
            "marker": "project bootstrap",
            "stdin": sys.stdin.read(),
            "pid": os.getpid(),
            "entry_point_pid": int(os.environ["ORIONIS_CLI_TEST_PID"]),
        })
        stream = protocol_stdout()
        if stream is None:
            print(payload)
        else:
            stream.write((payload + "\\n").encode("utf-8"))
            stream.flush()
        return 23 if "fail" in arguments[1:] else 0

app = Application()
"""

class TestCliEntryPoint(TestCase):

    def setUp(self) -> None:
        """Create an isolated project with a bootstrap but no Reactor script.

        Returns
        -------
        None
            The temporary project is registered for automatic cleanup.
        """
        self._temporary = tempfile.TemporaryDirectory(prefix="orionis cli ")
        self.addCleanup(self._temporary.cleanup)
        self._root = Path(self._temporary.name).resolve()
        bootstrap = self._root / "bootstrap"
        bootstrap.mkdir()
        (bootstrap / "app.py").write_text(_BOOTSTRAP_SOURCE, encoding="utf-8")

    def _run(
        self, *arguments: str, startup_environment: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Invoke the entry point from the temporary project's root.

        Parameters
        ----------
        *arguments : str
            Command tokens forwarded to the local application's console handler.
        startup_environment : bool, optional
            Protect interpreter startup through the environment instead of -B.

        Returns
        -------
        subprocess.CompletedProcess[str]
            Captured streams and exit status of the CLI process.
        """
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(_PROJECT_ROOT)
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        environment.pop("PYTHONPYCACHEPREFIX", None)
        command = [sys.executable]
        if startup_environment:
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["PYTHONPYCACHEPREFIX"] = str(self._root / "bytecode")
        else:
            command.append("-B")
        command.extend(["-c", _ENTRY_POINT, *arguments])
        return subprocess.run(  # noqa: S603
            command,
            cwd=self._root,
            env=environment,
            input="protocol input\n",
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )

    def testForwardsArgumentsWithoutShellParsing(self) -> None:
        """Forward commands, options, and quoted values as separate tokens.

        Returns
        -------
        None
            Assertions verify that spaces and shell characters remain literal.
        """
        arguments = (
            "serve", "--port=9000", "value with spaces", 'quoted"value',
            "literal;value", "",
        )
        result = self._run(*arguments)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(payload["argv"], ["reactor", *arguments])

    def testUsesCurrentInterpreterAndDisablesBytecode(self) -> None:
        """Use the active interpreter and disable bytecode before bootstrap.

        Returns
        -------
        None
            Assertions verify interpreter identity and the absence of pyc files.
        """
        result = self._run("serve")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(Path(payload["executable"]).samefile(sys.executable))
        self.assertTrue(payload["bytecode_disabled"])
        self.assertEqual(list(self._root.rglob("__pycache__")), [])

    def testDisablesBytecodeInChildInterpreters(self) -> None:
        """Disable bytecode in child interpreters launched without Python flags.

        Returns
        -------
        None
            Assertions verify inherited protection and the absence of pyc files.
        """
        (self._root / "orionis_cli_child.py").write_text(
            "VALUE = 1\n", encoding="utf-8",
        )

        result = self._run("spawn-child")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(payload["child_bytecode_disabled"])
        self.assertEqual(payload["bytecode_environment"], "1")
        self.assertEqual(list(self._root.rglob("__pycache__")), [])
        self.assertEqual(list(self._root.rglob("*.pyc")), [])

    def testStartupEnvironmentPreventsAllBytecodeFiles(self) -> None:
        """Protect console-script imports and children without passing -B.

        Returns
        -------
        None
            Assertions verify that no startup or application cache is written.
        """
        (self._root / "orionis_cli_child.py").write_text(
            "VALUE = 1\n", encoding="utf-8",
        )

        result = self._run("spawn-child", startup_environment=True)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(payload["bytecode_disabled"])
        self.assertTrue(payload["child_bytecode_disabled"])
        self.assertEqual(list(self._root.rglob("*.pyc")), [])
        self.assertEqual(list(self._root.rglob("__pycache__")), [])
        self.assertFalse((self._root / "bytecode").exists())

    def testUsesBootstrapFromWorkingDirectoryWithoutReactor(self) -> None:
        """Import the local bootstrap without relying on a Reactor script.

        Returns
        -------
        None
            Assertions verify the project root and local bootstrap marker.
        """
        result = self._run("serve")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(Path(payload["cwd"]), self._root)
        self.assertEqual(payload["marker"], "project bootstrap")
        self.assertFalse((self._root / "reactor").exists())

    def testRunsCommandsInEntryPointProcess(self) -> None:
        """Run the console handler in the process that invoked the entry point.

        Returns
        -------
        None
            Assertions verify that command execution does not create a child.
        """
        result = self._run("serve")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(payload["pid"], payload["entry_point_pid"])

    def testPropagatesExitCode(self) -> None:
        """Return a nonzero exit code from the console handler unchanged.

        Returns
        -------
        None
            Assertions verify that failed commands remain failures.
        """
        result = self._run("fail")

        self.assertEqual(result.returncode, 23)

    def testAllowsNoCommandArguments(self) -> None:
        """Leave the no-command behavior to the application's console handler.

        Returns
        -------
        None
            Assertions verify that no extra command is inserted by the launcher.
        """
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(payload["argv"], ["reactor"])

    def testPreservesStandardStreams(self) -> None:
        """Preserve ordinary command input and keep stdout and stderr separate.

        Returns
        -------
        None
            Assertions verify that stream routing is unchanged.
        """
        result = self._run("serve")

        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[:2], ["bootstrap diagnostic", "command diagnostic"])
        self.assertEqual(json.loads(lines[-1])["stdin"], "protocol input\n")
        self.assertEqual(result.stderr, "application stderr\n")

    def testRedirectsMcpBootstrapAndCommandDiagnostics(self) -> None:
        """Keep MCP protocol stdout free of bootstrap and command diagnostics.

        Returns
        -------
        None
            Assertions verify diagnostic redirection before importing bootstrap.
        """
        result = self._run("mcp:start", "status")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["stdin"], "protocol input\n")
        self.assertEqual(
            result.stderr,
            "bootstrap diagnostic\ncommand diagnostic\napplication stderr\n",
        )

    def testIgnoresExistingReactorScript(self) -> None:
        """Ignore the root Reactor script even when executing it would fail.

        Returns
        -------
        None
            Assertions verify that only the local bootstrap is executed.
        """
        (self._root / "reactor").write_text(
            "raise RuntimeError('the Reactor script must not execute')\n",
            encoding="utf-8",
        )

        result = self._run("serve")

        self.assertEqual(result.returncode, 0, result.stderr)

    def testMissingBootstrapReportsImportError(self) -> None:
        """Report a missing local bootstrap instead of launching another app.

        Returns
        -------
        None
            Assertions verify that bootstrap import failures remain visible.
        """
        (self._root / "bootstrap" / "__init__.py").write_text(
            "", encoding="utf-8",
        )
        (self._root / "bootstrap" / "app.py").unlink()

        result = self._run("serve")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ModuleNotFoundError", result.stderr)
        self.assertIn("bootstrap.app", result.stderr)
        self.assertEqual(result.stdout, "")

    def testProjectRegistersEntryPoint(self) -> None:
        """Register the installable command against the package's launcher.

        Returns
        -------
        None
            Assertions verify the console-script metadata in the manifest.
        """
        manifest = tomllib.loads(
            (_PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"),
        )

        self.assertEqual(
            manifest["project"]["scripts"]["orionis"], "orionis.console.cli:main",
        )
