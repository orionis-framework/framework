from __future__ import annotations
import inspect
from unittest.mock import MagicMock, patch
from orionis.console.debug.dumper import Dumper
from orionis.console.debug.contracts.dumper import IDumper
from orionis.test import TestCase

class TestDumper(TestCase):

    # ------------------------------------------------------------------ #
    #  Interface & instantiation                                         #
    # ------------------------------------------------------------------ #

    def testInheritsFromIDumper(self) -> None:
        """Verify that Dumper inherits from IDumper.

        Ensures the implementation follows the expected class hierarchy
        and satisfies the abstract interface contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Dumper, IDumper))

    def testDumperIsNotAbstract(self) -> None:
        """Verify that Dumper can be instantiated without errors.

        Ensures that all abstract methods from IDumper have been
        implemented, allowing direct instantiation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = Dumper()
        self.assertIsInstance(instance, Dumper)

    def testDdAndDumpAreStaticMethods(self) -> None:
        """Verify that dd and dump are defined as static methods.

        Ensures they can be called directly on the class without
        requiring an instance, matching the interface contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(
            inspect.getattr_static(Dumper, "dd"),
            staticmethod,
        )
        self.assertIsInstance(
            inspect.getattr_static(Dumper, "dump"),
            staticmethod,
        )

    def testDdAndDumpAreNotCoroutines(self) -> None:
        """Verify that dd and dump are synchronous functions.

        Ensures neither static method is a coroutine function,
        since variable dumping is a synchronous operation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(inspect.iscoroutinefunction(Dumper.dd))
        self.assertFalse(inspect.iscoroutinefunction(Dumper.dump))

    # ------------------------------------------------------------------ #
    #  dump() — normal operation (no sys.exit)                           #
    # ------------------------------------------------------------------ #

    def testDumpDoesNotRaiseForSimpleValue(self) -> None:
        """Verify that dump() does not raise for a simple scalar value.

        Ensures that dumping a plain integer completes without error
        and does not terminate the process.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump(42)
            mock_vd.print.assert_called_once_with(insert_line=False)

    def testDumpPassesShowTypesFlag(self) -> None:
        """Verify that dump() forwards show_types to VarDumper.showTypes().

        Ensures the boolean flag is passed unchanged to the underlying
        VarDumper fluent builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump("hello", show_types=True)
            mock_vd.showTypes.assert_called_once_with(show=True)

    def testDumpPassesShowIndexFlag(self) -> None:
        """Verify that dump() forwards show_index to VarDumper.showIndex().

        Ensures the flag value is passed without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump("x", show_index=True)
            mock_vd.showIndex.assert_called_once_with(show=True)

    def testDumpPassesExpandAllFlag(self) -> None:
        """Verify that dump() forwards expand_all to VarDumper.expandAll().

        Ensures the flag controls whether nested structures are expanded.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump([], expand_all=False)
            mock_vd.expandAll.assert_called_once_with(expand=False)

    def testDumpPassesMaxDepth(self) -> None:
        """Verify that dump() forwards max_depth to VarDumper.maxDepth().

        Ensures the integer depth limit is passed to the builder.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump({}, max_depth=3)
            mock_vd.maxDepth.assert_called_once_with(3)

    def testDumpPassesModulePathAndLineNumber(self) -> None:
        """Verify that dump() forwards module_path and line_number to VarDumper.

        Ensures custom caller information is propagated to the builder
        instead of being auto-resolved.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump("v", module_path="my.module", line_number=99)
            mock_vd.modulePath.assert_called_once_with("my.module")
            mock_vd.lineNumber.assert_called_once_with(99)

    def testDumpPassesInsertLineFlag(self) -> None:
        """Verify that dump() forwards insert_line to VarDumper.print().

        Ensures the flag that controls blank-line insertion is passed
        through to the final print call.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump("v", insert_line=True)
            mock_vd.print.assert_called_once_with(insert_line=True)

    def testDumpSetsForceExitFalse(self) -> None:
        """Verify that dump() calls forceExit(force=False) on VarDumper.

        Ensures that dump never terminates execution, distinguishing it
        from the dd variant.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump("no exit")
            mock_vd.forceExit.assert_called_once_with(force=False)

    def testDumpPassesMultipleArgs(self) -> None:
        """Verify that dump() forwards all positional arguments to VarDumper.values().

        Ensures the variadic *args are passed as a tuple to the values() call.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump(1, "two", [3])
            mock_vd.values.assert_called_once_with(1, "two", [3])

    # ------------------------------------------------------------------ #
    #  dd() — forces exit                                                #
    # ------------------------------------------------------------------ #

    def testDdSetsForceExitTrue(self) -> None:
        """Verify that dd() calls forceExit(force=True) on VarDumper.

        Ensures that dd is configured to terminate execution after
        dumping, distinguishing it from dump.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dd("check exit")
            mock_vd.forceExit.assert_called_once_with(force=True)

    def testDdPassesAllConfigurationFlags(self) -> None:
        """Verify that dd() forwards all keyword flags to VarDumper.

        Ensures that each configuration option is passed correctly
        through the fluent builder when calling dd.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dd(
                "data",
                show_types=True,
                show_index=True,
                expand_all=False,
                max_depth=2,
                module_path="my.mod",
                line_number=10,
                redirect_output=True,
                insert_line=True,
            )
            mock_vd.showTypes.assert_called_once_with(show=True)
            mock_vd.showIndex.assert_called_once_with(show=True)
            mock_vd.expandAll.assert_called_once_with(expand=False)
            mock_vd.maxDepth.assert_called_once_with(2)
            mock_vd.modulePath.assert_called_once_with("my.mod")
            mock_vd.lineNumber.assert_called_once_with(10)
            mock_vd.redirectOutput.assert_called_once_with(redirect=True)
            mock_vd.forceExit.assert_called_once_with(force=True)
            mock_vd.print.assert_called_once_with(insert_line=True)

    def testDdPassesMultipleArgs(self) -> None:
        """Verify that dd() forwards all positional arguments to VarDumper.values().

        Ensures the variadic *args are transmitted without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dd(10, 20, 30)
            mock_vd.values.assert_called_once_with(10, 20, 30)

    # ------------------------------------------------------------------ #
    #  Edge cases                                                        #
    # ------------------------------------------------------------------ #

    def testDumpWithNoArgs(self) -> None:
        """Verify that dump() handles being called with no positional arguments.

        Ensures VarDumper.values() is called with an empty argument list
        without raising any exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump()
            mock_vd.values.assert_called_once_with()

    def testDdWithNoArgs(self) -> None:
        """Verify that dd() handles being called with no positional arguments.

        Ensures VarDumper.values() is called with an empty argument list
        and forceExit is still set to True.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dd()
            mock_vd.values.assert_called_once_with()
            mock_vd.forceExit.assert_called_once_with(force=True)

    def testDumpWithNoneMaxDepth(self) -> None:
        """Verify that dump() correctly passes max_depth=None to VarDumper.

        Ensures the None value for unlimited depth is transmitted
        without being converted or replaced.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump("v", max_depth=None)
            mock_vd.maxDepth.assert_called_once_with(None)

    def testDumpWithComplexNestedValue(self) -> None:
        """Verify that dump() handles a complex nested data structure without raising.

        Ensures that deeply nested dicts and lists are forwarded to
        VarDumper.values() without modification or error.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        nested = {"a": {"b": {"c": [1, 2, {"d": 3}]}}}

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump(nested)
            mock_vd.values.assert_called_once_with(nested)

    def testDumpDefaultsMatchInterface(self) -> None:
        """Verify that Dumper.dump uses the same defaults as defined in IDumper.

        Ensures that calling dump with no keyword arguments invokes VarDumper
        with the exact default values specified in the interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dump("v")
            mock_vd.showTypes.assert_called_once_with(show=False)
            mock_vd.showIndex.assert_called_once_with(show=False)
            mock_vd.expandAll.assert_called_once_with(expand=True)
            mock_vd.maxDepth.assert_called_once_with(None)
            mock_vd.modulePath.assert_called_once_with(None)
            mock_vd.lineNumber.assert_called_once_with(None)
            mock_vd.redirectOutput.assert_called_once_with(redirect=False)
            mock_vd.forceExit.assert_called_once_with(force=False)
            mock_vd.print.assert_called_once_with(insert_line=False)

    def testDdDefaultsMatchInterface(self) -> None:
        """Verify that Dumper.dd uses the same defaults as defined in IDumper.

        Ensures that calling dd with no keyword arguments invokes VarDumper
        with the exact default values, except forceExit which must be True.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        mock_vd = MagicMock()
        mock_vd.showTypes.return_value = mock_vd
        mock_vd.showIndex.return_value = mock_vd
        mock_vd.expandAll.return_value = mock_vd
        mock_vd.maxDepth.return_value = mock_vd
        mock_vd.modulePath.return_value = mock_vd
        mock_vd.lineNumber.return_value = mock_vd
        mock_vd.redirectOutput.return_value = mock_vd
        mock_vd.forceExit.return_value = mock_vd
        mock_vd.values.return_value = mock_vd
        mock_vd.print.return_value = None

        with patch("orionis.console.debug.dumper.VarDumper", return_value=mock_vd):
            Dumper.dd("v")
            mock_vd.showTypes.assert_called_once_with(show=False)
            mock_vd.showIndex.assert_called_once_with(show=False)
            mock_vd.expandAll.assert_called_once_with(expand=True)
            mock_vd.maxDepth.assert_called_once_with(None)
            mock_vd.modulePath.assert_called_once_with(None)
            mock_vd.lineNumber.assert_called_once_with(None)
            mock_vd.redirectOutput.assert_called_once_with(redirect=False)
            mock_vd.forceExit.assert_called_once_with(force=True)
            mock_vd.print.assert_called_once_with(insert_line=False)
