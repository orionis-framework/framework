import inspect
from abc import ABC
from typing import TYPE_CHECKING
from orionis.introspection.concretes.contracts.reflection import (
    IReflectionConcrete,
)
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.introspection.dependencies.entities.signature import Signature

# ---------------------------------------------------------------------------
# Minimal stub that satisfies every abstract method in IReflectionConcrete
# ---------------------------------------------------------------------------

class _StubConcrete(IReflectionConcrete):
    """Minimal concrete stub used only to verify contract compliance."""

    def getClass(self) -> type:
        """Implement the ``getClass`` contract stub.

        Returns
        -------
        type
            Value produced by the helper.
        """
        return object

    def getClassName(self) -> str:
        """Implement the ``getClassName`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "stub"

    def getModuleName(self) -> str:
        """Implement the ``getModuleName`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "stub_module"

    def getModuleWithClassName(self) -> str:
        """Implement the ``getModuleWithClassName`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "stub_module.stub"

    def getDocstring(self) -> str | None:
        """Implement the ``getDocstring`` contract stub.

        Returns
        -------
        str | None
            Value produced by the helper.
        """
        return None

    def getBaseClasses(self) -> list:
        """Implement the ``getBaseClasses`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getSourceCode(self, _method=None) -> str | None:
        """Implement the ``getSourceCode`` contract stub.

        Parameters
        ----------
        _method : object
            Value supplied for ``_method``.

        Returns
        -------
        str | None
            Value produced by the helper.
        """
        return None

    def getFile(self) -> str:
        """Implement the ``getFile`` contract stub.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "/stub.py"

    def getAnnotations(self) -> dict:
        """Implement the ``getAnnotations`` contract stub.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {}

    def hasAttribute(self, _attribute: str) -> bool:
        """Implement the ``hasAttribute`` contract stub.

        Parameters
        ----------
        _attribute : str
            Value supplied for ``_attribute``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return False

    def getAttribute(
        self, _name: str, _default: object = None,
    ) -> object:
        """Implement the ``getAttribute`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.
        _default : object
            Value supplied for ``_default``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return _default

    def setAttribute(self, _name: str, _value: object) -> bool:
        """Implement the ``setAttribute`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.
        _value : object
            Value supplied for ``_value``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True

    def removeAttribute(self, _name: str) -> bool:
        """Implement the ``removeAttribute`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True

    def getAttributes(self) -> dict:
        """Implement the ``getAttributes`` contract stub.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {}

    def getPublicAttributes(self) -> dict:
        """Implement the ``getPublicAttributes`` contract stub.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {}

    def getProtectedAttributes(self) -> dict:
        """Implement the ``getProtectedAttributes`` contract stub.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {}

    def getPrivateAttributes(self) -> dict:
        """Implement the ``getPrivateAttributes`` contract stub.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {}

    def getDunderAttributes(self) -> dict:
        """Implement the ``getDunderAttributes`` contract stub.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {}

    def getMagicAttributes(self) -> dict:
        """Implement the ``getMagicAttributes`` contract stub.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {}

    def hasMethod(self, _name: str) -> bool:
        """Implement the ``hasMethod`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return False

    def setMethod(self, _name: str, _method: object) -> bool:
        """Implement the ``setMethod`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.
        _method : object
            Value supplied for ``_method``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True

    def removeMethod(self, _name: str) -> bool:
        """Implement the ``removeMethod`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True

    def getMethodSignature(self, _name: str) -> inspect.Signature:
        """Implement the ``getMethodSignature`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.

        Returns
        -------
        inspect.Signature
            Value produced by the helper.
        """
        return inspect.signature(lambda: None)

    def getMethods(self) -> list:
        """Implement the ``getMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicMethods(self) -> list:
        """Implement the ``getPublicMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicSyncMethods(self) -> list:
        """Implement the ``getPublicSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicAsyncMethods(self) -> list:
        """Implement the ``getPublicAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedMethods(self) -> list:
        """Implement the ``getProtectedMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedSyncMethods(self) -> list:
        """Implement the ``getProtectedSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedAsyncMethods(self) -> list:
        """Implement the ``getProtectedAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateMethods(self) -> list:
        """Implement the ``getPrivateMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateSyncMethods(self) -> list:
        """Implement the ``getPrivateSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateAsyncMethods(self) -> list:
        """Implement the ``getPrivateAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicClassMethods(self) -> list:
        """Implement the ``getPublicClassMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicClassSyncMethods(self) -> list:
        """Implement the ``getPublicClassSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicClassAsyncMethods(self) -> list:
        """Implement the ``getPublicClassAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedClassMethods(self) -> list:
        """Implement the ``getProtectedClassMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedClassSyncMethods(self) -> list:
        """Implement the ``getProtectedClassSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedClassAsyncMethods(self) -> list:
        """Implement the ``getProtectedClassAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateClassMethods(self) -> list:
        """Implement the ``getPrivateClassMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateClassSyncMethods(self) -> list:
        """Implement the ``getPrivateClassSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateClassAsyncMethods(self) -> list:
        """Implement the ``getPrivateClassAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicStaticMethods(self) -> list:
        """Implement the ``getPublicStaticMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicStaticSyncMethods(self) -> list:
        """Implement the ``getPublicStaticSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicStaticAsyncMethods(self) -> list:
        """Implement the ``getPublicStaticAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedStaticMethods(self) -> list:
        """Implement the ``getProtectedStaticMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedStaticSyncMethods(self) -> list:
        """Implement the ``getProtectedStaticSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedStaticAsyncMethods(self) -> list:
        """Implement the ``getProtectedStaticAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateStaticMethods(self) -> list:
        """Implement the ``getPrivateStaticMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateStaticSyncMethods(self) -> list:
        """Implement the ``getPrivateStaticSyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateStaticAsyncMethods(self) -> list:
        """Implement the ``getPrivateStaticAsyncMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getDunderMethods(self) -> list:
        """Implement the ``getDunderMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getMagicMethods(self) -> list:
        """Implement the ``getMagicMethods`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProperties(self) -> list:
        """Implement the ``getProperties`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPublicProperties(self) -> list:
        """Implement the ``getPublicProperties`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProtectedProperties(self) -> list:
        """Implement the ``getProtectedProperties`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getPrivateProperties(self) -> list:
        """Implement the ``getPrivateProperties`` contract stub.

        Returns
        -------
        list
            Value produced by the helper.
        """
        return []

    def getProperty(self, _name: str) -> object:
        """Implement the ``getProperty`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return None

    def getPropertySignature(self, _name: str) -> inspect.Signature:
        """Implement the ``getPropertySignature`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.

        Returns
        -------
        inspect.Signature
            Value produced by the helper.
        """
        return inspect.signature(lambda: None)

    def getPropertyDocstring(self, _name: str) -> str | None:
        """Implement the ``getPropertyDocstring`` contract stub.

        Parameters
        ----------
        _name : str
            Value supplied for ``_name``.

        Returns
        -------
        str | None
            Value produced by the helper.
        """
        return None

    def getConstructorSignature(self) -> inspect.Signature:
        """Implement the ``getConstructorSignature`` contract stub.

        Returns
        -------
        inspect.Signature
            Value produced by the helper.
        """
        return inspect.signature(lambda: None)

    def constructorSignature(self) -> Signature:
        """Implement the ``constructorSignature`` contract stub.

        Returns
        -------
        Signature
            Value produced by the helper.
        """
        return None  # type: ignore[return-value]
  # type: ignore[return-value]

    def methodSignature(self, _method_name: str) -> Signature:
        """Implement the ``methodSignature`` contract stub.

        Parameters
        ----------
        _method_name : str
            Value supplied for ``_method_name``.

        Returns
        -------
        Signature
            Value produced by the helper.
        """
        return None  # type: ignore[return-value]
  # type: ignore[return-value]

    def clearCache(self) -> None:
        """Implement the ``clearCache`` contract stub.

        Returns
        -------
        None
            Completes the operation described above.
        """

