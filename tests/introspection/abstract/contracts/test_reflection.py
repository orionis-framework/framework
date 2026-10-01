from abc import ABC
from inspect import isabstract
from orionis.introspection.abstract.contracts.reflection import (
    IReflectionAbstract,
)
from orionis.test import TestCase

class TestIReflectionAbstractBaseType(TestCase):

    def testInheritsFromABC(self) -> None:
        """
        Assert that IReflectionAbstract inherits from ABC.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        Verifies that abc.ABC is present in the MRO.
        """
        self.assertTrue(issubclass(IReflectionAbstract, ABC))

    def testIsAbstractClass(self) -> None:
        """
        Assert that inspect.isabstract identifies IReflectionAbstract as abstract.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        Only classes with at least one unimplemented abstract method pass.
        """
        self.assertTrue(isabstract(IReflectionAbstract))

    def testCannotInstantiateDirectly(self) -> None:
        """
        Assert that instantiating IReflectionAbstract directly raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        Python raises TypeError for classes with unimplemented abstract methods.
        """
        with self.assertRaises(TypeError):
            IReflectionAbstract()

    def testAbstractMethodsSetIsNonEmpty(self) -> None:
        """
        Assert that __abstractmethods__ is a non-empty frozenset.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        Ensures at least one abstract method is declared on the interface.
        """
        self.assertGreater(len(IReflectionAbstract.__abstractmethods__), 0)

    def testPartialSubclassCannotBeInstantiated(self) -> None:
        """
        Assert that a subclass implementing only one method cannot be created.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        All abstract methods must be implemented before instantiation is allowed.
        """
        # Subclass that only overrides one of many required abstract methods

        class _PartialImpl(IReflectionAbstract):
            def getClass(self):
                """Implement the ``getClass`` contract stub.

                Returns
                -------
                object
                    Value produced by the helper.
                """
                return

        with self.assertRaises(TypeError):
            _PartialImpl()

class TestIReflectionAbstractAttributeMethods(TestCase):
    """Tests that IReflectionAbstract declares the expected attribute methods."""

    def testHasAbstractMethodGetClass(self) -> None:
        """
        Assert that getClass is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.

        Notes
        -----
        Checks __abstractmethods__ frozenset membership.
        """
        self.assertIn("getClass", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetClassName(self) -> None:
        """
        Assert that getClassName is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getClassName", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetModuleName(self) -> None:
        """
        Assert that getModuleName is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getModuleName", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetModuleWithClassName(self) -> None:
        """
        Assert that getModuleWithClassName is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getModuleWithClassName",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetDocstring(self) -> None:
        """
        Assert that getDocstring is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getDocstring", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetBaseClasses(self) -> None:
        """
        Assert that getBaseClasses is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getBaseClasses", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetSourceCode(self) -> None:
        """
        Assert that getSourceCode is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getSourceCode", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetFile(self) -> None:
        """
        Assert that getFile is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getFile", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetAnnotations(self) -> None:
        """
        Assert that getAnnotations is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getAnnotations", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodHasAttribute(self) -> None:
        """
        Assert that hasAttribute is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("hasAttribute", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetAttribute(self) -> None:
        """
        Assert that getAttribute is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getAttribute", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodSetAttribute(self) -> None:
        """
        Assert that setAttribute is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("setAttribute", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodRemoveAttribute(self) -> None:
        """
        Assert that removeAttribute is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("removeAttribute", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetAttributes(self) -> None:
        """
        Assert that getAttributes is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getAttributes", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetPublicAttributes(self) -> None:
        """
        Assert that getPublicAttributes is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getPublicAttributes",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetProtectedAttributes(self) -> None:
        """
        Assert that getProtectedAttributes is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getProtectedAttributes",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetPrivateAttributes(self) -> None:
        """
        Assert that getPrivateAttributes is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getPrivateAttributes",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetDunderAttributes(self) -> None:
        """
        Assert that getDunderAttributes is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getDunderAttributes",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetMagicAttributes(self) -> None:
        """
        Assert that getMagicAttributes is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getMagicAttributes",
            IReflectionAbstract.__abstractmethods__,
        )

class TestIReflectionAbstractMethodOperations(TestCase):
    """Tests that IReflectionAbstract declares the expected method-inspection."""

    def testHasAbstractMethodHasMethod(self) -> None:
        """
        Assert that hasMethod is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("hasMethod", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodRemoveMethod(self) -> None:
        """
        Assert that removeMethod is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("removeMethod", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetMethodSignature(self) -> None:
        """
        Assert that getMethodSignature is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getMethodSignature",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetMethods(self) -> None:
        """
        Assert that getMethods is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getMethods", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetPublicMethods(self) -> None:
        """
        Assert that getPublicMethods is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getPublicMethods",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetPublicSyncMethods(self) -> None:
        """
        Assert that getPublicSyncMethods is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getPublicSyncMethods",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetPublicAsyncMethods(self) -> None:
        """
        Assert that getPublicAsyncMethods is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getPublicAsyncMethods",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetProtectedMethods(self) -> None:
        """
        Assert that getProtectedMethods is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getProtectedMethods",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetPrivateMethods(self) -> None:
        """
        Assert that getPrivateMethods is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getPrivateMethods",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetDunderMethods(self) -> None:
        """
        Assert that getDunderMethods is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getDunderMethods",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetMagicMethods(self) -> None:
        """
        Assert that getMagicMethods is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getMagicMethods",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodGetProperties(self) -> None:
        """
        Assert that getProperties is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("getProperties", IReflectionAbstract.__abstractmethods__)

    def testHasAbstractMethodGetPublicProperties(self) -> None:
        """
        Assert that getPublicProperties is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "getPublicProperties",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodConstructorSignature(self) -> None:
        """
        Assert that constructorSignature is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "constructorSignature",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodMethodSignature(self) -> None:
        """
        Assert that methodSignature is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(
            "methodSignature",
            IReflectionAbstract.__abstractmethods__,
        )

    def testHasAbstractMethodClearCache(self) -> None:
        """
        Assert that clearCache is declared as an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn("clearCache", IReflectionAbstract.__abstractmethods__)
