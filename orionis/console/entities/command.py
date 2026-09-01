from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from orionis.support.entities.base import BaseEntity

if TYPE_CHECKING:
    import argparse
    from orionis.console.args.argument import Argument

@dataclass(kw_only=True)
class Command(BaseEntity):
    """
    Represent a console command and its metadata.

    Parameters
    ----------
    obj : type
        Type or class associated with the command.
    method : str, optional
        Method name to invoke on the object. Defaults to 'handle'.
    timestamps : bool, optional
        Enable timestamps for this command. Defaults to True.
    signature : str
        Command usage signature.
    description : str
        Brief description of the command.
    args : list of Argument or argparse.ArgumentParser or None, optional
        Declarative argument list while the command is being defined, and the
        parser built from it once the loader materializes the command.
        Defaults to None.

    Returns
    -------
    Command
        Instance containing metadata and configuration for a console command.
    """

    # The type or class associated with the command
    obj: type

    # The method name to be invoked on the object (default: 'handle')
    method: str = "handle"

    # Indicates if timestamps are enabled for this command (default: True)
    timestamps: bool = True

    # The command usage signature
    signature: str

    # Description of the command's purpose
    description: str

    # Declarative arguments (fluent builder) or the built parser (loader)
    args: list[Argument] | argparse.ArgumentParser | None = None
