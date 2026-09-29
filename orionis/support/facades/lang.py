from orionis.container.facades.facade import Facade
from orionis.localization.contracts.translator import ITranslator

class Lang(Facade):
    """
    Facade for the localization system.

    Proxies all calls to the bound :class:`ITranslator` singleton. The
    facade is only an entry point: every behavior lives in the
    translator resolved through it.

    Usage (facade pinned at boot)::

        Lang.get("Welcome")
        Lang.get("Hello :name", name="Carlos")
        Lang.choice("There is one apple|There are :count apples", 5)
        Lang.setLocale("es")
    """

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the translator.

        Returns
        -------
        type
            :class:`ITranslator`.
        """
        return ITranslator
