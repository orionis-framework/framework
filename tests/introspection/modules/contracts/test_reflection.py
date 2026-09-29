from abc import ABC
from orionis.test import TestCase
from orionis.introspection.modules.contracts.reflection import (
    IReflectionModule,
)

class _StubModule(IReflectionModule):
    """
    Minimal concrete implementation of IReflectionModule for contract tests.

    Implements every abstract method with the simplest possible body so
    that the stub can be instantiated and return types can be verified.
    """

    def getModule(self) -> object:
        """
        Return a bare object as a minimal module placeholder.

        Returns
        -------
        object
            A new bare object satisfying the contract.
        """
        return object()

    def hasClass(self, _class_name: str) -> bool:
        """
        Return False unconditionally for any class name query.

        Parameters
        ----------
        class_name : str
            Name of the class to look up.

        Returns
        -------
        bool
            Always False.
        """
        return False

    def getClass(self, _class_name: str) -> object | None:
        """
        Return None unconditionally for any class name query.

        Parameters
        ----------
        class_name : str
            Name of the class to retrieve.

        Returns
        -------
        object | None
            Always None.
        """
        return None

    def setClass(self, _class_name: str, _cls: type) -> bool:
        """
        Return True to indicate a successful class registration.

        Parameters
        ----------
        class_name : str
            Name under which the class should be stored.
        cls : type
            The class object to register.

        Returns
        -------
        bool
            Always True.
        """
        return True

    def removeClass(self, _class_name: str) -> bool:
        """
        Return True to indicate a successful class removal.

        Parameters
        ----------
        class_name : str
            Name of the class to remove.

        Returns
        -------
        bool
            Always True.
        """
        return True

    def getClasses(self) -> dict:
        """
        Return an empty dict representing no registered classes.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPublicClasses(self) -> dict:
        """
        Return an empty dict of public classes.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getProtectedClasses(self) -> dict:
        """
        Return an empty dict of protected classes.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPrivateClasses(self) -> dict:
        """
        Return an empty dict of private classes.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getConstant(self, _constant_name: str) -> object | None:
        """
        Return None unconditionally for any constant name query.

        Parameters
        ----------
        constant_name : str
            Name of the constant to retrieve.

        Returns
        -------
        object | None
            Always None.
        """
        return None

    def getConstants(self) -> dict:
        """
        Return an empty dict of all module constants.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPublicConstants(self) -> dict:
        """
        Return an empty dict of public constants.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getProtectedConstants(self) -> dict:
        """
        Return an empty dict of protected constants.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPrivateConstants(self) -> dict:
        """
        Return an empty dict of private constants.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getFunctions(self) -> dict:
        """
        Return an empty dict of all module functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPublicFunctions(self) -> dict:
        """
        Return an empty dict of public functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPublicSyncFunctions(self) -> dict:
        """
        Return an empty dict of public synchronous functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPublicAsyncFunctions(self) -> dict:
        """
        Return an empty dict of public asynchronous functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getProtectedFunctions(self) -> dict:
        """
        Return an empty dict of protected functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getProtectedSyncFunctions(self) -> dict:
        """
        Return an empty dict of protected synchronous functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getProtectedAsyncFunctions(self) -> dict:
        """
        Return an empty dict of protected asynchronous functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPrivateFunctions(self) -> dict:
        """
        Return an empty dict of private functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPrivateSyncFunctions(self) -> dict:
        """
        Return an empty dict of private synchronous functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getPrivateAsyncFunctions(self) -> dict:
        """
        Return an empty dict of private asynchronous functions.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getImports(self) -> dict:
        """
        Return an empty dict of module-level imports.

        Returns
        -------
        dict
            Always an empty dictionary.
        """
        return {}

    def getFile(self) -> str:
        """
        Return an empty string as the module file path.

        Returns
        -------
        str
            Always an empty string.
        """
        return ""

    def getSourceCode(self) -> str:
        """
        Return an empty string as the module source code.

        Returns
        -------
        str
            Always an empty string.
        """
        return ""

    def clearCache(self) -> None:
        """
        Clear the internal cache and return None.

        Returns
        -------
        None
            Always None; the cache is cleared as a side effect.
        """
        return

class _OnlyGetModule(IReflectionModule):

    def getModule(self) -> object:
        """
        Return a bare object as a minimal module placeholder.

        Returns
        -------
        object
            A new bare object satisfying the abstract contract.
        """
        return object()