# ---------------------------------------------------------------------------
# Contract structure tests
# ---------------------------------------------------------------------------

class TestIReflectionConcreteIsABC(TestCase):
    """
    Verify that IReflectionConcrete is a proper abstract base class.

    Methods
    -------
    testIsAbstractBaseClass :
        IReflectionConcrete must inherit from ABC.
    testCannotInstantiateDirectly :
        Direct instantiation must raise TypeError.
    testConcreteSubclassInstantiates :
        A fully-implemented subclass must instantiate without errors.
    """

    def testIsAbstractBaseClass(self) -> None:
        """
        Assert that IReflectionConcrete inherits from ABC.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertTrue(issubclass(IReflectionConcrete, ABC))

    def testCannotInstantiateDirectly(self) -> None:
        """
        Assert that instantiating IReflectionConcrete directly raises TypeError.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        with self.assertRaises(TypeError):
            IReflectionConcrete()  # type: ignore[abstract]

    def testConcreteSubclassInstantiates(self) -> None:
        """
        Assert that a fully-implemented subclass can be instantiated.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(_StubConcrete(), IReflectionConcrete)

class TestIReflectionConcreteAbstractMethods(TestCase):

    def _assertAbstract(self, name: str) -> None:
        """
        Assert that a method name is in IReflectionConcrete.__abstractmethods__.

        Parameters
        ----------
        name : str
            Name of the method to check.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIn(name, IReflectionConcrete.__abstractmethods__)

    def testGetClassIsAbstract(self) -> None:
        """
        Assert that getClass is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getClass")

    def testGetClassNameIsAbstract(self) -> None:
        """
        Assert that getClassName is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getClassName")

    def testGetModuleNameIsAbstract(self) -> None:
        """
        Assert that getModuleName is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getModuleName")

    def testGetModuleWithClassNameIsAbstract(self) -> None:
        """
        Assert that getModuleWithClassName is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getModuleWithClassName")

    def testGetDocstringIsAbstract(self) -> None:
        """
        Assert that getDocstring is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getDocstring")

    def testGetBaseClassesIsAbstract(self) -> None:
        """
        Assert that getBaseClasses is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getBaseClasses")

    def testGetSourceCodeIsAbstract(self) -> None:
        """
        Assert that getSourceCode is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getSourceCode")

    def testGetFileIsAbstract(self) -> None:
        """
        Assert that getFile is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getFile")

    def testGetAnnotationsIsAbstract(self) -> None:
        """
        Assert that getAnnotations is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getAnnotations")

    def testHasAttributeIsAbstract(self) -> None:
        """
        Assert that hasAttribute is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("hasAttribute")

    def testGetAttributeIsAbstract(self) -> None:
        """
        Assert that getAttribute is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getAttribute")

    def testSetAttributeIsAbstract(self) -> None:
        """
        Assert that setAttribute is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("setAttribute")

    def testRemoveAttributeIsAbstract(self) -> None:
        """
        Assert that removeAttribute is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("removeAttribute")

    def testGetAttributesIsAbstract(self) -> None:
        """
        Assert that getAttributes is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getAttributes")

    def testGetPublicAttributesIsAbstract(self) -> None:
        """
        Assert that getPublicAttributes is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicAttributes")

    def testGetProtectedAttributesIsAbstract(self) -> None:
        """
        Assert that getProtectedAttributes is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedAttributes")

    def testGetPrivateAttributesIsAbstract(self) -> None:
        """
        Assert that getPrivateAttributes is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateAttributes")

    def testGetDunderAttributesIsAbstract(self) -> None:
        """
        Assert that getDunderAttributes is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getDunderAttributes")

    def testGetMagicAttributesIsAbstract(self) -> None:
        """
        Assert that getMagicAttributes is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getMagicAttributes")

    def testHasMethodIsAbstract(self) -> None:
        """
        Assert that hasMethod is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("hasMethod")

    def testSetMethodIsAbstract(self) -> None:
        """
        Assert that setMethod is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("setMethod")

    def testRemoveMethodIsAbstract(self) -> None:
        """
        Assert that removeMethod is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("removeMethod")

    def testGetMethodSignatureIsAbstract(self) -> None:
        """
        Assert that getMethodSignature is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getMethodSignature")

    def testGetMethodsIsAbstract(self) -> None:
        """
        Assert that getMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getMethods")

    def testGetPublicMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicMethods")

    def testGetPublicSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicSyncMethods")

    def testGetPublicAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicAsyncMethods")

    def testGetProtectedMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedMethods")

    def testGetProtectedSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedSyncMethods")

    def testGetProtectedAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedAsyncMethods")

    def testGetPrivateMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateMethods")

    def testGetPrivateSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateSyncMethods")

    def testGetPrivateAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateAsyncMethods")

    def testGetPublicClassMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicClassMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicClassMethods")

    def testGetPublicClassSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicClassSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicClassSyncMethods")

    def testGetPublicClassAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicClassAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicClassAsyncMethods")

    def testGetProtectedClassMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedClassMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedClassMethods")

    def testGetProtectedClassSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedClassSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedClassSyncMethods")

    def testGetProtectedClassAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedClassAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedClassAsyncMethods")

    def testGetPrivateClassMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateClassMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateClassMethods")

    def testGetPrivateClassSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateClassSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateClassSyncMethods")

    def testGetPrivateClassAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateClassAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateClassAsyncMethods")

    def testGetPublicStaticMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicStaticMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicStaticMethods")

    def testGetPublicStaticSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicStaticSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicStaticSyncMethods")

    def testGetPublicStaticAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPublicStaticAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicStaticAsyncMethods")

    def testGetProtectedStaticMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedStaticMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedStaticMethods")

    def testGetProtectedStaticSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedStaticSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedStaticSyncMethods")

    def testGetProtectedStaticAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getProtectedStaticAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedStaticAsyncMethods")

    def testGetPrivateStaticMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateStaticMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateStaticMethods")

    def testGetPrivateStaticSyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateStaticSyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateStaticSyncMethods")

    def testGetPrivateStaticAsyncMethodsIsAbstract(self) -> None:
        """
        Assert that getPrivateStaticAsyncMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateStaticAsyncMethods")

    def testGetDunderMethodsIsAbstract(self) -> None:
        """
        Assert that getDunderMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getDunderMethods")

    def testGetMagicMethodsIsAbstract(self) -> None:
        """
        Assert that getMagicMethods is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getMagicMethods")

    def testGetPropertiesIsAbstract(self) -> None:
        """
        Assert that getProperties is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProperties")

    def testGetPublicPropertiesIsAbstract(self) -> None:
        """
        Assert that getPublicProperties is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPublicProperties")

    def testGetProtectedPropertiesIsAbstract(self) -> None:
        """
        Assert that getProtectedProperties is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProtectedProperties")

    def testGetPrivatePropertiesIsAbstract(self) -> None:
        """
        Assert that getPrivateProperties is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPrivateProperties")

    def testGetPropertyIsAbstract(self) -> None:
        """
        Assert that getProperty is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getProperty")

    def testGetPropertySignatureIsAbstract(self) -> None:
        """
        Assert that getPropertySignature is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPropertySignature")

    def testGetPropertyDocstringIsAbstract(self) -> None:
        """
        Assert that getPropertyDocstring is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getPropertyDocstring")

    def testGetConstructorSignatureIsAbstract(self) -> None:
        """
        Assert that getConstructorSignature is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("getConstructorSignature")

    def testConstructorSignatureIsAbstract(self) -> None:
        """
        Assert that constructorSignature is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("constructorSignature")

    def testMethodSignatureIsAbstract(self) -> None:
        """
        Assert that methodSignature is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("methodSignature")

    def testClearCacheIsAbstract(self) -> None:
        """
        Assert that clearCache is an abstract method.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self._assertAbstract("clearCache")

