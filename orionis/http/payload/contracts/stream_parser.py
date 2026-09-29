from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.payload.form_data import FormData

class IMultipartStreamParser(ABC):
    """
    Define the contract for parsing a multipart byte stream.

    Implementations consume an async byte stream bounded by a MIME
    boundary token and produce a ``FormData`` container of all
    parsed fields and uploaded files.
    """

    __slots__ = ()

    @abstractmethod
    async def parse(self) -> FormData:
        """
        Parse the multipart stream and return all form fields and files.

        Returns
        -------
        FormData
            Container holding all parsed field values and uploaded files.
        """
