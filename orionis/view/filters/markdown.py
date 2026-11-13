# ruff: noqa: PLC0415, TC003
# Load Markdown only when used and expose callable types at runtime.

"""Provide view filters operations through ``_filter_markdown``."""

from __future__ import annotations
from collections.abc import Callable


def _filter_markdown() -> Callable[[object], str]:
    """
    Build the ``markdown`` template filter.

    Returns
    -------
    collections.abc.Callable[[object], str]
        Callable rendering a Markdown string to HTML.
    """

    def render_markdown(value: object) -> str:
        """
        Render a Markdown string to HTML.

        Parameters
        ----------
        value : object
            Value whose string representation contains Markdown.

        Returns
        -------
        str
            HTML-rendered string that remains subject to Jinja autoescaping.
        """
        import markdown as markdown_lib

        return markdown_lib.markdown(
            str(value),
            extensions=["extra", "codehilite", "toc"],
        )

    return render_markdown
