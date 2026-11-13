# ruff: noqa: ARG002
# HTMLParser callbacks retain the required attrs parameter.
"""Strip markup using the standard HTML parser while preserving allowed tags."""

from html.parser import HTMLParser


class _TagStripper(HTMLParser):
    """Collect text and explicitly allowed markup without sanitizing attributes."""

    def __init__(self, allowed: frozenset[str]) -> None:
        """
        Initialize the parser with permitted lower-case tag names.

        Parameters
        ----------
        allowed : frozenset[str]
            Tags whose original opening markup is preserved.

        Returns
        -------
        None
            No return value.
        """
        super().__init__(convert_charrefs=bool(allowed))
        self.allowed = allowed
        """Tag names retained in the output."""
        self.parts: list[str] = []
        """Text and markup fragments in encounter order."""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """
        Retain an allowed opening tag exactly as supplied.

        Parameters
        ----------
        tag : str
            Normalized tag name supplied by HTMLParser.
        attrs : list[tuple[str, str or None]]
            Parsed attributes, retained through the original tag text.

        Returns
        -------
        None
            No return value.
        """
        if tag in self.allowed:
            self.parts.append(self.get_starttag_text())

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """
        Retain an allowed self-closing tag without adding an end tag.

        Parameters
        ----------
        tag : str
            Normalized tag name supplied by HTMLParser.
        attrs : list[tuple[str, str or None]]
            Parsed attributes supplied by HTMLParser.

        Returns
        -------
        None
            No return value.
        """
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        """
        Retain the closing tag of an allowed element.

        Parameters
        ----------
        tag : str
            Normalized tag name supplied by HTMLParser.

        Returns
        -------
        None
            No return value.
        """
        if tag in self.allowed:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        """
        Retain text content, including content within removed elements.

        Parameters
        ----------
        data : str
            Text supplied by HTMLParser.

        Returns
        -------
        None
            No return value.
        """
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        """
        Preserve an entity when automatic entity conversion is disabled.

        Parameters
        ----------
        name : str
            Entity name without delimiters.

        Returns
        -------
        None
            No return value.
        """
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        """
        Preserve a numeric reference when entity conversion is disabled.

        Parameters
        ----------
        name : str
            Numeric reference without delimiters.

        Returns
        -------
        None
            No return value.
        """
        self.parts.append(f"&#{name};")
