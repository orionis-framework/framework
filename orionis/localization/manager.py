from pathlib import Path
from orionis.foundation.contracts.application import IApplication
from orionis.localization.contracts.manager import ILocalizationManager
from orionis.localization.contracts.translator import ITranslator
from orionis.localization.loader import TranslationLoader
from orionis.localization.repository import TranslationRepository
from orionis.localization.translator import Translator

# ruff: noqa: TC001

class LocalizationManager(ILocalizationManager):
    """
    Wire the localization component from the application configuration.

    The manager reads the ``app.locale``, ``app.fallback_locale``, and
    ``app.language_path`` settings, builds the loader, the repository,
    and the translator, and caches the resulting translator so a single
    shared instance serves the whole application.

    Notes
    -----
    This module must not enable ``from __future__ import annotations``:
    the container resolves constructor dependencies from evaluated
    annotations, and stringized annotations cannot be injected.
    """

    __slots__ = ("_app", "_translator")

    def __init__(self, app: IApplication) -> None:
        """
        Initialize the manager with the application container.

        Parameters
        ----------
        app : IApplication
            Application container providing configuration and paths.

        Returns
        -------
        None
        """
        self._app = app
        self._translator: ITranslator | None = None

    def translator(self) -> ITranslator:
        """
        Return the shared translator instance, building it on demand.

        Returns
        -------
        ITranslator
            Translator configured from the application settings.

        Raises
        ------
        InvalidLocaleException
            If the configured locale or fallback locale is malformed.
        """
        if self._translator is None:
            self._translator = self.__buildTranslator()
        return self._translator

    def __buildTranslator(self) -> ITranslator:
        """
        Build the translator from the application configuration.

        Returns
        -------
        ITranslator
            Translator bound to a fresh loader and repository.

        Raises
        ------
        InvalidLocaleException
            If the configured locale or fallback locale is malformed.
        """
        # Read the localization settings from the app configuration.
        locale = str(self._app.config("app.locale") or "en")
        fallback = str(self._app.config("app.fallback_locale") or locale)
        raw_path = str(self._app.config("app.language_path") or "resources/lang/")

        # Resolve relative language paths against the application root.
        path = Path(raw_path)
        if not path.is_absolute():
            path = self._app.basePath / path

        # Wire the loader, the cache repository, and the translator.
        loader = TranslationLoader(path)
        repository = TranslationRepository(loader)
        return Translator(
            locale=locale,
            fallback=fallback,
            loader=loader,
            repository=repository,
        )
