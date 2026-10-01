import sys
import tomllib
from asyncio import CancelledError, create_subprocess_exec, to_thread
from asyncio.subprocess import DEVNULL, PIPE, STDOUT
from contextlib import suppress
from shutil import which
from typing import TYPE_CHECKING, ClassVar
from rich import box
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.enums.actions import ArgumentAction
from orionis.foundation.contracts.application import IApplication

if TYPE_CHECKING:
    from pathlib import Path

_ACCENT_STYLE = "bold cyan"
_ERROR_STYLE = "bold red"
_WARNING_STYLE = "yellow"

class InstallCommand(BaseCommand):
    """Install dependencies declared by the application's project manifest."""

    # ruff: noqa: TC001

    __slots__ = ("_console",)

    timestamps: bool = False
    signature: str = "install"
    description: str = "Install optional dependencies and dependency groups."
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="options",
            nargs="*",
            default=[],
            type_=str,
            help="Names or numbers to install; use extra:NAME or group:NAME.",
        ),
        Argument(
            name_or_flags="--list",
            action=ArgumentAction.STORE_TRUE,
            default=False,
            help="List installation options without installing packages.",
        ),
        Argument(
            name_or_flags=("--yes", "-y"),
            action=ArgumentAction.STORE_TRUE,
            default=False,
            help="Install the selected options without asking for confirmation.",
        ),
    ]

    def __init__(self) -> None:
        """
        Initialize the command arguments and Rich output.

        Returns
        -------
        None
            Initialize the console used for the installation interface.
        """
        super().__init__()
        self._console = RichConsole()

    async def handle(self, app: IApplication) -> int:
        """
        List and install dependencies in the interpreter running Reactor.

        Parameters
        ----------
        app : IApplication
            Application providing the project root.

        Returns
        -------
        int
            Zero on success or a declined selection, 130 on interruption,
            or a nonzero status when validation or installation fails.
        """
        project_path = app.basePath / "pyproject.toml"
        try:
            options = await to_thread(self.__loadOptions, project_path)
            self.__renderOptions(project_path, options)
            if self.getArgument("list", default=False) or not options:
                return 0

            selected = await to_thread(self.__selectOptions, options)
            if not selected:
                return 0
            return await self.__installSelection(project_path.parent, options, selected)
        except (CancelledError, EOFError, KeyboardInterrupt):
            self._console.print(Text("Installation interrupted.", _WARNING_STYLE))
            return 130
        except (OSError, TypeError, ValueError) as error:
            self._console.print(Text(str(error), style=_ERROR_STYLE))
            return 1

    def __loadOptions(self, project_path: Path) -> dict[str, tuple[str, ...]]:
        """
        Read extras and expand dependency groups from a TOML manifest.

        Parameters
        ----------
        project_path : Path
            Application manifest to read.

        Returns
        -------
        dict[str, tuple[str, ...]]
            Namespaced options and their deduplicated package requirements.

        Raises
        ------
        OSError
            If the manifest cannot be read.
        TypeError
            If a dependency section has an invalid TOML type.
        ValueError
            If TOML, dependency values or group references are invalid.
        """
        manifest = tomllib.loads(project_path.read_text(encoding="utf-8"))
        project = self.__dependencyTable(manifest.get("project", {}), "project")
        extras = self.__dependencyTable(
            project.get("optional-dependencies", {}),
            "project.optional-dependencies",
        )
        groups = self.__dependencyTable(
            manifest.get("dependency-groups", {}), "dependency-groups",
        )
        options = {
            f"extra:{name}": self.__requirements(entries, f"extra:{name}")
            for name, entries in extras.items()
        }
        options.update({
            f"group:{name}": self.__resolveGroup(name, groups, ())
            for name in groups
        })
        return options

    @staticmethod
    def __dependencyTable(value: object, origin: str) -> dict[str, object]:
        """
        Validate a manifest table containing dependency declarations.

        Parameters
        ----------
        value : object
            Parsed TOML value expected to be a table.
        origin : str
            Manifest section used in error messages.

        Returns
        -------
        dict[str, object]
            Validated dependency table.

        Raises
        ------
        TypeError
            If the section is not a TOML table.
        """
        if not isinstance(value, dict):
            error_msg = f"'{origin}' must be a TOML table."
            raise TypeError(error_msg)
        return value

    @staticmethod
    def __requirements(entries: object, origin: str) -> tuple[str, ...]:
        """
        Validate and deduplicate a list of package requirements.

        Parameters
        ----------
        entries : object
            Parsed dependency list.
        origin : str
            Option used in error messages.

        Returns
        -------
        tuple[str, ...]
            Nonempty requirement strings in declaration order.

        Raises
        ------
        ValueError
            If the declaration is not a list of nonempty strings.
        """
        if not isinstance(entries, list) or any(
            not isinstance(entry, str) or not entry.strip() for entry in entries
        ):
            error_msg = f"'{origin}' must contain a list of package requirements."
            raise ValueError(error_msg)
        return tuple(dict.fromkeys(entry.strip() for entry in entries))

    def __resolveGroup(
        self,
        name: str,
        groups: dict[str, object],
        chain: tuple[str, ...],
    ) -> tuple[str, ...]:
        """
        Expand included dependency groups and reject recursive references.

        Parameters
        ----------
        name : str
            Dependency group to expand.
        groups : dict[str, object]
            All dependency groups declared by the manifest.
        chain : tuple[str, ...]
            Groups already visited in this expansion.

        Returns
        -------
        tuple[str, ...]
            Deduplicated requirements including referenced groups.

        Raises
        ------
        TypeError
            If the group does not declare a list of dependencies.
        ValueError
            If a group is missing, cyclic or contains an invalid declaration.
        """
        if name in chain:
            error_msg = f"Cyclic dependency group reference: {' -> '.join(chain)}"
            raise ValueError(error_msg)
        if name not in groups:
            error_msg = f"Included dependency group '{name}' does not exist."
            raise ValueError(error_msg)

        entries = groups[name]
        if not isinstance(entries, list):
            error_msg = f"'group:{name}' must contain a list of dependencies."
            raise TypeError(error_msg)

        requirements: list[str] = []
        for entry in entries:
            if isinstance(entry, dict):
                included = entry.get("include-group")
                if set(entry) != {"include-group"} or not isinstance(included, str):
                    error_msg = f"'group:{name}' has an invalid group inclusion."
                    raise ValueError(error_msg)
                requirements.extend(
                    self.__resolveGroup(included, groups, (*chain, name)),
                )
            else:
                requirements.extend(self.__requirements([entry], f"group:{name}"))
        return tuple(dict.fromkeys(requirements))

    def __renderOptions(
        self,
        project_path: Path,
        options: dict[str, tuple[str, ...]],
    ) -> None:
        """
        Render a compact catalog with one row per installation option.

        Parameters
        ----------
        project_path : Path
            Manifest supplying the catalog.
        options : dict[str, tuple[str, ...]]
            Namespaced installation options.

        Returns
        -------
        None
            Print project metadata and a compact Rich dependency table.
        """
        header = Text.assemble(
            ("ORIONIS", "bold white"),
            ("  Dependency installer", _ACCENT_STYLE),
        )
        self._console.print(header)
        self._console.print(
            Text.assemble(("Manifest  ", "dim"), str(project_path)),
            overflow="ellipsis", no_wrap=True,
        )
        self._console.print(
            Text.assemble(("Python    ", "dim"), sys.executable),
            overflow="ellipsis", no_wrap=True,
        )
        if not options:
            self._console.print(
                Text(
                    "No optional dependencies or groups are declared.", _WARNING_STYLE,
                ),
            )
            return

        self._console.print()
        table = Table(box=box.SIMPLE_HEAD, padding=(0, 1), show_edge=False)
        table.add_column(
            "#", style="dim", justify="right", no_wrap=True,
            min_width=len(str(len(options))),
        )
        table.add_column("Option", no_wrap=True)
        table.add_column(
            "Packages", style="dim", no_wrap=True, overflow="ellipsis",
            max_width=self._console.width // 2,
        )
        for index, (key, requirements) in enumerate(options.items(), start=1):
            kind, _, name = key.partition(":")
            option = Text(
                key if kind == "group" else name,
                style=_ACCENT_STYLE if kind == "group" else "bold green",
            )
            if len(requirements) > 1:
                option.append(f" ({len(requirements)})", style="dim")
            table.add_row(
                str(index), option, Text(", ".join(requirements) or "No packages"),
            )
        self._console.print(table)

    def __selectOptions(self, options: dict[str, tuple[str, ...]]) -> list[str]:
        """
        Read explicit options or ask for an interactive selection.

        Parameters
        ----------
        options : dict[str, tuple[str, ...]]
            Available namespaced installation options.

        Returns
        -------
        list[str]
            Unique option keys, or an empty list for a canceled selection.

        Raises
        ------
        EOFError
            If interactive input is closed.
        KeyboardInterrupt
            If the user interrupts the prompt.
        ValueError
            If an option is unknown or ambiguous.
        """
        raw = " ".join(self.getArgument("options", default=[]) or [])
        if not raw:
            if not self._console.is_interactive:
                self._console.print(Text(
                    "Pass option names and --yes to install non-interactively.",
                    _WARNING_STYLE,
                ))
                return []
            raw = Prompt.ask(
                "[bold cyan]Select names or numbers[/bold cyan] "
                "(separate with spaces or commas; 0 cancels)",
                console=self._console,
                default="0",
            )

        if raw.strip() in {"", "0"}:
            self._console.print(Text("Installation canceled.", _WARNING_STYLE))
            return []
        keys = tuple(options)
        return list(dict.fromkeys(
            self.__resolveOption(token, keys)
            for token in raw.replace(",", " ").split()
        ))

    @staticmethod
    def __resolveOption(token: str, keys: tuple[str, ...]) -> str:
        """
        Resolve a catalog number, namespaced key or unambiguous name.

        Parameters
        ----------
        token : str
            Selection supplied by the user.
        keys : tuple[str, ...]
            Available keys in the order displayed by the catalog.

        Returns
        -------
        str
            Canonical installation option key.

        Raises
        ------
        ValueError
            If a number is out of range or a name is unknown or ambiguous.
        """
        if token in keys:
            return token
        if token.isdecimal():
            index = int(token) - 1
            if 0 <= index < len(keys):
                return keys[index]
        matches = [key for key in keys if key.partition(":")[2] == token]
        if len(matches) == 1:
            return matches[0]
        if matches:
            error_msg = f"Ambiguous option '{token}': use {' or '.join(matches)}."
        else:
            error_msg = f"Unknown installation option: '{token}'."
        raise ValueError(error_msg)

    async def __installSelection(
        self,
        project_root: Path,
        options: dict[str, tuple[str, ...]],
        selected: list[str],
    ) -> int:
        """
        Confirm and install all requirements from the selected options.

        Parameters
        ----------
        project_root : Path
            Working directory for relative package references.
        options : dict[str, tuple[str, ...]]
            Available dependency requirements.
        selected : list[str]
            Canonical keys chosen by the user.

        Returns
        -------
        int
            Installer status, zero for cancellation or an empty selection,
            or one when non-interactive confirmation is missing.

        Raises
        ------
        EOFError
            If interactive confirmation input is closed.
        KeyboardInterrupt
            If the user interrupts the confirmation prompt.
        OSError
            If the installer process cannot be started.
        """
        requirements = tuple(dict.fromkeys(
            requirement for key in selected for requirement in options[key]
        ))
        if not requirements:
            self._console.print(Text(
                "The selection contains no packages.", _WARNING_STYLE,
            ))
            return 0

        summary = Text.assemble(
            ("Options   ", _ACCENT_STYLE), ", ".join(selected),
            ("\nPackages  ", _ACCENT_STYLE), str(len(requirements)),
            ("\nTarget    ", _ACCENT_STYLE), sys.executable,
        )
        self._console.print(Panel(
            summary, title="Installation", border_style="green", padding=(1, 2),
        ))
        confirmed = self.getArgument("yes", default=False)
        if not confirmed:
            if not self._console.is_interactive:
                self._console.print(Text(
                    "Confirmation required: pass --yes to install these packages.",
                    _ERROR_STYLE,
                ))
                return 1
            confirmed = await to_thread(
                Confirm.ask, "Install selected packages?",
                console=self._console, default=False,
            )
        if not confirmed:
            self._console.print(Text("Installation canceled.", _WARNING_STYLE))
            return 0
        return await self.__runInstaller(project_root, requirements)

    async def __runInstaller(
        self,
        project_root: Path,
        requirements: tuple[str, ...],
    ) -> int:
        """
        Run uv against the current Python environment without a shell.

        Parameters
        ----------
        project_root : Path
            Working directory used to resolve local dependency references.
        requirements : tuple[str, ...]
            Requirement strings passed unchanged as individual arguments.

        Returns
        -------
        int
            Zero on success, one when uv is missing or terminated by a signal,
            or the positive exit code reported by uv.

        Raises
        ------
        CancelledError
            If execution is canceled after stopping and waiting for the child.
        OSError
            If uv cannot be started.
        """
        executable = await to_thread(which, "uv")
        if executable is None:
            self._console.print(Text(
                "uv is required but was not found on PATH. Install uv and retry.",
                _ERROR_STYLE,
            ))
            return 1

        with self._console.status(
            "Installing selected packages...", spinner="dots", spinner_style="cyan",
        ):
            process = await create_subprocess_exec(
                executable, "pip", "install", "--python", sys.executable,
                "--", *requirements,
                cwd=project_root, stdin=DEVNULL, stdout=PIPE, stderr=STDOUT,
            )
            try:
                output, _ = await process.communicate()
            except CancelledError:
                with suppress(ProcessLookupError):
                    process.terminate()
                await process.wait()
                raise

        if output:
            self._console.print(Text(output.decode("utf-8", errors="replace")))
        exit_code = process.returncode
        if exit_code:
            self._console.print(Text(
                f"Installation failed (exit code {exit_code}).", _ERROR_STYLE,
            ))
            return exit_code if exit_code > 0 else 1
        self._console.print(Text("Packages installed successfully.", "bold green"))
        return 0
