"""Resolve the lang service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.localization.contracts.translator import ITranslator

class Lang(Facade):
    """Resolve the lang service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the translator.

        Returns
        -------
        type
            :class:`orionis.localization.contracts.ITranslator`.
        """
        return ITranslator
