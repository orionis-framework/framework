from asyncio import to_thread
from pathlib import Path
from typing import ClassVar
from orionis.cache.file_based_cache import FileBasedCache
from orionis.console.base.command import BaseCommand
from orionis.console.commands.bootstrap._service import Bootstrapper
from orionis.console.enums.styles import ANSIColors
from orionis.foundation.contracts.application import IApplication  # noqa: TC001

class BootstrapCommand(BaseCommand):
    """Run component bootstrapping through native Reactor output and injection."""

    timestamps = False
    context: ClassVar[str]
    _action_styles: ClassVar[dict[str, ANSIColors]] = {
        "CREATED": ANSIColors.TEXT_BOLD_SUCCESS,
        "UPDATED": ANSIColors.TEXT_BOLD_INFO,
    }

    def bootstrap(self, app: IApplication) -> list[tuple[str, str]]:
        """
        Enable this command's routing context.

        Parameters
        ----------
        app : IApplication
            Configured application injected by Reactor.

        Returns
        -------
        list[tuple[str, str]]
            Successful resource actions.
        """
        # Delegate path resolution and generation to the shared bootstrap service.
        return Bootstrapper(app).routing(self.context)

    def _execute(self, app: IApplication) -> list[tuple[str, str]]:
        """
        Generate resources and invalidate existing compiled state if changed.

        Parameters
        ----------
        app : IApplication
            Application providing its configured compiled cache directory.

        Returns
        -------
        list[tuple[str, str]]
            Completed generation and cache invalidation actions.
        """
        # Clear compiled state only when resources were created or updated.
        actions = self.bootstrap(app)
        changed = any(action in {"CREATED", "UPDATED"} for action, _ in actions)
        cache_path = getattr(app, "compiledPath", None)
        if changed and isinstance(cache_path, Path) and cache_path.is_dir():
            for name in ("config", "commands", "routes"):
                if (cache_path / name).exists():
                    FileBasedCache(path=cache_path, filename=name).clear()
        return actions

    def _write_action(self, action: str, resource: str) -> None:
        """
        Write one aligned resource action with a single colored status.

        Parameters
        ----------
        action : str
            Completed resource action to display.
        resource : str
            Resource path or explanation associated with the action.

        Returns
        -------
        None
            Print one uniformly aligned row through Reactor's console output.
        """
        # Color the status alone and keep resource paths aligned across rows.
        color = self._action_styles.get(action, ANSIColors.TEXT_MUTED).value
        reset = ANSIColors.DEFAULT.value
        self.write(f"  {color}{action:<7}{reset}  {resource}")

    async def handle(self, app: IApplication) -> int:
        """
        Generate resources off the event loop and report the actual result.

        Parameters
        ----------
        app : IApplication
            Configured application injected by Reactor.

        Returns
        -------
        int
            Zero on success; one if generation or integration fails.
        """
        # Keep filesystem work off the event loop and report its actual outcome.
        self.newLine()
        try:
            actions = await to_thread(self._execute, app)
            for action, resource in actions:
                self._write_action(action, resource)
            return 0
        except (OSError, TypeError, ValueError, RuntimeError, SyntaxError) as error:
            self.error(f"{self.signature}: {error}", timestamp=False)
            return 1
        finally:
            self.newLine()
