from orionis.container.facades.facade import Facade
from orionis.localization.contracts.translator import ITranslator

class Lang(Facade):

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
