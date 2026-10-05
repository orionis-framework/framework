from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.mcp.server.primitives import Tool

@dataclass(frozen=True, slots=True, init=False)
class ToolCatalog:
    """Hide catalog tools behind bounded search_tools and execute_tools tools."""

    tools: tuple[type[Tool], ...]
    search_name: str
    execute_name: str

    def __init__(
        self,
        *tools: type[Tool],
        search_name: str = "search_tools",
        execute_name: str = "execute_tools",
    ) -> None:
        """
        Store definitions without resolving instances or inspecting handlers.

        Parameters
        ----------
        search_name : str
            Value supplied for ``search_name``.
        execute_name : str
            Value supplied for ``execute_name``.
        *tools : type[Tool]
            Value supplied for ``*tools``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        object.__setattr__(self, "tools", tools)
        object.__setattr__(self, "search_name", search_name)
        object.__setattr__(self, "execute_name", execute_name)
