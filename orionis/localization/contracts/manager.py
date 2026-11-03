"""Define the contract for the localization manager."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.localization.contracts.translator import ITranslator

class ILocalizationManager(ABC):
    """
    Define the contract for the localization manager.

    The manager wires the loader, the repository, and the translator
    from the application configuration, exposing a single shared
    translator instance.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def translator(self) -> ITranslator:
        """
        Return the shared translator instance, building it on demand.

        Returns
        -------
        orionis.localization.contracts.ITranslator
            Translator configured from the application settings.
        """
