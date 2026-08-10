from __future__ import annotations
from typing import Any
import markdown as markdown_lib

# ruff: noqa: ANN401

def _filter_markdown() -> Any:
    """
    Build the ``markdown`` template filter.

    Returns
    -------
    Any
        Callable rendering a Markdown string to HTML.
    """
    def render_markdown(value: Any) -> str:
        """
        Render a Markdown string to HTML.

        Parameters
        ----------
        value : Any
            Markdown-formatted string to convert.

        Returns
        -------
        str
            HTML-rendered string.
        """
        return markdown_lib.markdown(
            str(value),
            extensions=["extra", "codehilite", "toc"],
        )

    return render_markdown