class TestIReflectionModuleIsABC(TestCase):

    def testIsABC(self) -> None:
        """
        Assert that IReflectionModule inherits from ABC.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(issubclass(IReflectionModule, ABC))

    def testDirectInstantiationRaisesTypeError(self) -> None:
        """
        Assert that direct instantiation of IReflectionModule raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            IReflectionModule()

    def testStubCanBeInstantiated(self) -> None:
        """
        Assert that a complete stub implementation can be instantiated.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        stub = _StubModule()
        self.assertIsInstance(stub, IReflectionModule)

class TestIReflectionModuleAbstractMethods(TestCase):

    def _assertAbstract(self, name: str) -> None:
        """
        Assert that the named method is abstract in IReflectionModule.

        Parameters
        ----------
        name : str
            Name of the method expected in ``__abstractmethods__``.

        Returns
        -------
        None
            Raises AssertionError if the method is not abstract.
        """
        self.assertIn(name, IReflectionModule.__abstractmethods__)

    def testGetModuleIsAbstract(self) -> None:
        """
        Assert that getModule is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getModule")

    def testHasClassIsAbstract(self) -> None:
        """
        Assert that hasClass is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("hasClass")

    def testGetClassIsAbstract(self) -> None:
        """
        Assert that getClass is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getClass")

    def testSetClassIsAbstract(self) -> None:
        """
        Assert that setClass is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("setClass")

    def testRemoveClassIsAbstract(self) -> None:
        """
        Assert that removeClass is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("removeClass")

    def testGetClassesIsAbstract(self) -> None:
        """
        Assert that getClasses is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getClasses")

    def testGetPublicClassesIsAbstract(self) -> None:
        """
        Assert that getPublicClasses is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicClasses")

    def testGetProtectedClassesIsAbstract(self) -> None:
        """
        Assert that getProtectedClasses is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedClasses")

    def testGetPrivateClassesIsAbstract(self) -> None:
        """
        Assert that getPrivateClasses is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateClasses")

    def testGetConstantIsAbstract(self) -> None:
        """
        Assert that getConstant is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getConstant")

    def testGetConstantsIsAbstract(self) -> None:
        """
        Assert that getConstants is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getConstants")

    def testGetPublicConstantsIsAbstract(self) -> None:
        """
        Assert that getPublicConstants is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicConstants")

    def testGetProtectedConstantsIsAbstract(self) -> None:
        """
        Assert that getProtectedConstants is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedConstants")

    def testGetPrivateConstantsIsAbstract(self) -> None:
        """
        Assert that getPrivateConstants is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateConstants")

    def testGetFunctionsIsAbstract(self) -> None:
        """
        Assert that getFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getFunctions")

    def testGetPublicFunctionsIsAbstract(self) -> None:
        """
        Assert that getPublicFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicFunctions")

    def testGetPublicSyncFunctionsIsAbstract(self) -> None:
        """
        Assert that getPublicSyncFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicSyncFunctions")

    def testGetPublicAsyncFunctionsIsAbstract(self) -> None:
        """
        Assert that getPublicAsyncFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicAsyncFunctions")

    def testGetProtectedFunctionsIsAbstract(self) -> None:
        """
        Assert that getProtectedFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedFunctions")

    def testGetProtectedSyncFunctionsIsAbstract(self) -> None:
        """
        Assert that getProtectedSyncFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedSyncFunctions")

    def testGetProtectedAsyncFunctionsIsAbstract(self) -> None:
        """
        Assert that getProtectedAsyncFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedAsyncFunctions")

    def testGetPrivateFunctionsIsAbstract(self) -> None:
        """
        Assert that getPrivateFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateFunctions")

    def testGetPrivateSyncFunctionsIsAbstract(self) -> None:
        """
        Assert that getPrivateSyncFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateSyncFunctions")

    def testGetPrivateAsyncFunctionsIsAbstract(self) -> None:
        """
        Assert that getPrivateAsyncFunctions is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateAsyncFunctions")

    def testGetImportsIsAbstract(self) -> None:
        """
        Assert that getImports is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getImports")

    def testGetFileIsAbstract(self) -> None:
        """
        Assert that getFile is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getFile")

    def testGetSourceCodeIsAbstract(self) -> None:
        """
        Assert that getSourceCode is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getSourceCode")

    def testClearCacheIsAbstract(self) -> None:
        """
        Assert that clearCache is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("clearCache")

class TestIReflectionModulePartialImplementation(TestCase):

    def testPartialImplementationRaisesTypeError(self) -> None:
        """
        Assert that instantiating a partially implemented class raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            _OnlyGetModule()

class TestIReflectionModuleStubReturnTypes(TestCase):

    def setUp(self) -> None:
        """
        Instantiate the stub before each test.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.stub = _StubModule()

    def testGetModuleReturnsObject(self) -> None:
        """
        Assert that getModule returns an object instance.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getModule(), object)

    def testHasClassReturnsBool(self) -> None:
        """
        Assert that hasClass returns a boolean value.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.hasClass("Any"), bool)

    def testGetClassReturnsNone(self) -> None:
        """
        Assert that getClass returns None when the class is not present.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.stub.getClass("Missing"))

    def testGetClassesReturnsDict(self) -> None:
        """
        Assert that getClasses returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getClasses(), dict)

    def testGetPublicClassesReturnsDict(self) -> None:
        """
        Assert that getPublicClasses returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getPublicClasses(), dict)

    def testGetConstantsReturnsDict(self) -> None:
        """
        Assert that getConstants returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getConstants(), dict)

    def testGetFunctionsReturnsDict(self) -> None:
        """
        Assert that getFunctions returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getFunctions(), dict)

    def testGetImportsReturnsDict(self) -> None:
        """
        Assert that getImports returns a dictionary.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getImports(), dict)

    def testGetFileReturnsStr(self) -> None:
        """
        Assert that getFile returns a string.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getFile(), str)

    def testGetSourceCodeReturnsStr(self) -> None:
        """
        Assert that getSourceCode returns a string.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getSourceCode(), str)

    def testClearCacheReturnsNone(self) -> None:
        """
        Assert that clearCache returns None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.stub.clearCache())
