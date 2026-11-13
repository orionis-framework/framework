# ruff: noqa: PLC0415, TC001, TC003
# Preserve dynamic reflection, lazy concrete helpers, and runtime public hints.
"""Select reflection helpers for classes, instances, functions and modules."""

from __future__ import annotations
import abc
import inspect
import typing

from collections.abc import Callable
from orionis.introspection.abstract.contracts.reflection import (
    IReflectionAbstract,
)
from orionis.introspection.callables.contracts.reflection import (
    IReflectionCallable,
)
from orionis.introspection.concretes.contracts.reflection import (
    IReflectionConcrete,
)
from orionis.introspection.instances.contracts.reflection import (
    IReflectionInstance,
)
from orionis.introspection.modules.contracts.reflection import (
    IReflectionModule,
)


class Reflection:
    """Select reflection helpers for classes, instances, functions and modules."""

    @staticmethod
    def instance(instance: object) -> IReflectionInstance:
        """
        Create a ReflectionInstance for an object instance.

        Parameters
        ----------
        instance : object
            Object instance to reflect.

        Returns
        -------
        orionis.introspection.instances.contracts.reflection.IReflectionInstance
            Reflection object for the provided instance.
        """
        from orionis.introspection.instances.reflection import (
            ReflectionInstance,
        )

        return ReflectionInstance(instance)

    @staticmethod
    def abstract(abstract: type) -> IReflectionAbstract:
        """
        Create a ReflectionAbstract for an abstract class.

        Parameters
        ----------
        abstract : type
            The abstract class to reflect.

        Returns
        -------
        orionis.introspection.abstract.contracts.reflection.IReflectionAbstract
            Reflection object for the provided abstract class.
        """
        from orionis.introspection.abstract.reflection import (
            ReflectionAbstract,
        )

        return ReflectionAbstract(abstract)

    @staticmethod
    def concrete(concrete: type) -> IReflectionConcrete:
        """
        Create a ReflectionConcrete for a concrete class.

        Parameters
        ----------
        concrete : type
            The concrete class to reflect.

        Returns
        -------
        orionis.introspection.concretes.contracts.reflection.IReflectionConcrete
            Reflection object for the provided concrete class.
        """
        from orionis.introspection.concretes.reflection import (
            ReflectionConcrete,
        )

        return ReflectionConcrete(concrete)

    @staticmethod
    def module(module: str) -> IReflectionModule:
        """
        Create a reflection object for a module.

        Parameters
        ----------
        module : str
            Name of the module to reflect.

        Returns
        -------
        orionis.introspection.modules.contracts.reflection.IReflectionModule
            Reflection object for the specified module.
        """
        from orionis.introspection.modules.reflection import ReflectionModule

        return ReflectionModule(module)

    @staticmethod
    def callable(fn: Callable) -> IReflectionCallable:
        """
        Create a ReflectionCallable for a callable object.

        Parameters
        ----------
        fn : collections.abc.Callable
            The function or method to wrap.

        Returns
        -------
        orionis.introspection.callables.contracts.reflection.IReflectionCallable
            Reflection object encapsulating the provided callable.
        """
        from orionis.introspection.callables.reflection import (
            ReflectionCallable,
        )

        return ReflectionCallable(fn)

    @staticmethod
    def isAbstract(obj: object) -> bool:
        """
        Determine if the object is an abstract base class.

        Parameters
        ----------
        obj : object
            Object to check for abstractness.

        Returns
        -------
        bool
            True if the object is an abstract base class, False otherwise.
        """
        # Use inspect to check for abstract base class
        return inspect.isabstract(obj)

    @staticmethod
    def isConcreteClass(obj: object) -> bool:
        """
        Determine if the object is a concrete user-defined class.

        Parameters
        ----------
        obj : object
            Object to check for concreteness.

        Returns
        -------
        bool
            True if the object is a concrete class; False otherwise.
        """
        # Check if the object is a class type.
        result = True

        if (
            not isinstance(obj, type)
            or obj.__module__ == "builtins"
            or Reflection.isAbstract(obj)
            or Reflection.isGeneric(obj)
            or Reflection.isProtocol(obj)
            or Reflection.isTypingConstruct(obj)
            or abc.ABC in obj.__bases__
            or not hasattr(obj, "__init__")
        ):
            result = False

        return result

    @staticmethod
    def isAsyncGen(obj: object) -> bool:
        """
        Determine if the object is an asynchronous generator.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is an asynchronous generator, False otherwise.
        """
        # Use inspect to check for asynchronous generator
        return inspect.isasyncgen(obj)

    @staticmethod
    def isAsyncGenFunction(obj: object) -> bool:
        """
        Determine if the object is an asynchronous generator function.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is an asynchronous generator function,
            False otherwise.
        """
        # Use inspect to check for async generator function
        return inspect.isasyncgenfunction(obj)

    @staticmethod
    def isAwaitable(obj: object) -> bool:
        """
        Determine if the object can be awaited.

        Parameters
        ----------
        obj : object
            Object to check for awaitability.

        Returns
        -------
        bool
            True if the object is awaitable, otherwise False.
        """
        # Use inspect to check for awaitable objects
        return inspect.isawaitable(obj)

    @staticmethod
    def isBuiltIn(obj: object) -> bool:
        """
        Determine if the object is a built-in function or method.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a built-in function or method, False otherwise.
        """
        # Use inspect to check for built-in functions or methods
        return inspect.isbuiltin(obj)

    @staticmethod
    def isClass(obj: object) -> bool:
        """
        Determine if the object is a class.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a class, otherwise False.
        """
        return inspect.isclass(obj)

    @staticmethod
    def isCode(obj: object) -> bool:
        """
        Determine if the object is a code object.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a code object, otherwise False.
        """
        return inspect.iscode(obj)

    @staticmethod
    def isCoroutine(obj: object) -> bool:
        """
        Determine if the object is a coroutine.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a coroutine, otherwise False.
        """
        return inspect.iscoroutine(obj)

    @staticmethod
    def isCoroutineFunction(obj: object) -> bool:
        """
        Determine if the object is a coroutine function.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a coroutine function, otherwise False.
        """
        return inspect.iscoroutinefunction(obj)

    @staticmethod
    def isDataDescriptor(obj: object) -> bool:
        """
        Determine if the object is a data descriptor.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a data descriptor, otherwise False.
        """
        return inspect.isdatadescriptor(obj)

    @staticmethod
    def isFrame(obj: object) -> bool:
        """
        Determine if the object is a frame object.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a frame object, otherwise False.
        """
        return inspect.isframe(obj)

    @staticmethod
    def isFunction(obj: object) -> bool:
        """
        Determine if the object is a Python function.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a function, otherwise False.
        """
        return inspect.isfunction(obj)

    @staticmethod
    def isGenerator(obj: object) -> bool:
        """
        Determine if the object is a generator.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a generator, otherwise False.
        """
        return inspect.isgenerator(obj)

    @staticmethod
    def isGeneratorFunction(obj: object) -> bool:
        """
        Determine if the object is a generator function.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a generator function, otherwise False.
        """
        return inspect.isgeneratorfunction(obj)

    @staticmethod
    def isGetSetDescriptor(obj: object) -> bool:
        """
        Determine if the object is a getset descriptor.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a getset descriptor, otherwise False.
        """
        return inspect.isgetsetdescriptor(obj)

    @staticmethod
    def isMemberDescriptor(obj: object) -> bool:
        """
        Determine if the object is a member descriptor.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a member descriptor, otherwise False.
        """
        return inspect.ismemberdescriptor(obj)

    @staticmethod
    def isMethod(obj: object) -> bool:
        """
        Determine if the object is a method.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a method, otherwise False.
        """
        return inspect.ismethod(obj)

    @staticmethod
    def isMethodDescriptor(obj: object) -> bool:
        """
        Determine if the object is a method descriptor.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a method descriptor, otherwise False.
        """
        return inspect.ismethoddescriptor(obj)

    @staticmethod
    def isModule(obj: object) -> bool:
        """
        Determine if the object is a module.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a module, otherwise False.
        """
        return inspect.ismodule(obj)

    @staticmethod
    def isRoutine(obj: object) -> bool:
        """
        Determine if the object is a user-defined or built-in function or method.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a routine, otherwise False.
        """
        return inspect.isroutine(obj)

    @staticmethod
    def isTraceback(obj: object) -> bool:
        """
        Determine if the object is a traceback object.

        Parameters
        ----------
        obj : object
            Object to check.

        Returns
        -------
        bool
            True if the object is a traceback object, otherwise False.
        """
        return inspect.istraceback(obj)

    @staticmethod
    def isGeneric(obj: object) -> bool:
        """
        Determine if the provided type is a generic type.

        Parameters
        ----------
        obj : object
            The type to check.

        Returns
        -------
        bool
            True if the type is generic, otherwise False.
        """
        # Parameterized generics expose an origin either through the public
        # helper or, for bare typing constructs, the __origin__ attribute.
        if typing.get_origin(obj) is not None or hasattr(obj, "__origin__"):
            return True

        # Type variables are generic placeholders as well.
        return isinstance(obj, typing.TypeVar)

    @staticmethod
    def isProtocol(obj: object) -> bool:
        """
        Determine if the object is a subclass of ``typing.Protocol``.

        Parameters
        ----------
        obj : object
            Object or type to evaluate.

        Returns
        -------
        bool
            True if ``obj`` is a class that is a subclass of ``typing.Protocol``
            (but not ``Protocol`` itself), otherwise False.
        """
        # Return the condition directly
        return (
            isinstance(obj, type)
            and issubclass(obj, typing.Protocol)
            and obj is not typing.Protocol
        )

    @staticmethod
    def isInstance(obj: object) -> bool:
        """
        Determine if the object is an instance of a user-defined class.

        Parameters
        ----------
        obj : object
            Object to evaluate.

        Returns
        -------
        bool
            True if the object is an instance of a user-defined class,
            False otherwise.
        """
        # Ensure obj is not a class type
        if not (isinstance(obj, object) and not isinstance(obj, type)):
            return False

        # Exclude instances of built-in or abstract base classes
        module: str = type(obj).__module__
        return module not in {"builtins", "abc"}

    @staticmethod
    def isTypingConstruct(obj: object) -> bool:
        """
        Determine if the object is a construct from the ``typing`` module.

        Parameters
        ----------
        obj : object
            Object to evaluate.

        Returns
        -------
        bool
            True if the object is a recognized typing construct from the ``typing``
            module, otherwise False.
        """
        return not inspect.isfunction(obj) and (
            getattr(obj, "__module__", None) == "typing"
            or type(obj).__module__ == "typing"
        )
