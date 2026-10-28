import ast
import asyncio
import inspect
from contextlib import redirect_stdout
from html import escape
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from orionis.console import Dumper as ConsoleDumper
from orionis.console.debug.dumper import Dumper, HttpDump
from orionis.container.context.manager import ScopeManager
from orionis.container.facades.facade import Facade
from orionis.failure.enums.kernel_type import KernelContext
from orionis.support import facades
from orionis.support.facades import Debug as ExportedDebug
from orionis.support.facades.debug import Debug
from orionis.test import TestCase

class TestDebugFacade(TestCase):

    def setUp(self) -> None:
        """
        Pin an isolated dumper service for each test.

        Returns
        -------
        None
            Register cleanup to restore the previous pinned service.
        """
        self.enterContext(
            patch.object(Debug, "_pinned_instance", Dumper()),
        )

    def testExportsTheFacadeWithoutReplacingTheConsoleHelper(self) -> None:
        """
        Verify that the debug facade and console helper remain distinct.

        Returns
        -------
        None
            This test does not return a value.
        """
        self.assertTrue(issubclass(Debug, Facade))
        self.assertIs(ExportedDebug, Debug)
        self.assertEqual(Debug.__name__, "Debug")
        self.assertIn("Debug", facades.__all__)
        self.assertNotIn("Dumper", facades.__all__)
        self.assertIs(ConsoleDumper, Dumper)
        self.assertIsNot(ExportedDebug, ConsoleDumper)

    def testHasAMatchingFacadeStub(self) -> None:
        """
        Verify that the facade stub inherits the shared typing contracts.

        Returns
        -------
        None
            This test does not return a value.
        """
        stub_path = Path(inspect.getfile(Debug)).with_suffix(".pyi")
        stub = ast.parse(stub_path.read_text(encoding="utf-8"))
        definition = next(
            node for node in stub.body
            if isinstance(node, ast.ClassDef) and node.name == Debug.__name__
        )
        self.assertEqual(
            [ast.unparse(base) for base in definition.bases],
            ["IDumper", "IFacade"],
        )

    def testDumpPrintsSynchronouslyWithoutExiting(self) -> None:
        """
        Verify that facade dumping prints synchronously without exiting.

        Returns
        -------
        None
            This test does not return a value.
        """
        output = StringIO()
        with (
            redirect_stdout(output),
            patch("sys.exit") as sys_exit,
            patch("os._exit") as os_exit,
        ):
            result = Debug.dump({"facade-value": 7})

        self.assertIsNone(result)
        self.assertIn("facade-value", output.getvalue())
        sys_exit.assert_not_called()
        os_exit.assert_not_called()

    async def testHttpDdPreservesTheCallerLocationAndOptions(self) -> None:
        """
        Verify that HTTP facade dumps preserve caller location and options.

        Returns
        -------
        None
            This test does not return a value.
        """
        async with ScopeManager() as scope:
            scope["kernel"] = KernelContext.HTTP
            with self.assertRaises(HttpDump) as captured:
                Debug.dd(
                    {"facade-source": "<value>"},
                    show_types=True,
                    show_index=True,
                    redirect_output=True,
                    insert_line=True,
                )

        method = type(self).testHttpDdPreservesTheCallerLocationAndOptions
        source_lines, first_line = inspect.getsourcelines(method)
        call_line = first_line + next(
            index for index, line in enumerate(source_lines)
            if line.lstrip().startswith("Debug.dd(")
        )
        html = captured.exception.dumper.toHtml(
            insert_line=captured.exception.insert_line,
        )
        filename = escape(method.__code__.co_filename)
        self.assertIn(f">{filename}:{call_line}</span>", html)
        self.assertIn("facade-source", html)
        self.assertIn("&lt;value&gt;", html)
        self.assertIn("dict", html)
        self.assertIn("#1", html)
        self.assertTrue(captured.exception.insert_line)

    async def testConcurrentHttpDumpsKeepIndependentSnapshots(self) -> None:
        """
        Verify that concurrent facade dumps retain independent snapshots.

        Returns
        -------
        None
            This test does not return a value.
        """
        async def capture(value: str) -> HttpDump:
            """
            Capture an HTTP dump snapshot before mutating its input.

            Parameters
            ----------
            value : str
                Request-local marker to preserve in the snapshot.

            Returns
            -------
            HttpDump
                Captured interruption containing the original request marker.
            """
            data = {"value": value}
            async with ScopeManager() as scope:
                scope["kernel"] = KernelContext.HTTP
                await asyncio.sleep(0)
                with self.assertRaises(HttpDump) as captured:
                    Debug.dd(data)
                data["value"] = "changed-after-dump"
            return captured.exception

        first, second = await asyncio.gather(
            capture("first-facade-request"),
            capture("second-facade-request"),
        )

        self.assertIsNot(first.dumper, second.dumper)
        first_html, second_html = first.dumper.toHtml(), second.dumper.toHtml()
        self.assertIn("first-facade-request", first_html)
        self.assertNotIn("second-facade-request", first_html)
        self.assertIn("second-facade-request", second_html)
        self.assertNotIn("first-facade-request", second_html)
        self.assertNotIn("changed-after-dump", first_html)
        self.assertNotIn("changed-after-dump", second_html)
