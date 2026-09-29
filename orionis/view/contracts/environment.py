from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

class IViewEnvironment(ABC):
    """
    Contract for the view-environment wrapper.

    The implementation is the sole authority for configuring the underlying
    template engine's environment (loaders, caches, globals, filters, tests,
    and extensions).  No other class should access the engine environment
    directly.
    """

    # ruff: noqa: ANN401

    __slots__ = ()

    @abstractmethod
    def addGlobal(self, name: str, value: Any) -> None:
        """
        Register a global variable or callable available in all templates.

        Parameters
        ----------
        name : str
            Identifier used to reference the value inside templates.
        value : Any
            Value or callable to expose as a template global.

        Returns
        -------
        None
        """

    @abstractmethod
    def addFilter(self, name: str, callback: Callable) -> None:
        """
        Register a filter callable that templates can apply with ``|``.

        Parameters
        ----------
        name : str
            Filter name used inside template expressions (e.g. ``| slug``).
        callback : Callable
            Function applied to the piped value.  The first argument receives
            the value being filtered.

        Returns
        -------
        None
        """

    @abstractmethod
    def addTest(self, name: str, callback: Callable) -> None:
        """
        Register a test callable used in Jinja2 ``is`` expressions.

        Parameters
        ----------
        name : str
            Test name used in template expressions (e.g. ``is odd``).
        callback : Callable
            Function that receives the tested value and returns a bool.

        Returns
        -------
        None
        """

    @abstractmethod
    def addExtension(self, extension: Any) -> None:
        """
        Register a Jinja2 extension class with the environment.

        Parameters
        ----------
        extension : Any
            A Jinja2 :class:`Extension` subclass or its dotted import path.

        Returns
        -------
        None

        Raises
        ------
        ViewException
            When the extension cannot be registered.
        """

    @abstractmethod
    def getJinjaEnvironment(self) -> Any:
        """
        Return the underlying Jinja2 :class:`Environment` instance.

        Access is intentionally restricted to this method so that all
        configuration changes flow through the typed helpers above.

        Returns
        -------
        jinja2.Environment
            The configured Jinja2 environment.
        """
