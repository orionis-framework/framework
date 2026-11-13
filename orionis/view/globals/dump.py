# ruff: noqa: ANN401, S704, TC003
# Keep public callback and application annotations resolvable at runtime.
# Preserve heterogeneous template payload values.
# VarDumper produces escaped HTML that must retain its generated markup.
"""Provide view globals operations through ``_global_dump``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from markupsafe import Markup

from orionis.console.output.var_dumper import VarDumper


def _global_dump() -> Callable[..., Markup]:
    """
    Build the ``dump`` template global.

    Returns
    -------
    collections.abc.Callable
        Callable dumping the given variables and returning safe HTML.
    """

    def dump(*args: Any) -> Markup:
        """
        Dump the given variables and return their HTML representation.

        Parameters
        ----------
        *args : typing.Any
            Values to dump.

        Returns
        -------
        ``markupsafe.Markup``
            Safe HTML markup with the dumped variables, exempt from the
            environment autoescaping.
        """
        dumper = VarDumper()
        dumper.values(*args)
        return Markup(dumper.toHtml(insert_line=True))

    return dump
