import os
import sys
from importlib import import_module
from pathlib import Path
from orionis.aio import Loop
from orionis.console.stdio import protocol_stdio

def main() -> int:
    """
    Boot the local application and run CLI commands in the current process.

    Load ``bootstrap.app`` from the working directory without requiring a
    Reactor script. Disable bytecode writes in this process and child
    interpreters, preserving command arguments, standard streams, and the
    application's command lifecycle.

    Returns
    -------
    int
        Exit code returned by the application's console handler.

    Notes
    -----
    Console-script imports happen before this function runs. To prevent their
    bytecode caches too, set ``PYTHONDONTWRITEBYTECODE=1`` before starting Python.
    """
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.path.insert(0, str(Path.cwd()))
    arguments = ["reactor", *sys.argv[1:]]

    with protocol_stdio(arguments):
        application = import_module("bootstrap.app").app
        return Loop.run(application.handleCommand(arguments))
