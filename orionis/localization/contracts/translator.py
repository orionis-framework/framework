from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.localization.types import MissingKeyHandler

class ITranslator(ABC):
    """
    Define the contract for the translation service.

    The translator resolves lines for the active locale, falls back to
    the configured fallback locale, applies parameter
    replacement, and selects pluralized segments.
    """

    @abstractmethod
    def get(
        self,
        key: str,
        locale: str | None = None,
        **replace: object,
    ) -> str:
        """
        Retrieve the translation line registered under *key*.

        The lookup order is the requested locale first, then the
        fallback locale, and finally the key itself when no translation
        exists. Placeholders in the ``:name`` form are substituted with
        the values provided in *replace*.

        Parameters
        ----------
        key : str
            Translation key, either a literal source text or a
            dot-notated grouped key such as ``validation.required``.
        locale : str | None, optional
            Locale to translate into, or ``None`` for the active locale.
        **replace : object
            Placeholder values substituted into the resolved line.

        Returns
        -------
        str
            Translated line, or the key itself when missing.

        Raises
        ------
        InvalidLocaleException
            If an explicit locale is malformed.
        """

    @abstractmethod
    def has(
        self,
        key: str,
        locale: str | None = None,
        *,
        fallback: bool = True,
    ) -> bool:
        """
        Determine whether a translation exists for *key*.

        Parameters
        ----------
        key : str
            Translation key to check.
        locale : str | None, optional
            Locale to inspect, or ``None`` for the active locale.
        fallback : bool, optional
            Whether the fallback locale is also inspected.

        Returns
        -------
        bool
            True when a translation line is registered for the key.

        Raises
        ------
        InvalidLocaleException
            If an explicit locale is malformed.
        """

    @abstractmethod
    def choice(
        self,
        key: str,
        count: int,
        locale: str | None = None,
        **replace: object,
    ) -> str:
        """
        Retrieve a pluralized translation line based on *count*.

        Segments are separated by ``|`` and may declare explicit
        conditions such as ``{0}``, ``{1}`` or ranges ``[2,*]``. When no
        explicit condition matches, the first segment is used for a
        count of one and the second segment otherwise. The ``:count``
        placeholder is always available in the selected segment.

        Parameters
        ----------
        key : str
            Translation key containing the pluralized segments.
        count : int
            Quantity used to select the proper segment.
        locale : str | None, optional
            Locale to translate into, or ``None`` for the active locale.
        **replace : object
            Placeholder values substituted into the selected segment.

        Returns
        -------
        str
            Pluralized and interpolated translation line.

        Raises
        ------
        InvalidLocaleException
            If an explicit locale is malformed.
        """

    @abstractmethod
    def setLocale(self, locale: str) -> None:
        """
        Change the active locale at runtime.

        Parameters
        ----------
        locale : str
            Locale code to activate.

        Returns
        -------
        None

        Raises
        ------
        InvalidLocaleException
            If the locale is malformed.
        """

    @abstractmethod
    def getLocale(self) -> str:
        """
        Return the active locale.

        Returns
        -------
        str
            Locale code currently in use.
        """

    @abstractmethod
    def availableLocales(self) -> tuple[str, ...]:
        """
        Return every locale with at least one translation source.

        Returns
        -------
        tuple[str, ...]
            Sorted locale codes discovered in the language path.
        """

    @abstractmethod
    def reload(self, locale: str | None = None) -> None:
        """
        Discard cached translations so they are re-read from disk.

        Parameters
        ----------
        locale : str | None, optional
            Locale to reload, or ``None`` to reload every locale.

        Returns
        -------
        None

        Raises
        ------
        InvalidLocaleException
            If an explicit locale is malformed.
        """

    @abstractmethod
    def forget(self, locale: str) -> bool:
        """
        Discard the cached translations for a single locale.

        Parameters
        ----------
        locale : str
            Locale code whose cache entry must be removed.

        Returns
        -------
        bool
            True when an entry was removed, False otherwise.

        Raises
        ------
        InvalidLocaleException
            If the locale is malformed.
        """

    @abstractmethod
    def flush(self) -> None:
        """
        Discard every cached translation map.

        Returns
        -------
        None
        """

    @abstractmethod
    def missing(self, handler: MissingKeyHandler | None) -> None:
        """
        Register a handler invoked when a translation key is missing.

        The handler receives the key and the locale, and may return a
        replacement line. When it returns ``None`` the key itself is
        used as the translation.

        Parameters
        ----------
        handler : MissingKeyHandler | None
            Callable invoked on missing keys, or ``None`` to remove the
            current handler.

        Returns
        -------
        None
        """
