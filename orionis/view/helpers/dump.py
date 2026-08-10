from __future__ import annotations
from typing import Any
from markupsafe import Markup
from orionis.console.output.var_dumper import VarDumper

# ruff: noqa: ANN401, S704

def _global_dd() -> Any:
    """
    Build the ``dd`` template global.

    Returns
    -------
    Any
        Callable dumping the given variables and returning safe HTML.
    """
    def dd(*args: Any) -> Markup:
        """
        Dump the given variables and return their HTML representation.

        Parameters
        ----------
        *args : Any
            Values to dump.

        Returns
        -------
        Markup
            Safe HTML markup with the dumped variables, exempt from the
            environment autoescaping.
        """
        dumper = VarDumper()
        dumper.values(*args)
        return Markup(dumper.toHtml(insert_line=True))

    return dd
