import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_FRAME = "⠋ Inicializando Orionis...".encode()
_CLEAR = ("\r" + " " * len(_FRAME.decode()) + "\r").encode()
_NEWLINE = os.linesep.encode()
_STATE_MARKER = b"\n__ORIONIS_CLI_STATE__"
_DRIVER = r'''
import builtins
import json
import runpy
import sys

entry, scenario, reactor_path, *arguments = sys.argv[1:]
state = {"scenario": scenario, "events": []}
builtins._orionis_startup_test = state

class Terminal:
    def __init__(self, stream, name):
        """
        Initialize a terminal wrapper with shared output recording.

        Parameters
        ----------
        stream : TextIO
            Original standard stream to wrap.
        name : str
            Stream label to record alongside each write.

        Returns
        -------
        None
            Retain the wrapped stream and its event label.
        """
        self.stream = stream
        self.name = name

    def __getattr__(self, name):
        """
        Delegate an unresolved attribute to the wrapped stream.

        Parameters
        ----------
        name : str
            Attribute name to retrieve from the original stream.

        Returns
        -------
        object
            Attribute value exposed by the wrapped stream.
        """
        return getattr(self.stream, name)

    def isatty(self):
        """
        Report the wrapped pipe as an interactive terminal.

        Returns
        -------
        bool
            Always ``True`` to enable launcher feedback during the test.
        """
        return True

    def write(self, value):
        """
        Record output and forward it to the original stream.

        Parameters
        ----------
        value : str
            Text to record and write unchanged.

        Returns
        -------
        int
            Number of characters written by the original stream.
        """
        state["events"].append([self.name, value])
        return self.stream.write(value)

stdout, stderr = Terminal(sys.stdout, "stdout"), Terminal(sys.stderr, "stderr")
sys.stdout, sys.stderr = stdout, stderr
builtins._orionis_startup_streams = (stdout, stderr)
original_import = builtins.__import__

def observe_import(name, *arguments, **keywords):
    """
    Record feedback timing before delegating to Python's import hook.

    Parameters
    ----------
    name : str
        Module name passed to the import hook.
    *arguments : object
        Positional import arguments to forward unchanged.
    **keywords : object
        Keyword import arguments to forward unchanged.

    Returns
    -------
    ModuleType
        Module returned by the original import hook.
    """
    if name == "orionis.aio" and "indicator_before_loop" not in state:
        state["indicator_before_loop"] = (
            state["events"] == [["stderr", "⠋ Inicializando Orionis..."]]
        )
    return original_import(name, *arguments, **keywords)

builtins.__import__ = observe_import
try:
    if entry == "console":
        sys.argv = ["orionis", *arguments]
        from orionis.console.cli import main
        raise SystemExit(main())
    sys.argv = [reactor_path, *arguments]
    runpy.run_path(reactor_path, run_name="__main__")
except BaseException as error:
    state["exception"] = type(error).__name__
    if isinstance(error, SystemExit):
        state["exit_code"] = error.code
    raise
finally:
    state["stdout_restored"] = sys.stdout is stdout
    state["stderr_restored"] = sys.stderr is stderr
    payload = "\n__ORIONIS_CLI_STATE__" + json.dumps(state) + "\n"
    sys.__stdout__.flush()
    sys.__stdout__.buffer.write(payload.encode("utf-8"))
    sys.__stdout__.buffer.flush()
'''
_BOOTSTRAP = r'''
import asyncio
import builtins
import sys

state = builtins._orionis_startup_test
state["indicator_before_bootstrap"] = (
    state["events"] == [["stderr", "⠋ Inicializando Orionis..."]]
)
assert state["indicator_before_bootstrap"], "feedback did not precede bootstrap"
scenario = state["scenario"]
if scenario == "bootstrap_stdout":
    sys.stdout.write("bootstrap\n")
elif scenario == "bootstrap_stderr":
    sys.stderr.write("bootstrap\n")
elif scenario == "bootstrap_exit":
    raise SystemExit(23)
elif scenario == "bootstrap_interrupt":
    raise KeyboardInterrupt
elif scenario == "bootstrap_error":
    raise RuntimeError("bootstrap failed")

async def native_command():
    """
    Dispatch native output through the real reactor with isolated doubles.

    Returns
    -------
    int
        Command exit code returned by the reactor for the selected scenario.
    """
    import os
    import subprocess
    from contextlib import asynccontextmanager
    from orionis.console.core.reactor import Reactor
    from orionis.console.entities.command import Command

    class Native:
        async def handle(self):
            """
            Write native and child-process output, then return an exit code.

            Returns
            -------
            int
                Exit code ``23`` after both output operations complete.
            """
            os.write(sys.stdout.fileno(), b"\x1b[32mnative\rready\x1b[0m\n")
            subprocess.run(
                [sys.executable, "-B", "-c", (
                    "import os; os.write(1, b'child\\n')"
                )], check=True,
            )
            return 23

    command = Command(
        obj=Native, signature="native", description="Native output test",
        timestamps=False,
    )

    class Scope:
        def set(self, *arguments):
            """
            Accept reactor scope values without storing them.

            Parameters
            ----------
            *arguments : object
                Scope values accepted to satisfy the reactor interface.

            Returns
            -------
            None
                Leave scope state unchanged.
            """
            pass

    class Container:
        @asynccontextmanager
        async def beginScope(self):
            """
            Yield a minimal scope for native command dispatch.

            Yields
            ------
            Scope
                Fresh no-op scope used by the reactor.
            """
            yield Scope()

        async def build(self, target):
            """
            Check stream restoration before constructing the command.

            Parameters
            ----------
            target : type
                Command class to instantiate after checking the streams.

            Returns
            -------
            object
                New instance of the supplied command class.
            """
            stdout, stderr = builtins._orionis_startup_streams
            state["restored_before_build"] = (
                sys.stdout is stdout and sys.stderr is stderr
            )
            assert state["restored_before_build"], "feedback survived dispatch"
            return target()

        async def call(self, instance, method, **arguments):
            """
            Invoke and await the selected command method.

            Parameters
            ----------
            instance : object
                Command instance that exposes the requested method.
            method : str
                Name of the asynchronous method to invoke.
            **arguments : object
                Keyword arguments to forward to the method.

            Returns
            -------
            object
                Result awaited from the selected method.
            """
            return await getattr(instance, method)(**arguments)

    class Loader:
        async def get(self, signature):
            """
            Resolve the command fixture or simulate a discovery failure.

            Parameters
            ----------
            signature : str
                Requested command signature, ignored by this scenario double.

            Returns
            -------
            Command | None
                Command fixture, or ``None`` for the missing-command scenario.

            Raises
            ------
            ImportError
                If the scenario requests a command discovery failure.
            """
            if scenario == "native_missing":
                return None
            if scenario == "native_discovery_error":
                raise ImportError("native command discovery failed")
            return command

    class Counter:
        async def astart(self):
            """
            Accept the reactor's counter-start call without side effects.

            Returns
            -------
            None
                Leave timing state unchanged.
            """
            pass

        async def astop(self):
            """
            Accept the reactor's counter-stop call without side effects.

            Returns
            -------
            None
                Leave timing state unchanged.
            """
            pass

        async def agetSeconds(self):
            """
            Return zero elapsed seconds for deterministic timing.

            Returns
            -------
            float
                Fixed elapsed time ``0.0``.
            """
            return 0.0

    class Output:
        def info(self, value):
            """
            Record the reactor's informational message.

            Parameters
            ----------
            value : object
                Log message to retain in the shared scenario state.

            Returns
            -------
            None
                Store the message without emitting output.
            """
            state["log"] = value

        def error(self, value):
            """
            Record an error and check restoration before native diagnostics.

            Parameters
            ----------
            value : object
                Error message to retain in the shared scenario state.

            Returns
            -------
            None
                Store the message and emit native output for lookup failures.
            """
            state["error_log"] = value
            if scenario in {"native_missing", "native_discovery_error"}:
                stdout, stderr = builtins._orionis_startup_streams
                state["restored_before_error_log"] = (
                    sys.stdout is stdout and sys.stderr is stderr
                )
                assert state["restored_before_error_log"], "feedback survived failure"
                os.write(sys.stderr.fileno(), b"native logger\n")

        async def exception(self, error):
            """
            Report expected lookup failures or propagate unexpected errors.

            Parameters
            ----------
            error : BaseException
                Exception supplied by the reactor's failure handler.

            Returns
            -------
            None
                Record expected failures and emit native diagnostic output.

            Raises
            ------
            BaseException
                If the scenario does not represent an expected lookup failure.
            """
            if scenario in {"native_missing", "native_discovery_error"}:
                stdout, stderr = builtins._orionis_startup_streams
                state["restored_before_catch"] = (
                    sys.stdout is stdout and sys.stderr is stderr
                )
                assert state["restored_before_catch"], "feedback survived catch"
                state["caught_error"] = type(error).__name__
                os.write(sys.stderr.fileno(), b"native failure\n")
                return
            raise error

    output = Output()
    reactor = Reactor(Container(), Loader(), output, output, output, Counter())
    return await reactor.call("native")

class Application:
    async def handleCommand(self, arguments):
        """
        Record launcher arguments and execute the selected startup scenario.

        Parameters
        ----------
        arguments : list[str]
            Literal reactor argument tokens supplied by the launcher.

        Returns
        -------
        int
            Scenario exit code, including native command dispatch results.

        Raises
        ------
        KeyboardInterrupt
            If the scenario requests interruption during command execution.
        """
        state["arguments"] = arguments
        if scenario in {"bootstrap_stdout", "bootstrap_stderr"}:
            sys.stdout.write("command\n")
        elif scenario == "slow":
            await asyncio.sleep(0.01)
            sys.stdout.write("\x1b[32mprogress 1\x1b[0m\r")
            await asyncio.sleep(0.01)
            sys.stderr.write("\rworking")
            sys.stdout.write("\x1b[32mDONE\x1b[0m\n")
        elif scenario == "command_interrupt":
            raise KeyboardInterrupt
        elif scenario in {"native", "native_missing", "native_discovery_error"}:
            return await native_command()
        return 23 if scenario == "returned_exit" else 0

app = Application()
    '''

