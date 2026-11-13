"""Describe a database schema comment."""

import re
import unicodedata


class Comment:
    """Describe a database schema comment."""

    def __init__(self, text: str) -> None:
        """
        Initialize a Comment instance.

        Parameters
        ----------
        text : str
            The comment text content.

        Returns
        -------
        None
            No return value.
        """
        # Normaliza Unicode
        text = unicodedata.normalize("NFC", text)

        # Elimina caracteres de control ASCII
        text = re.sub(r"[\x00-\x1F\x7F]", " ", text)

        # Colapsa espacios consecutivos
        text = re.sub(r"\s+", " ", text)

        # Store the comment text.
        self.text = text.strip()
        """The comment text content."""