class TestIReflectionConcretePartialImplementation(TestCase):

    def testMissingClearCacheRaisesTypeError(self) -> None:
        """
        Assert that a subclass implementing only one method cannot be instantiated.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """

        class _OnlyGetClass(IReflectionConcrete):
            """Purposely incomplete subclass."""

            def getClass(self) -> type:
                """Implement the ``getClass`` contract stub.

                Returns
                -------
                type
                    Value produced by the helper.
                """
                return object
            # all other abstract methods intentionally omitted

        with self.assertRaises(TypeError):
            _OnlyGetClass()

class TestIReflectionConcreteStubReturnTypes(TestCase):

    def setUp(self) -> None:
        """
        Initialise a shared stub instance for return-type tests.

        Returns
        -------
        None
            Sets self.stub to a new _StubConcrete instance.
        """
        self.stub = _StubConcrete()

    def testGetClassReturnsType(self) -> None:
        """
        Assert that getClass returns a type object.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getClass(), type)

    def testGetClassNameReturnsStr(self) -> None:
        """
        Assert that getClassName returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getClassName(), str)

    def testGetModuleNameReturnsStr(self) -> None:
        """
        Assert that getModuleName returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getModuleName(), str)

    def testGetModuleWithClassNameReturnsStr(self) -> None:
        """
        Assert that getModuleWithClassName returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getModuleWithClassName(), str)

    def testGetFileReturnsStr(self) -> None:
        """
        Assert that getFile returns a str.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getFile(), str)

    def testGetAnnotationsReturnsDict(self) -> None:
        """
        Assert that getAnnotations returns a dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getAnnotations(), dict)

    def testGetAttributesReturnsDict(self) -> None:
        """
        Assert that getAttributes returns a dict.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getAttributes(), dict)

    def testGetMethodsReturnsList(self) -> None:
        """
        Assert that getMethods returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getMethods(), list)

    def testGetPropertiesReturnsList(self) -> None:
        """
        Assert that getProperties returns a list.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(self.stub.getProperties(), list)

    def testGetConstructorSignatureReturnsInspectSignature(self) -> None:
        """
        Assert that getConstructorSignature returns an inspect.Signature.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsInstance(
            self.stub.getConstructorSignature(), inspect.Signature,
        )

    def testClearCacheReturnsNone(self) -> None:
        """
        Assert that clearCache returns None.

        Returns
        -------
        None
            Raises AssertionError on failure.
        """
        self.assertIsNone(self.stub.clearCache())
