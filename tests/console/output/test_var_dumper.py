from __future__ import annotations
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
        Create a VarDumper instance with a mocked Rich Console.

        Returns
        -------
        VarDumper
            A VarDumper instance whose internal Console is replaced by a
            MagicMock so no real terminal output is produced.
        """
        with patch("orionis.console.output.var_dumper.Console") as mock_console:
            mock_con = MagicMock()
            mock_con.size.width = 120
            mock_console.return_value = mock_con
            dumper = VarDumper()
        dumper._VarDumper__console = mock_con
        return dumper

    # ------------------------------------------------------------------ #
    #  Instantiation & interface                                         #
    # ------------------------------------------------------------------ #

    def testInstantiation(self) -> None:
        """Verify that VarDumper can be instantiated without errors.

        Ensures the constructor completes without raising any exception
        and returns a valid instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        self.assertIsInstance(dumper, VarDumper)

    def testIsSubclassOfIVarDumper(self) -> None:
        """Verify that VarDumper is a subclass of IVarDumper.

        Ensures the concrete implementation satisfies the abstract interface
        so it can be used polymorphically wherever IVarDumper is expected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(VarDumper, IVarDumper))

    def testInstanceIsIVarDumper(self) -> None:
        """Verify that a VarDumper instance satisfies isinstance(obj, IVarDumper).

        Ensures polymorphic usage is valid and the object passes type checks
        against the abstract interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        self.assertIsInstance(dumper, IVarDumper)

    # ------------------------------------------------------------------ #
    #  showTypes                                                         #
    # ------------------------------------------------------------------ #

    def testShowTypesReturnsSelf(self) -> None:
        """Verify that showTypes returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so callers can
        chain configuration calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.showTypes()
        self.assertIs(result, dumper)

    def testShowTypesDefaultTrue(self) -> None:
        """Verify that showTypes() called with its default argument stores True.

        Ensures that omitting the keyword argument uses the documented
        default value of True.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.showTypes()
        self.assertTrue(dumper._VarDumper__show_types)

    def testShowTypesFalse(self) -> None:
        """Verify that showTypes(show=False) stores False.

        Ensures the flag can be explicitly disabled so type information
        is omitted from panel titles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.showTypes(show=False)
        self.assertFalse(dumper._VarDumper__show_types)

    def testShowTypesRaisesTypeError(self) -> None:
        """Verify that showTypes raises TypeError when show is not a bool.

        Ensures invalid argument types are rejected early with a descriptive
        error rather than silently mis-configuring the dumper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.showTypes(show="yes")  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  showIndex                                                         #
    # ------------------------------------------------------------------ #

    def testShowIndexReturnsSelf(self) -> None:
        """Verify that showIndex returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so callers can
        chain configuration calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.showIndex()
        self.assertIs(result, dumper)

    def testShowIndexDefaultTrue(self) -> None:
        """Verify that showIndex() called with its default argument stores True.

        Ensures that omitting the keyword argument uses the documented
        default value of True.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.showIndex()
        self.assertTrue(dumper._VarDumper__show_index)

    def testShowIndexFalse(self) -> None:
        """Verify that showIndex(show=False) stores False.

        Ensures the flag can be explicitly disabled so index numbers
        are omitted from panel titles.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.showIndex(show=False)
        self.assertFalse(dumper._VarDumper__show_index)

    def testShowIndexRaisesTypeError(self) -> None:
        """Verify that showIndex raises TypeError when show is not a bool.

        Ensures invalid argument types are rejected early with a descriptive
        error rather than silently mis-configuring the dumper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.showIndex(show=1)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  expandAll                                                         #
    # ------------------------------------------------------------------ #

    def testExpandAllReturnsSelf(self) -> None:
        """Verify that expandAll returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so callers can
        chain configuration calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.expandAll()
        self.assertIs(result, dumper)

    def testExpandAllDefaultTrue(self) -> None:
        """Verify that expandAll() called with its default argument stores True.

        Ensures that omitting the keyword argument uses the documented
        default value of True.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.expandAll()
        self.assertTrue(dumper._VarDumper__expand_all)

    def testExpandAllFalse(self) -> None:
        """Verify that expandAll(expand=False) stores False.

        Ensures nested data structures can be rendered collapsed by
        explicitly disabling full expansion.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.expandAll(expand=False)
        self.assertFalse(dumper._VarDumper__expand_all)

    def testExpandAllRaisesTypeError(self) -> None:
        """Verify that expandAll raises TypeError when expand is not a bool.

        Ensures invalid argument types are rejected early with a descriptive
        error rather than silently mis-configuring the dumper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.expandAll(expand=0)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  maxDepth                                                          #
    # ------------------------------------------------------------------ #

    def testMaxDepthReturnsSelf(self) -> None:
        """Verify that maxDepth returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so callers can
        chain configuration calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.maxDepth(5)
        self.assertIs(result, dumper)

    def testMaxDepthNone(self) -> None:
        """Verify that maxDepth(None) stores None to indicate unlimited depth.

        Ensures callers can explicitly configure the dumper to traverse
        nested structures without any depth restriction.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.maxDepth(None)
        self.assertIsNone(dumper._VarDumper__max_depth)

    def testMaxDepthPositiveInt(self) -> None:
        """Verify that maxDepth stores a positive integer depth limit.

        Ensures the configured depth is preserved exactly and passed on
        to the Rich Pretty renderer for nested structure formatting.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.maxDepth(3)
        self.assertEqual(dumper._VarDumper__max_depth, 3)

    def testMaxDepthZero(self) -> None:
        """Verify that maxDepth(0) is accepted as a valid edge case.

        Ensures the boundary value of zero is treated as a legal integer
        and stored without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.maxDepth(0)
        self.assertEqual(dumper._VarDumper__max_depth, 0)

    def testMaxDepthRaisesTypeError(self) -> None:
        """Verify that maxDepth raises TypeError for a non-int, non-None argument.

        Ensures strings, floats, and other invalid types are rejected
        before they can corrupt the internal configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.maxDepth("deep")  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  modulePath                                                        #
    # ------------------------------------------------------------------ #

    def testModulePathReturnsSelf(self) -> None:
        """Verify that modulePath returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so callers can
        chain configuration calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.modulePath("some.module")
        self.assertIs(result, dumper)

    def testModulePathNone(self) -> None:
        """Verify that modulePath(None) stores None.

        Ensures the module path can be cleared or left unset, causing the
        dumper to resolve the caller's module automatically at print time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.modulePath(None)
        self.assertIsNone(dumper._VarDumper__module_path)

    def testModulePathString(self) -> None:
        """Verify that modulePath stores the provided module path string verbatim.

        Ensures the configured value is preserved exactly and used in the
        dump header instead of the auto-resolved caller module name.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.modulePath("orionis.app.module")
        self.assertEqual(dumper._VarDumper__module_path, "orionis.app.module")

    def testModulePathRaisesTypeError(self) -> None:
        """Verify that modulePath raises TypeError for a non-str, non-None argument.

        Ensures numeric values and other invalid types are rejected before
        they can produce malformed header output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.modulePath(123)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  lineNumber                                                        #
    # ------------------------------------------------------------------ #

    def testLineNumberReturnsSelf(self) -> None:
        """Verify that lineNumber returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so callers can
        chain configuration calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.lineNumber(42)
        self.assertIs(result, dumper)

    def testLineNumberNone(self) -> None:
        """Verify that lineNumber(None) stores None.

        Ensures the line number can be cleared so the dumper resolves
        the caller's line automatically at print time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.lineNumber(None)
        self.assertIsNone(dumper._VarDumper__line_number)

    def testLineNumberPositiveInt(self) -> None:
        """Verify that lineNumber stores the provided integer line number.

        Ensures the configured line number is preserved exactly and shown
        in the dump header without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.lineNumber(99)
        self.assertEqual(dumper._VarDumper__line_number, 99)

    def testLineNumberRaisesTypeError(self) -> None:
        """Verify that lineNumber raises TypeError for a non-int, non-None argument.

        Ensures string values and other invalid types are rejected before
        they can produce invalid header output.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.lineNumber("42")  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  forceExit                                                         #
    # ------------------------------------------------------------------ #

    def testForceExitReturnsSelf(self) -> None:
        """Verify that forceExit returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so callers can
        chain configuration calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.forceExit()
        self.assertIs(result, dumper)

    def testForceExitDefaultTrue(self) -> None:
        """Verify that forceExit() called with its default argument stores True.

        Ensures that calling forceExit() without an explicit argument
        enables the force-exit behaviour as documented.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.forceExit()
        self.assertTrue(dumper._VarDumper__force_exit)

    def testForceExitFalse(self) -> None:
        """Verify that forceExit(force=False) stores False.

        Ensures the flag can be explicitly disabled so the dumper does
        not terminate the process after printing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.forceExit(force=False)
        self.assertFalse(dumper._VarDumper__force_exit)

    def testForceExitRaisesTypeError(self) -> None:
        """Verify that forceExit raises TypeError when force is not a bool.

        Ensures non-boolean values like integers are rejected with a
        descriptive error rather than silently mis-configuring the dumper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.forceExit(force=1)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  redirectOutput                                                    #
    # ------------------------------------------------------------------ #

    def testRedirectOutputReturnsSelf(self) -> None:
        """Verify that redirectOutput returns the VarDumper instance for chaining.

        Ensures the fluent interface contract is honoured so callers can
        chain configuration calls without capturing intermediate results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.redirectOutput()
        self.assertIs(result, dumper)

    def testRedirectOutputDefaultTrue(self) -> None:
        """Verify that redirectOutput() called with its default argument stores True.

        Ensures that omitting the keyword argument enables output redirection
        as documented.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.redirectOutput()
        self.assertTrue(dumper._VarDumper__redirect_output)

    def testRedirectOutputFalse(self) -> None:
        """Verify that redirectOutput(redirect=False) stores False.

        Ensures stdout and stderr restoration can be explicitly disabled
        when the caller manages streams independently.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.redirectOutput(redirect=False)
        self.assertFalse(dumper._VarDumper__redirect_output)

    def testRedirectOutputRaisesTypeError(self) -> None:
        """Verify that redirectOutput raises TypeError when redirect is not a bool.

        Ensures invalid argument types are rejected early with a descriptive
        error rather than silently mis-configuring the dumper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        with self.assertRaises(TypeError):
            dumper.redirectOutput(redirect="yes")  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    #  value                                                             #
    # ------------------------------------------------------------------ #

    def testValueReturnsSelf(self) -> None:
        """Verify that value returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so multiple
        values can be added with consecutive chained calls.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.value("hello")
        self.assertIs(result, dumper)

    def testValueStoresSingleValue(self) -> None:
        """Verify that a single call to value adds exactly one entry to the args list.

        Ensures that each call to value produces exactly one stored entry
        without duplicating or discarding the argument.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        self.assertEqual(len(dumper._VarDumper__args), 0)
        dumper.value("hello")
        self.assertEqual(len(dumper._VarDumper__args), 1)

    def testValueStoresTypeInfo(self) -> None:
        """Verify that value records the type name alongside the stored value.

        Ensures the internal entry contains a 'type' key with the
        class name so it can be rendered in the panel title.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.value(42)
        entry = dumper._VarDumper__args[0]
        self.assertIn("type", entry)
        self.assertEqual(entry["type"], "int")

    def testValueDeepCopies(self) -> None:
        """Verify that value deep-copies the argument so later mutations are isolated.

        Ensures mutations to the original object after calling value do not
        affect the data that will be rendered at print time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        original = [1, 2, 3]
        dumper.value(original)
        original.append(4)
        stored = dumper._VarDumper__args[0]["value"]
        self.assertNotIn(4, stored)

    def testValueAcceptsDiverseTypes(self) -> None:
        """Verify that value accepts Python built-in types without raising errors.

        Ensures None, bool, float, dict, tuple, and list are all accepted
        so the dumper can handle any value a caller might pass.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        for v in (None, True, 3.14, {"key": "val"}, (1, 2), [1, 2]):
            dumper.value(v)
        self.assertEqual(len(dumper._VarDumper__args), 6)

    # ------------------------------------------------------------------ #
    #  values                                                            #
    # ------------------------------------------------------------------ #

    def testValuesReturnsSelf(self) -> None:
        """Verify that values returns the VarDumper instance for method chaining.

        Ensures the fluent interface contract is honoured so callers can
        continue configuring the dumper after providing their data.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.values(1, 2, 3)
        self.assertIs(result, dumper)

    def testValuesStoresAllArguments(self) -> None:
        """Verify that all positional arguments provided to values are stored.

        Ensures every argument passed to values ends up as a separate
        entry in the internal args list ready for rendering.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.values("a", "b", "c")
        self.assertEqual(len(dumper._VarDumper__args), 3)

    def testValuesWithNoArguments(self) -> None:
        """Verify that calling values with no arguments does not raise an error.

        Ensures the empty-call edge case is handled gracefully and the
        instance remains valid for subsequent use.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.values()
        self.assertIs(result, dumper)
        self.assertEqual(len(dumper._VarDumper__args), 0)

    def testValuesCumulatesWithValue(self) -> None:
        """Verify that values and value calls accumulate entries together.

        Ensures entries added via value and values are combined in the
        same internal list so the full set is printed together.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.value("first")
        dumper.values("second", "third")
        self.assertEqual(len(dumper._VarDumper__args), 3)

    # ------------------------------------------------------------------ #
    #  print                                                             #
    # ------------------------------------------------------------------ #

    def testPrintReturnsNone(self) -> None:
        """Verify that the print method always returns None.

        Ensures print is a pure side-effect method that does not
        accidentally return a value that callers might depend on.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.value("test")
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintCallsConsole(self) -> None:
        """Verify that print delegates rendering to the internal Rich Console.

        Ensures all formatted output goes through the Console instance
        and is not written directly to stdout.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        dumper.value("test")
        dumper.print()
        self.assertTrue(mock_con.print.called)

    def testPrintCallsConsoleMultipleTimesWithValue(self) -> None:
        """Verify that print calls Console.print at least twice when a value is stored.

        Ensures the header and the value panel are printed as separate
        Console.print calls rather than combined into one.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        dumper.value("test")
        dumper.print()
        self.assertGreaterEqual(mock_con.print.call_count, 2)

    def testPrintWithInsertLine(self) -> None:
        """Verify that print(insert_line=True) completes without errors.

        Ensures the optional blank-line padding around output can be
        enabled without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.value("test")
        with patch("builtins.print"):
            result = dumper.print(insert_line=True)
        self.assertIsNone(result)

    def testPrintWithPresetModuleAndLine(self) -> None:
        """Verify that print uses the pre-configured module path and line number.

        Ensures that when both modulePath and lineNumber are set manually
        the auto-resolver is bypassed and print completes normally.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.modulePath("custom.module")
        dumper.lineNumber(10)
        dumper.value("x")
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithNoStoredValues(self) -> None:
        """Verify that print completes without error when no values have been stored.

        Ensures the empty-args edge case is handled gracefully and only a
        header is rendered without attempting to iterate over panels.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithShowTypesDisabled(self) -> None:
        """Verify that print works correctly when type display is disabled.

        Ensures disabling showTypes produces no error and the panel
        is rendered without a type annotation in the title.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.showTypes(show=False)
        dumper.value({"a": 1})
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithShowIndexDisabled(self) -> None:
        """Verify that print works correctly when index display is disabled.

        Ensures disabling showIndex produces no error and the panel
        is rendered without an index number in the title.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.showIndex(show=False)
        dumper.value([1, 2, 3])
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithBothFlagsDisabled(self) -> None:
        """Verify that print works when both showTypes and showIndex are disabled.

        Ensures the panel is rendered with no title when both display
        flags are False without causing any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        dumper.showTypes(show=False)
        dumper.showIndex(show=False)
        dumper.value("no title panel")
        result = dumper.print()
        self.assertIsNone(result)

    def testPrintWithMaxDepthSet(self) -> None:
        """Verify that print works correctly with a non-default max depth.

        Ensures that setting a depth limit propagates to the panel
        renderer without raising errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Verify that toHtml returns a string value.

        Ensures the method produces a serialisable HTML representation
        that callers can write to a file or send over HTTP.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        mock_con.export_html.return_value = "<html><body>output</body></html>"
        dumper.value("test")
        result = dumper.toHtml()
        self.assertIsInstance(result, str)

    def testToHtmlCallsExportHtml(self) -> None:
        """Verify that toHtml delegates to Console.export_html for HTML generation.

        Ensures the method uses the Rich Console's built-in export feature
        rather than implementing its own serialisation logic.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        mock_con.export_html.return_value = "<html></html>"
        dumper.value("content")
        dumper.toHtml()
        mock_con.export_html.assert_called_once()

    def testToHtmlWithInsertLine(self) -> None:
        """Verify that toHtml(insert_line=True) completes without errors.

        Ensures the optional blank-line padding can be enabled in the
        HTML export path without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        mock_con.export_html.return_value = "<html></html>"
        dumper.value("test")
        with patch("builtins.print"):
            result = dumper.toHtml(insert_line=True)
        self.assertIsInstance(result, str)

    def testToHtmlWithNoValues(self) -> None:
        """Verify that toHtml completes without error when no values are stored.

        Ensures callers can obtain an HTML export of an empty dump session
        without having to add any values first.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        mock_con = dumper._VarDumper__console
        mock_con.export_html.return_value = "<html></html>"
        result = dumper.toHtml()
        self.assertIsInstance(result, str)

    # ------------------------------------------------------------------ #
    #  forceExit behaviour                                               #
    # ------------------------------------------------------------------ #

    def testForceExitTriggersSysExit(self) -> None:
        """Verify that print calls sys.exit(1) after dumping when forceExit is enabled.

        Ensures the process-termination behaviour is triggered at the
        correct point in the output pipeline with the expected exit code.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Verify that all setter methods can be chained on a single instance.

        Ensures the fluent API is consistent across all configuration
        methods and that the final reference is the original VarDumper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
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
        """Verify that value and values can be chained alongside configuration methods.

        Ensures the fluent API allows interleaving configuration and data
        additions without losing the instance reference.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        dumper = self._make()
        result = dumper.value("a").value("b").values("c", "d")
        self.assertIs(result, dumper)
        self.assertEqual(len(dumper._VarDumper__args), 4)
