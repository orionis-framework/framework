from __future__ import annotations
import inspect
from contextlib import redirect_stderr, redirect_stdout
from html import escape
from io import StringIO
from unittest.mock import MagicMock, patch
from orionis.console.output.contracts.var_dumper import IVarDumper
from orionis.console.output.var_dumper import VarDumper
from orionis.test import TestCase

class TestVarDumper(TestCase):

    # ------------------------------------------------------------------ #
    #  Helpers                                                           #
    # ------------------------------------------------------------------ #

    def _make(self) -> VarDumper:
        """
        Create a dumper backed by a mocked Rich console.

        Returns
        -------
        VarDumper
            Dumper with a mock console configured for 120-column output.
        """
        mock_console = self.enterContext(
            patch("orionis.console.output.var_dumper.Console"),
        )
        mock_con = MagicMock()
        mock_con.size.width = 120
        mock_console.return_value = mock_con
        return VarDumper()

    # ------------------------------------------------------------------ #
    #  Instantiation & interface                                         #
    # ------------------------------------------------------------------ #

    def testInstantiation(self) -> None:
        """
        Verify that the dumper can be instantiated.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        self.assertIsInstance(dumper, VarDumper)

    def testIsSubclassOfIVarDumper(self) -> None:
        """
        Verify that ``VarDumper`` is a subclass of ``IVarDumper``.

        Returns
        -------
        None
            This test does not return a value.
        """
        self.assertTrue(issubclass(VarDumper, IVarDumper))

    def testInstanceIsIVarDumper(self) -> None:
        """
        Verify that a dumper instance satisfies ``IVarDumper``.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        self.assertIsInstance(dumper, IVarDumper)

    # ------------------------------------------------------------------ #
    #  showTypes                                                         #
    # ------------------------------------------------------------------ #

    def testShowTypesReturnsSelf(self) -> None:
        """
        Verify that ``showTypes`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.showTypes()
        self.assertIs(result, dumper)

    def testShowTypesDefaultTrue(self) -> None:
        """
        Verify that ``showTypes`` enables type labels by default.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.showTypes()
        self.assertTrue(dumper._VarDumper__show_types)

    def testShowTypesFalse(self) -> None:
        """
        Verify that ``showTypes`` stores an explicitly disabled flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.showTypes(show=False)
        self.assertFalse(dumper._VarDumper__show_types)

    def testShowTypesRaisesTypeError(self) -> None:
        """
        Verify that ``showTypes`` rejects a non-boolean flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.showTypes(show="yes")  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  showIndex                                                         #
    # ------------------------------------------------------------------ #

    def testShowIndexReturnsSelf(self) -> None:
        """
        Verify that ``showIndex`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.showIndex()
        self.assertIs(result, dumper)

    def testShowIndexDefaultTrue(self) -> None:
        """
        Verify that ``showIndex`` enables index labels by default.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.showIndex()
        self.assertTrue(dumper._VarDumper__show_index)

    def testShowIndexFalse(self) -> None:
        """
        Verify that ``showIndex`` stores an explicitly disabled flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.showIndex(show=False)
        self.assertFalse(dumper._VarDumper__show_index)

    def testShowIndexRaisesTypeError(self) -> None:
        """
        Verify that ``showIndex`` rejects a non-boolean flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.showIndex(show=1)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  expandAll                                                         #
    # ------------------------------------------------------------------ #

    def testExpandAllReturnsSelf(self) -> None:
        """
        Verify that ``expandAll`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.expandAll()
        self.assertIs(result, dumper)

    def testExpandAllDefaultTrue(self) -> None:
        """
        Verify that ``expandAll`` enables expansion by default.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.expandAll()
        self.assertTrue(dumper._VarDumper__expand_all)

    def testExpandAllFalse(self) -> None:
        """
        Verify that ``expandAll`` stores an explicitly disabled flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.expandAll(expand=False)
        self.assertFalse(dumper._VarDumper__expand_all)

    def testExpandAllRaisesTypeError(self) -> None:
        """
        Verify that ``expandAll`` rejects a non-boolean flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.expandAll(expand=0)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  maxDepth                                                          #
    # ------------------------------------------------------------------ #

    def testMaxDepthReturnsSelf(self) -> None:
        """
        Verify that ``maxDepth`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.maxDepth(5)
        self.assertIs(result, dumper)

    def testMaxDepthNone(self) -> None:
        """
        Verify that ``maxDepth`` accepts ``None`` for unlimited depth.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.maxDepth(None)
        self.assertIsNone(dumper._VarDumper__max_depth)

    def testMaxDepthPositiveInt(self) -> None:
        """
        Verify that ``maxDepth`` stores a positive integer limit.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.maxDepth(3)
        self.assertEqual(dumper._VarDumper__max_depth, 3)

    def testMaxDepthZero(self) -> None:
        """
        Verify that ``maxDepth`` accepts and stores a zero limit.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.maxDepth(0)
        self.assertEqual(dumper._VarDumper__max_depth, 0)

    def testMaxDepthRaisesTypeError(self) -> None:
        """
        Verify that ``maxDepth`` rejects a string depth limit.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.maxDepth("deep")  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  modulePath                                                        #
    # ------------------------------------------------------------------ #

    def testModulePathReturnsSelf(self) -> None:
        """
        Verify that ``modulePath`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.modulePath("some.module")
        self.assertIs(result, dumper)

    def testModulePathNone(self) -> None:
        """
        Verify that ``modulePath`` accepts and stores ``None``.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.modulePath(None)
        self.assertIsNone(dumper._VarDumper__module_path)

    def testModulePathString(self) -> None:
        """
        Verify that ``modulePath`` preserves the supplied string.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.modulePath("orionis.app.module")
        self.assertEqual(dumper._VarDumper__module_path, "orionis.app.module")

    def testModulePathRaisesTypeError(self) -> None:
        """
        Verify that ``modulePath`` rejects an integer argument.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.modulePath(123)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  lineNumber                                                        #
    # ------------------------------------------------------------------ #

    def testLineNumberReturnsSelf(self) -> None:
        """
        Verify that ``lineNumber`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.lineNumber(42)
        self.assertIs(result, dumper)

    def testLineNumberNone(self) -> None:
        """
        Verify that ``lineNumber`` accepts and stores ``None``.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.lineNumber(None)
        self.assertIsNone(dumper._VarDumper__line_number)

    def testLineNumberPositiveInt(self) -> None:
        """
        Verify that ``lineNumber`` preserves the supplied integer.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.lineNumber(99)
        self.assertEqual(dumper._VarDumper__line_number, 99)

    def testLineNumberRaisesTypeError(self) -> None:
        """
        Verify that ``lineNumber`` rejects a string argument.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.lineNumber("42")  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  forceExit                                                         #
    # ------------------------------------------------------------------ #

    def testForceExitReturnsSelf(self) -> None:
        """
        Verify that ``forceExit`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.forceExit()
        self.assertIs(result, dumper)

    def testForceExitDefaultTrue(self) -> None:
        """
        Verify that ``forceExit`` enables termination by default.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.forceExit()
        self.assertTrue(dumper._VarDumper__force_exit)

    def testForceExitFalse(self) -> None:
        """
        Verify that ``forceExit`` stores an explicitly disabled flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.forceExit(force=False)
        self.assertFalse(dumper._VarDumper__force_exit)

    def testForceExitRaisesTypeError(self) -> None:
        """
        Verify that ``forceExit`` rejects a non-boolean flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.forceExit(force=1)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  redirectOutput                                                    #
    # ------------------------------------------------------------------ #

    def testRedirectOutputReturnsSelf(self) -> None:
        """
        Verify that ``redirectOutput`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.redirectOutput()
        self.assertIs(result, dumper)

    def testRedirectOutputDefaultTrue(self) -> None:
        """
        Verify that ``redirectOutput`` enables redirection by default.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.redirectOutput()
        self.assertTrue(dumper._VarDumper__redirect_output)

    def testRedirectOutputFalse(self) -> None:
        """
        Verify that ``redirectOutput`` stores an explicitly disabled flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.redirectOutput(redirect=False)
        self.assertFalse(dumper._VarDumper__redirect_output)

    def testRedirectOutputRaisesTypeError(self) -> None:
        """
        Verify that ``redirectOutput`` rejects a non-boolean flag.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.redirectOutput(redirect="yes")  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  value                                                             #
    # ------------------------------------------------------------------ #

    def testValueReturnsSelf(self) -> None:
        """
        Verify that ``value`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.value("hello")
        self.assertIs(result, dumper)

    def testValueStoresSingleValue(self) -> None:
        """
        Verify that ``value`` adds exactly one stored entry.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        self.assertEqual(len(dumper._VarDumper__args), 0)
        dumper.value("hello")
        self.assertEqual(len(dumper._VarDumper__args), 1)

    def testValueStoresTypeInfo(self) -> None:
        """
        Verify that ``value`` records the stored argument's type name.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.value(42)
        entry = dumper._VarDumper__args[0]
        self.assertIn("type", entry)
        self.assertEqual(entry["type"], "int")

    def testValueDeepCopies(self) -> None:
        """
        Verify that later mutations leave a stored value unchanged.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        original = [1, 2, 3]
        dumper.value(original)
        original.append(4)
        stored = dumper._VarDumper__args[0]["value"]
        self.assertNotIn(4, stored)

    def testValueAcceptsDiverseTypes(self) -> None:
        """
        Verify that ``value`` accepts common built-in Python types.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        for v in (None, True, 3.14, {"key": "val"}, (1, 2), [1, 2]):
            dumper.value(v)
        self.assertEqual(len(dumper._VarDumper__args), 6)

    # ------------------------------------------------------------------ #
    #  values                                                            #
    # ------------------------------------------------------------------ #

    def testValuesReturnsSelf(self) -> None:
        """
        Verify that ``values`` returns the dumper for chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.values(1, 2, 3)
        self.assertIs(result, dumper)

    def testValuesStoresAllArguments(self) -> None:
        """
        Verify that ``values`` stores one entry per positional argument.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.values("a", "b", "c")
        self.assertEqual(len(dumper._VarDumper__args), 3)

    def testValuesWithNoArguments(self) -> None:
        """
        Verify that an empty ``values`` call returns the unchanged dumper.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.values()
        self.assertIs(result, dumper)
        self.assertEqual(len(dumper._VarDumper__args), 0)

    def testValuesCumulatesWithValue(self) -> None:
        """
        Verify that ``value`` and ``values`` accumulate entries together.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.value("first")
        dumper.values("second", "third")
        self.assertEqual(len(dumper._VarDumper__args), 3)

    # ------------------------------------------------------------------ #
    #  print                                                             #
    # ------------------------------------------------------------------ #

    def testPrintReturnsNone(self) -> None:
        """
        Verify that ``print`` returns ``None`` after rendering a value.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.value("test")
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintCallsConsole(self) -> None:
        """
        Verify that ``print`` delegates output to the Rich console.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        dumper.value("test")
        dumper.print()
        self.assertTrue(mock_con.print.called)

    def testPrintCallsConsoleMultipleTimesWithValue(self) -> None:
        """
        Verify that printing one value makes at least two console calls.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        dumper.value("test")
        dumper.print()
        self.assertGreaterEqual(mock_con.print.call_count, 2)

    def testPrintWithInsertLine(self) -> None:
        """
        Verify that ``print`` accepts blank-line padding.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.value("test")
        with patch("builtins.print"):
            result = dumper.print(insert_line=True)
        self.assertIsNone(result)

    def testPrintWithPresetModuleAndLine(self) -> None:
        """
        Verify that ``print`` accepts a preset module path and line number.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.modulePath("custom.module")
        dumper.lineNumber(10)
        dumper.value("x")
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithNoStoredValues(self) -> None:
        """
        Verify that ``print`` returns ``None`` when no values are stored.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithShowTypesDisabled(self) -> None:
        """
        Verify that ``print`` succeeds with type labels disabled.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.showTypes(show=False)
        dumper.value({"a": 1})
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithShowIndexDisabled(self) -> None:
        """
        Verify that ``print`` succeeds with index labels disabled.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.showIndex(show=False)
        dumper.value([1, 2, 3])
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithBothFlagsDisabled(self) -> None:
        """
        Verify that ``print`` succeeds with both display labels disabled.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.showTypes(show=False)
        dumper.showIndex(show=False)
        dumper.value("no title panel")
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithMaxDepthSet(self) -> None:
        """
        Verify that ``print`` accepts a configured depth limit.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.maxDepth(2)
        dumper.value({"nested": {"deep": "value"}})
        result = dumper.print()
        self.assertIsNone(result)

    # ------------------------------------------------------------------ #
    #  toHtml                                                            #
    # ------------------------------------------------------------------ #

    def testToHtmlReturnsString(self) -> None:
        """
        Verify that ``toHtml`` returns a string for stored values.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        mock_con.export_html.return_value = "<html><body>output</body></html>"
        dumper.value("test")
        result = dumper.toHtml()
        self.assertIsInstance(result, str)

    def testToHtmlCallsExportHtml(self) -> None:
        """
        Verify that ``toHtml`` delegates to the console's HTML exporter.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        mock_con.export_html.return_value = "<html></html>"
        dumper.value("content")
        dumper.toHtml()
        mock_con.export_html.assert_called_once()

    def testToHtmlWithInsertLine(self) -> None:
        """
        Verify that ``toHtml`` accepts the blank-line padding option.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        mock_con.export_html.return_value = "<html></html>"
        dumper.value("test")
        with patch("builtins.print"):
            result = dumper.toHtml(insert_line=True)
        self.assertIsInstance(result, str)

    def testToHtmlWithNoValues(self) -> None:
        """
        Verify that ``toHtml`` returns a string without stored values.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        mock_con.export_html.return_value = "<html></html>"
        result = dumper.toHtml()
        self.assertIsInstance(result, str)

    def testToHtmlDoesNotPrintRedirectOrExit(self) -> None:
        """
        Verify that HTML export neither writes to streams nor exits.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = (
            VarDumper()
            .values({"marker": "html-only-marker"})
            .forceExit(force=True)
            .redirectOutput(redirect=True)
        )
        stdout, stderr = StringIO(), StringIO()
        with (
            patch("sys.exit") as sys_exit,
            patch("os._exit") as os_exit,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            html = dumper.toHtml(insert_line=True)

        self.assertIn("html-only-marker", html)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        sys_exit.assert_not_called()
        os_exit.assert_not_called()

    def testToHtmlEscapesValuesAndOmitsTheConsoleHeader(self) -> None:
        """
        Verify that HTML export escapes values and omits the console header.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = VarDumper().values("<script>alert('dump')</script>")
        stdout = StringIO()
        with redirect_stdout(stdout):
            dumper.print()
            html = dumper.toHtml()

        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("Module(", html)
        self.assertEqual(html.count("&lt;script&gt;"), 1)

    def testToHtmlDoesNotAccumulatePreviousExports(self) -> None:
        """
        Verify that repeated HTML exports do not accumulate prior output.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = (
            VarDumper()
            .showIndex(show=False)
            .showTypes(show=False)
            .values("repeat-html-marker")
        )
        with redirect_stdout(StringIO()):
            first = dumper.toHtml()
            second = dumper.toHtml()

        self.assertEqual(first, second)
        self.assertEqual(second.count("repeat-html-marker"), 1)

    def testToHtmlUsesNativeDiagnosticPanels(self) -> None:
        """
        Verify that HTML uses themed value panels without terminal borders.

        Returns
        -------
        None
            This test does not return a value.
        """
        html = VarDumper().values({"message": "Hola"}, [1, 2]).toHtml()

        self.assertEqual(html.count('class="code-container dump-panel"'), 2)
        self.assertEqual(html.count('class="dump-output"'), 2)
        self.assertIn("var(--orionis-border,#dce1e7)", html)
        self.assertIn("var(--orionis-mono,", html)
        self.assertIn("min-width:min-content", html)
        self.assertIn("#1", html)
        self.assertIn("#2", html)
        self.assertIn("dict", html)
        self.assertIn("list", html)
        self.assertNotIn("\u256d", html)
        self.assertNotIn("\u256e", html)

    def testToHtmlShowsConfiguredLocation(self) -> None:
        """
        Verify that HTML panel headers show the configured file and line.

        Returns
        -------
        None
            This test does not return a value.
        """
        filename = r"app\http\controllers\auth\login_controller.py"
        html = (
            VarDumper()
            .modulePath(filename)
            .lineNumber(23)
            .values("first", "second")
            .toHtml()
        )

        self.assertEqual(html.count(f">{filename}:23</span>"), 2)
        self.assertNotIn(">Python</span>", html)

    def testToHtmlCapturesCallerLocation(self) -> None:
        """
        Verify that HTML captures caller location without changing metadata.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = VarDumper().values("caller-location")
        frame = inspect.currentframe()
        if frame is None:
            self.fail("The test requires Python frame support.")
        filename = frame.f_code.co_filename
        line_number = frame.f_lineno + 1
        html = dumper.toHtml()
        del frame

        self.assertIn(f">{escape(filename)}:{line_number}</span>", html)
        self.assertIsNone(dumper._VarDumper__module_path)
        self.assertIsNone(dumper._VarDumper__line_number)
        self.assertEqual(html, dumper.toHtml())
        with redirect_stdout(StringIO()) as stdout:
            dumper.print()
        self.assertIn(__name__, stdout.getvalue())

    def testToHtmlEscapesSourceLocation(self) -> None:
        """
        Verify that HTML escapes source filenames in panel headers.

        Returns
        -------
        None
            This test does not return a value.
        """
        filename = '<img src=x onerror="alert(1)">.py'
        html = VarDumper().modulePath(filename).lineNumber(42).values("x").toHtml()

        self.assertIn(f">{escape(filename)}:42</span>", html)
        self.assertNotIn("<img", html)

    def testToHtmlShowsUnknownLocationWithoutAFrame(self) -> None:
        """
        Verify that HTML marks the source unknown when no frame is available.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = VarDumper().values("no-frame")
        with patch(
            "orionis.console.output.var_dumper.inspect.currentframe",
            return_value=None,
        ):
            html = dumper.toHtml()

        self.assertIn(">unknown:?</span>", html)

    def testToHtmlLeavesConsoleIndicesUnchanged(self) -> None:
        """
        Verify that HTML exports leave terminal indices unchanged.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = VarDumper().values("repeat-native-panel")
        first = dumper.toHtml()
        second = dumper.toHtml()

        self.assertEqual(first, second)
        self.assertEqual(dumper._VarDumper__last_index, 0)
        with redirect_stdout(StringIO()):
            dumper.print()
        self.assertEqual(dumper._VarDumper__last_index, 1)

    def testToHtmlEscapesTypeLabels(self) -> None:
        """
        Verify that HTML escapes custom type names in panel labels.

        Returns
        -------
        None
            This test does not return a value.
        """
        value = type("</span><img src=x onerror=alert(1)>", (), {})()
        html = VarDumper().values(value).toHtml()

        self.assertIn("&lt;/span&gt;&lt;img src=x onerror=alert(1)&gt;", html)
        self.assertNotIn("<img", html)

    def testToHtmlRespectsHiddenLabelsAndDepth(self) -> None:
        """
        Verify that HTML honors hidden labels and the configured depth limit.

        Returns
        -------
        None
            This test does not return a value.
        """
        html = (
            VarDumper()
            .showIndex(show=False)
            .showTypes(show=False)
            .expandAll(expand=True)
            .maxDepth(1)
            .values({"nested": {"marker": "hidden-depth-marker"}})
            .toHtml()
        )

        self.assertNotIn(">#1", html)
        self.assertNotIn(">dict<", html)
        self.assertNotIn("hidden-depth-marker", html)
        self.assertIn("...", html)

    def testToHtmlPreservesConsoleExitConfiguration(self) -> None:
        """
        Verify that HTML export preserves the console's termination setting.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = VarDumper().values("preserved-exit").forceExit(force=True)
        with (
            redirect_stdout(StringIO()),
            patch("sys.exit") as sys_exit,
        ):
            dumper.toHtml()
            sys_exit.assert_not_called()
            dumper.print()

        sys_exit.assert_called_once_with(1)

    def testPrintPreservesTheCallingModuleHeader(self) -> None:
        """
        Verify that the console header identifies the calling module.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = VarDumper().values("caller-header")
        stdout = StringIO()
        with redirect_stdout(stdout):
            dumper.print()

        self.assertIn(__name__, stdout.getvalue())

    # ------------------------------------------------------------------ #
    #  forceExit behaviour                                               #
    # ------------------------------------------------------------------ #

    def testForceExitTriggersSysExit(self) -> None:
        """
        Verify that ``print`` calls ``sys.exit(1)`` when forced to exit.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        dumper.forceExit()
        dumper.value("trigger")
        with patch("sys.exit") as mock_exit:
            dumper.print()
        mock_exit.assert_called_once_with(1)

    # ------------------------------------------------------------------ #
    #  Method chaining                                                   #
    # ------------------------------------------------------------------ #

    def testMethodChainingCompletes(self) -> None:
        """
        Verify that configuration methods and ``value`` support chaining.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = (
            dumper
            .showTypes(show=True)
            .showIndex(show=True)
            .expandAll(expand=True)
            .maxDepth(5)
            .modulePath("app.main")
            .lineNumber(1)
            .forceExit(force=False)
            .redirectOutput(redirect=False)
            .value("chained")
        )
        self.assertIs(result, dumper)

    def testMethodChainingWithValues(self) -> None:
        """
        Verify that chained ``value`` and ``values`` calls retain all entries.

        Returns
        -------
        None
            This test does not return a value.
        """
        dumper = self._make()
        result = dumper.value("a").value("b").values("c", "d")
        self.assertIs(result, dumper)
        self.assertEqual(len(dumper._VarDumper__args), 4)
