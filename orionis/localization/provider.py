from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.localization.contracts.manager import ILocalizationManager
from orionis.localization.contracts.translator import ITranslator
from orionis.localization.manager import LocalizationManager
from orionis.support.facades.lang import Lang as LangFacade

class LocalizationProvider(ServiceProvider):
    """
    Service provider for the Orionis localization system.

    Registration phase
    ------------------
    Binds :class:`ILocalizationManager` to :class:`LocalizationManager`
    as a singleton.

    Boot phase
    ----------
    Builds the shared translator from the application configuration,
    binds it under :class:`ITranslator`, and pins the :class:`Lang`
    facade so attribute access is direct without container resolution
    overhead on every call.
    """

    def register(self) -> None:
        """
        Bind ILocalizationManager to LocalizationManager as a singleton.

        Returns
        -------
        None
        """
        self.app.singleton(ILocalizationManager, LocalizationManager)

    async def boot(self) -> None:
        """
        Bind the shared translator and pin the Lang facade.

        Returns
        -------
        None
        """
        # Build the translator once from the application configuration.
        manager: ILocalizationManager = await self.app.make(ILocalizationManager)
        self.app.instance(ITranslator, manager.translator())

        # Pin the facade for direct attribute access without DI overhead.
        await LangFacade.pin()
