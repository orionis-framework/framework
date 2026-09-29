from __future__ import annotations
import inspect
from unittest.mock import MagicMock, patch
from orionis.console.output.contracts.var_dumper import IVarDumper
from orionis.console.output.var_dumper import VarDumper
from orionis.test import TestCase

class TestIVarDumperContract(TestCase):

    # ------------------------------------------------------------------ #
    #  Abstract class characteristics                                    #
    # ------------------------------------------------------------------ #

    def testIsAbstractClass(self) -> None:
        """Verify that IVarDumper is recognised as an abstract class.

        Ensures the interface declares at least one abstract method so
        Python prevents direct instantiation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.isabstract(IVarDumper))

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Verify that IVarDumper cannot be instantiated directly.

        Ensures that attempting to create an instance raises TypeError
        due to unimplemented abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            IVarDumper()  # type: ignore[abstract]

    def testHasExactlyTwelveAbstractMethods(self) -> None:
        """Verify that IVarDumper declares exactly twelve abstract methods.

        Ensures the interface surface area is stable and that no methods
        have been silently added or removed without updating consumers.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(len(IVarDumper.__abstractmethods__), 12)

    # ------------------------------------------------------------------ #
    #  Abstract methods presence                                         #
    # ------------------------------------------------------------------ #

    def testShowTypesIsAbstract(self) -> None:
        """Verify that showTypes is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the showTypes configuration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("showTypes", IVarDumper.__abstractmethods__)

    def testShowIndexIsAbstract(self) -> None:
        """Verify that showIndex is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the showIndex configuration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("showIndex", IVarDumper.__abstractmethods__)

    def testExpandAllIsAbstract(self) -> None:
        """Verify that expandAll is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the expandAll configuration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("expandAll", IVarDumper.__abstractmethods__)

    def testMaxDepthIsAbstract(self) -> None:
        """Verify that maxDepth is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the maxDepth configuration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("maxDepth", IVarDumper.__abstractmethods__)

    def testModulePathIsAbstract(self) -> None:
        """Verify that modulePath is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the modulePath configuration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("modulePath", IVarDumper.__abstractmethods__)

    def testLineNumberIsAbstract(self) -> None:
        """Verify that lineNumber is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the lineNumber configuration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("lineNumber", IVarDumper.__abstractmethods__)

    def testForceExitIsAbstract(self) -> None:
        """Verify that forceExit is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the forceExit configuration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("forceExit", IVarDumper.__abstractmethods__)

    def testRedirectOutputIsAbstract(self) -> None:
        """Verify that redirectOutput is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the redirectOutput configuration method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("redirectOutput", IVarDumper.__abstractmethods__)

    def testValuesIsAbstract(self) -> None:
        """Verify that values is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the bulk-value storage method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("values", IVarDumper.__abstractmethods__)

    def testValueIsAbstract(self) -> None:
        """Verify that value is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the single-value storage method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("value", IVarDumper.__abstractmethods__)

    def testPrintIsAbstract(self) -> None:
        """Verify that print is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the terminal-output method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("print", IVarDumper.__abstractmethods__)

    def testToHtmlIsAbstract(self) -> None:
        """Verify that toHtml is listed in IVarDumper.__abstractmethods__.

        Ensures every concrete subclass is forced to provide an
        implementation of the HTML-export method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("toHtml", IVarDumper.__abstractmethods__)

    # ------------------------------------------------------------------ #
    #  Signature verification                                            #
    # ------------------------------------------------------------------ #

    def testShowTypesSignatureDefaultShow(self) -> None:
        """Verify that showTypes has a keyword-only 'show' parameter defaulting to True.

        Ensures callers can call showTypes() without arguments to enable
        type display using the documented default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IVarDumper.showTypes)
        params = sig.parameters
        self.assertIn("show", params)
        self.assertEqual(params["show"].default, True)
        self.assertEqual(params["show"].kind, inspect.Parameter.KEYWORD_ONLY)

    def testShowIndexSignatureDefaultShow(self) -> None:
        """Verify that showIndex has a keyword-only 'show' parameter defaulting to True.

        Ensures callers can call showIndex() without arguments to enable
        index display using the documented default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IVarDumper.showIndex)
        params = sig.parameters
        self.assertIn("show", params)
        self.assertEqual(params["show"].default, True)
        self.assertEqual(params["show"].kind, inspect.Parameter.KEYWORD_ONLY)

    def testMaxDepthSignatureHasDepthParam(self) -> None:
        """Verify that maxDepth declares a positional 'depth' parameter.

        Ensures the parameter name matches the documented interface so
        callers are not surprised by unexpected keyword names.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IVarDumper.maxDepth)
        self.assertIn("depth", sig.parameters)

    def testModulePathSignatureHasPathParam(self) -> None:
        """Verify that modulePath declares a positional 'path' parameter.

        Ensures the parameter name matches the documented interface so
        callers are not surprised by unexpected keyword names.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IVarDumper.modulePath)
        self.assertIn("path", sig.parameters)

    def testLineNumberSignatureHasNumberParam(self) -> None:
        """Verify that lineNumber declares a positional 'number' parameter.

        Ensures the parameter name matches the documented interface so
        callers are not surprised by unexpected keyword names.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IVarDumper.lineNumber)
        self.assertIn("number", sig.parameters)

    def testPrintSignatureHasInsertLineDefault(self) -> None:
        """Verify that print has a keyword-only 'insert_line' param defaulting to False.

        Ensures callers can call print() without arguments to produce
        output without extra blank lines as documented.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IVarDumper.print)
        params = sig.parameters
        self.assertIn("insert_line", params)
        self.assertEqual(params["insert_line"].default, False)
        self.assertEqual(params["insert_line"].kind, inspect.Parameter.KEYWORD_ONLY)

    def testToHtmlSignatureHasInsertLineDefault(self) -> None:
        """Verify that toHtml() defaults keyword-only insert_line to False.

        Ensures callers can call toHtml() without arguments to generate
        HTML without extra blank lines as documented.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IVarDumper.toHtml)
        params = sig.parameters
        self.assertIn("insert_line", params)
        self.assertEqual(params["insert_line"].default, False)
        self.assertEqual(params["insert_line"].kind, inspect.Parameter.KEYWORD_ONLY)

    def testValueSignatureHasValueParam(self) -> None:
        """Verify that value declares a positional 'value' parameter.

        Ensures the method signature aligns with the documented interface
        so callers know exactly what argument name to use.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(IVarDumper.value)
        self.assertIn("value", sig.parameters)

    # ------------------------------------------------------------------ #
    #  VarDumper conformance                                             #
    # ------------------------------------------------------------------ #

    def testVarDumperIsSubclassOfIVarDumper(self) -> None:
        """Verify that VarDumper is a subclass of IVarDumper.

        Ensures the concrete class satisfies the abstract interface
        so it can be used anywhere IVarDumper is expected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(VarDumper, IVarDumper))

    def testVarDumperCanBeInstantiated(self) -> None:
        """Verify that VarDumper can be instantiated without raising errors.

        Ensures the concrete class provides implementations for all
        abstract methods declared by IVarDumper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with patch("orionis.console.output.var_dumper.Console") as mock_console:
            mock_con = MagicMock()
            mock_con.size.width = 120
            mock_console.return_value = mock_con
            dumper = VarDumper()
        self.assertIsInstance(dumper, VarDumper)

    def testVarDumperIsInstanceOfIVarDumper(self) -> None:
        """Verify that a VarDumper instance passes isinstance(obj, IVarDumper).

        Ensures polymorphic usage is valid so any code accepting an
        IVarDumper can transparently receive a VarDumper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with patch("orionis.console.output.var_dumper.Console") as mock_console:
            mock_con = MagicMock()
            mock_con.size.width = 120
            mock_console.return_value = mock_con
            dumper = VarDumper()
        self.assertIsInstance(dumper, IVarDumper)

    def testVarDumperImplementsAllAbstractMethods(self) -> None:
        """Verify that VarDumper implements all methods declared abstract in IVarDumper.

        Ensures no abstract method was accidentally left unimplemented in
        the concrete class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        abstract_names = IVarDumper.__abstractmethods__
        for name in abstract_names:
            method = getattr(VarDumper, name, None)
            self.assertIsNotNone(
                method,
                msg=f"VarDumper is missing implementation for '{name}'",
            )
            is_concrete = inspect.isfunction(method) or isinstance(method, property)
            self.assertTrue(
                is_concrete,
                msg=f"VarDumper.{name} is not a concrete implementation",
            )