class TestStartupEntryPoints(unittest.TestCase):

    def setUp(self) -> None:
        """
        Create an isolated bootstrap for both production CLI launchers.

        Returns
        -------
        None
            Create a temporary bootstrap module and register directory cleanup.
        """
        temporary = tempfile.TemporaryDirectory(prefix="orionis startup ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        bootstrap = self.root / "bootstrap"
        bootstrap.mkdir()
        (bootstrap / "__init__.py").write_text("", encoding="utf-8")
        self.bootstrap = bootstrap / "app.py"
        self.bootstrap.write_text(_BOOTSTRAP, encoding="utf-8")

    def _environment(self) -> dict[str, str]:
        """
        Build a UTF-8 environment that enables interactive feedback.

        Returns
        -------
        dict[str, str]
            Copied environment with terminal settings, project imports, and no CI.
        """
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(_PROJECT_ROOT)
        environment["PYTHONIOENCODING"] = "utf-8"
        environment["COLUMNS"] = "80"
        environment["TERM"] = "xterm"
        environment.pop("CI", None)
        return environment

    def _run(
        self, entry: str, scenario: str, *arguments: str,
    ) -> tuple[subprocess.CompletedProcess[bytes], bytes, dict[str, object]]:
        """
        Run a launcher and separate command stdout from test metadata.

        Parameters
        ----------
        entry : str
            Launcher selector: ``"console"`` or ``"reactor"``.
        scenario : str
            Fixture behavior to exercise in the isolated bootstrap.
        *arguments : str
            Literal command-line tokens forwarded without shell interpretation.

        Returns
        -------
        tuple[subprocess.CompletedProcess[bytes], bytes, dict[str, object]]
            Completed process, command stdout, and decoded launcher state.
        """
        result = subprocess.run(  # noqa: S603
            [
                sys.executable, "-B", "-c", _DRIVER, entry, scenario,
                str(_PROJECT_ROOT / "reactor"), *arguments,
            ],
            cwd=self.root,
            env=self._environment(),
            capture_output=True,
            check=False,
            timeout=20,
        )
        output, separator, metadata = result.stdout.partition(_STATE_MARKER)
        self.assertTrue(separator, result.stderr.decode(errors="replace"))
        return result, output, json.loads(metadata)

    def _assertRestored(self, metadata: dict[str, object]) -> None:
        """
        Assert restoration of both original standard streams.

        Parameters
        ----------
        metadata : dict[str, object]
            Launcher state containing stdout and stderr restoration flags.

        Returns
        -------
        None
            Require successful restoration of both streams.
        """
        self.assertTrue(metadata["stdout_restored"])
        self.assertTrue(metadata["stderr_restored"])

    def testFeedbackPrecedesLoopAndBootstrapImports(self) -> None:
        """
        Verify that startup feedback precedes loop and bootstrap imports.

        Returns
        -------
        None
            Assert early display, one cleanup, and restored streams per launcher.
        """
        for entry in ("console", "reactor"):
            with self.subTest(entry=entry):
                result, output, metadata = self._run(entry, "silent", "list")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, b"")
                self.assertEqual(result.stderr, _FRAME + _CLEAR)
                self.assertTrue(metadata["indicator_before_loop"])
                self.assertTrue(metadata["indicator_before_bootstrap"])
                self._assertRestored(metadata)

    def testFirstBootstrapWriteClearsBeforeStdoutOrStderr(self) -> None:
        """
        Verify cleanup before initial bootstrap stdout or stderr output.

        Returns
        -------
        None
            Assert unchanged bootstrap and command text and restored streams.
        """
        for entry in ("console", "reactor"):
            for scenario in ("bootstrap_stdout", "bootstrap_stderr"):
                with self.subTest(entry=entry, scenario=scenario):
                    result, output, metadata = self._run(entry, scenario, "list")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    stderr = _FRAME + _CLEAR
                    if scenario == "bootstrap_stdout":
                        self.assertEqual(
                            output, b"bootstrap" + _NEWLINE + b"command" + _NEWLINE,
                        )
                    else:
                        self.assertEqual(output, b"command" + _NEWLINE)
                        stderr += b"bootstrap" + _NEWLINE
                    self.assertEqual(result.stderr, stderr)
                    self.assertEqual(metadata["events"][1], ["stderr", _CLEAR.decode()])
                    self._assertRestored(metadata)

    def testArgumentsAndApplicationExitCodeArePreserved(self) -> None:
        """
        Verify that literal arguments and application exit codes remain unchanged.

        Returns
        -------
        None
            Assert literal tokens, the reactor executable name, and exit code 23.
        """
        arguments = ("custom:command", "value with spaces", "literal;value", "")
        for entry in ("console", "reactor"):
            with self.subTest(entry=entry):
                result, output, metadata = self._run(entry, "returned_exit", *arguments)
                self.assertEqual(result.returncode, 23)
                self.assertEqual(output, b"")
                self.assertEqual(metadata["arguments"][1:], list(arguments))
                self.assertEqual(Path(metadata["arguments"][0]).stem, "reactor")
                self.assertEqual(result.stderr, _FRAME + _CLEAR)
                self._assertRestored(metadata)

    def testBootstrapExceptionsAndInterruptsKeepExitCodesAndCleanUp(self) -> None:
        """
        Verify bootstrap error and interruption exit codes with cleanup.

        Returns
        -------
        None
            Assert matching exit codes, exception types, and restored streams.
        """
        interruption = subprocess.run(
            [sys.executable, "-B", "-c", "raise KeyboardInterrupt"],
            capture_output=True, check=False, timeout=10,
        ).returncode
        cases = (
            ("bootstrap_exit", 23, "SystemExit"),
            ("bootstrap_interrupt", interruption, "KeyboardInterrupt"),
            ("bootstrap_error", 1, "RuntimeError"),
        )
        for entry in ("console", "reactor"):
            for scenario, status, error in cases:
                with self.subTest(entry=entry, scenario=scenario):
                    result, output, metadata = self._run(entry, scenario, "list")
                    self.assertEqual(result.returncode, status, result.stderr)
                    self.assertEqual(output, b"")
                    self.assertTrue(result.stderr.startswith(_FRAME + _CLEAR))
                    self.assertEqual(metadata["exception"], error)
                    if error != "SystemExit":
                        self.assertIn(
                            error.encode(), result.stderr[len(_FRAME + _CLEAR):],
                        )
                    self._assertRestored(metadata)

    def testCommandInterruptPreservesExistingLoopExitPolicy(self) -> None:
        """
        Verify that command interruption follows the successful loop-exit policy.

        Returns
        -------
        None
            Assert exit code zero, cleared feedback, and restored streams.
        """
        for entry in ("console", "reactor"):
            with self.subTest(entry=entry):
                result, output, metadata = self._run(entry, "command_interrupt", "long")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, b"")
                self.assertEqual(result.stderr, _FRAME + _CLEAR)
                self._assertRestored(metadata)

    def testSlowDynamicCommandPreservesAnsiAndCarriageReturns(self) -> None:
        """
        Verify that asynchronous progress preserves ANSI and carriage-return bytes.

        Returns
        -------
        None
            Assert exact output on both streams and cleanup after the command.
        """
        for entry in ("console", "reactor"):
            with self.subTest(entry=entry):
                result, output, metadata = self._run(entry, "slow", "long")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    output,
                    b"\x1b[32mprogress 1\x1b[0m\r\x1b[32mDONE\x1b[0m" + _NEWLINE,
                )
                self.assertEqual(result.stderr, _FRAME + _CLEAR + b"\rworking")
                self._assertRestored(metadata)

    def testMissingBootstrapClearsBeforeTraceback(self) -> None:
        """
        Verify feedback cleanup before a missing-bootstrap traceback.

        Returns
        -------
        None
            Assert import failure, cleanup before diagnostics, and restored streams.
        """
        self.bootstrap.unlink()
        for entry in ("console", "reactor"):
            with self.subTest(entry=entry):
                result, output, metadata = self._run(entry, "silent", "list")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(output, b"")
                self.assertTrue(result.stderr.startswith(_FRAME + _CLEAR))
                self.assertIn(b"ModuleNotFoundError", result.stderr)
                self.assertEqual(metadata["exception"], "ModuleNotFoundError")
                self._assertRestored(metadata)

    def testRealReactorRetiresFeedbackBeforeNativeCommandBuildAndOutput(self) -> None:
        """
        Verify that the real reactor clears feedback before command construction.

        Returns
        -------
        None
            Assert restored streams before construction, native output, and code 23.
        """
        for entry in ("console", "reactor"):
            with self.subTest(entry=entry):
                result, output, metadata = self._run(entry, "native", "native")
                self.assertEqual(result.returncode, 23, result.stderr)
                self.assertTrue(metadata["restored_before_build"])
                self.assertEqual(output, b"\x1b[32mnative\rready\x1b[0m\nchild\n")
                self.assertEqual(result.stderr, _FRAME + _CLEAR)
                self._assertRestored(metadata)

    def testFailedResolutionRetiresFeedbackBeforeNativeLoggerAndCatch(self) -> None:
        """
        Verify cleanup before native diagnostics for command lookup failures.

        Returns
        -------
        None
            Assert restoration before logging and catching missing or failed lookup.
        """
        cases = (
            ("native_missing", "ValueError"),
            ("native_discovery_error", "ImportError"),
        )
        for entry in ("console", "reactor"):
            for scenario, error in cases:
                with self.subTest(entry=entry, scenario=scenario):
                    result, output, metadata = self._run(entry, scenario, "native")
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertEqual(output, b"")
                    self.assertTrue(metadata["restored_before_error_log"])
                    self.assertTrue(metadata["restored_before_catch"])
                    self.assertEqual(metadata["caught_error"], error)
                    self.assertEqual(
                        result.stderr,
                        _FRAME + _CLEAR + b"native logger\nnative failure\n",
                    )
                    self._assertRestored(metadata)
