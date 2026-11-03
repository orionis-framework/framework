"""Define the contract for a media-type-to-parser registry."""

from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Callable

# Special type alias for synchronous body parsers
BodyParser = Callable[[bytes], object]
"""Special type alias for synchronous body parsers."""

class IMediaTypeRegistry(ABC):
    """
    Define the contract for a media-type-to-parser registry.

    Implementations map lowercased media-type strings to synchronous
    ``BodyParser`` callables and support non-destructive extension.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    # Register or overwrite a parser for the specified media type.
    @abstractmethod
    def register(self, media_type: str, parser: BodyParser) -> None:
        """
        Add or replace the parser for *media_type* in place.

        Parameters
        ----------
        media_type : str
            Case-insensitive media-type string,
            e.g. ``"application/json"``.
        parser : orionis.http.payload.contracts.media_types.BodyParser
            Synchronous callable ``(bytes) -> object``.

        Returns
        -------
        None
            Add or replace the parser for *media_type* in place.
        """

    # Retrieve the parser associated with the given media type.
    @abstractmethod
    def get(self, media_type: str) -> BodyParser | None:
        """
        Return the parser registered for *media_type*, or ``None``.

        Parameters
        ----------
        media_type : str
            Case-insensitive media-type string.

        Returns
        -------
        orionis.http.payload.contracts.media_types.BodyParser | None
            The registered callable, or ``None`` if not found.
        """

    # Return a new registry with merged parsers, leaving self unchanged.
    @abstractmethod
    def extend(self, parsers: dict[str, BodyParser]) -> IMediaTypeRegistry:
        """
        Return a new registry that merges *parsers* over a copy of self.

        Parameters
        ----------
        parsers : dict[str, orionis.http.payload.contracts.media_types.BodyParser]
            Additional or replacement media-type-to-parser entries.

        Returns
        -------
        orionis.http.payload.contracts.media_types.IMediaTypeRegistry
            New registry containing all entries from self plus *parsers*.
        """
