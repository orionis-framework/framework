import ast
from collections.abc import Mapping
from typing import TYPE_CHECKING
from orionis.console.commands.bootstrap._editor import BootstrapEditor
from orionis.console.commands.bootstrap._paths import application_path, display_path
from orionis.console.templates.stub import Stub
from orionis.introspection.modules.inspector import ModuleInspector

if TYPE_CHECKING:
    from pathlib import Path
    from orionis.foundation.contracts.application import IApplication

_HTTP_PATHS = (
    "app_http_controllers", "app_http_middleware", "app_http_schemas",
    "app_http_schemas_rules",
)
_CONTEXT_PATHS = {
    "api": _HTTP_PATHS,
    "web": _HTTP_PATHS,
    "websocket": _HTTP_PATHS,
    "console": ("app_console_commands", "app_console_listeners"),
    "ai": (
        "app_mcp_servers", "app_mcp_tools", "app_mcp_resources", "app_mcp_prompts",
    ),
}

class Bootstrapper:
    """Plan bootstrap integration before creating optional project resources."""

    def __init__(self, app: IApplication) -> None:
        """
        Store the configured application.

        Parameters
        ----------
        app : IApplication
            Application providing effective routes and component paths.

        Returns
        -------
        None
            Store the application used by subsequent bootstrap operations.
        """
        # Retain the live application so customized paths remain authoritative.
        self.app = app

    def _editor(self) -> BootstrapEditor:
        """
        Find the source recorded by Application.create.

        Returns
        -------
        BootstrapEditor
            Editor for the effective entry point or conventional bootstrap file.

        Raises
        ------
        FileNotFoundError
            If the application bootstrap source cannot be found.
        """
        # Prefer the source recorded by Application over a conventional filename.
        entry_point = getattr(self.app, "entryPoint", None)
        if isinstance(entry_point, str) and entry_point:
            module = entry_point.partition(":")[0]
            candidate = self.app.basePath.joinpath(*module.split("."))
            candidate = candidate.with_suffix(".py")
            if candidate.is_file():
                return BootstrapEditor(candidate, self.app.basePath)
        candidate = application_path(self.app, "bootstrap") / "app.py"
        if not candidate.is_file():
            error_msg = f"Application bootstrap source does not exist: {candidate}"
            raise FileNotFoundError(error_msg)
        return BootstrapEditor(candidate, self.app.basePath)

    def _directory(self, path: Path) -> tuple[str, str]:
        """
        Create a directory without changing existing resources.

        Parameters
        ----------
        path : Path
            Effective component directory.

        Returns
        -------
        tuple[str, str]
            Action and resource path for Reactor output.
        """
        # Preserve existing directories and create only missing parents.
        existed = path.is_dir()
        path.mkdir(parents=True, exist_ok=True)
        return ("EXISTS" if existed else "CREATED", display_path(self.app, path))

    def _file(self, path: Path, content: str) -> tuple[str, str]:
        """
        Create a template exclusively, preserving existing file bytes.

        Parameters
        ----------
        path : Path
            Exact effective target, including its original filename.
        content : str
            Rendered Python template.

        Returns
        -------
        tuple[str, str]
            Action and resource path for Reactor output.

        Raises
        ------
        ValueError
            If the target exists but is not a regular file.
        """
        # Treat existing resources as immutable and reject incompatible targets.
        if path.is_symlink() or path.exists():
            if not path.is_file():
                error_msg = f"Bootstrap resource is not a regular file: {path}"
                raise ValueError(error_msg)
            return ("EXISTS", display_path(self.app, path))
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents concurrent commands from replacing a file.
        try:
            target = path.open("x", encoding="utf-8", newline="\n")
        except FileExistsError:
            if not path.is_file():
                raise
            return ("EXISTS", display_path(self.app, path))
        # Remove an incomplete file so a later invocation can recreate it safely.
        try:
            with target:
                target.write(content)
        except OSError:
            path.unlink(missing_ok=True)
            raise
        return ("CREATED", display_path(self.app, path))

    def _routing_paths(
        self, editor: BootstrapEditor, context: str,
    ) -> list[Path]:
        """
        Reconcile declared routes with the loaded application registry.

        Parameters
        ----------
        editor : BootstrapEditor
            Safely identified application bootstrap.
        context : str
            Context whose effective files are required.

        Returns
        -------
        list[Path]
            Effective route files or the context's default destination.

        Raises
        ------
        ValueError
            If declared and effective routing cannot be reconciled safely.
        """
        # Refuse indirect configuration that a new withRouting call could replace.
        effective_routing = self.app.routingPaths()
        if (
            not editor.hasRouting
            and isinstance(effective_routing, Mapping)
            and any(effective_routing.values())
        ):
            error_msg = (
                f"Routing in {editor.path} is configured indirectly. "
                "Cannot safely update its registration without replacing "
                "existing contexts or health settings."
            )
            raise ValueError(error_msg)
        # Reconcile static declarations with the paths loaded by Application.
        routes = self.app.routingPaths(context)
        source_routes = editor.routePaths(context)
        if routes and source_routes:
            loaded = [(self.app.basePath / path).resolve() for path in routes]
            declared = [
                (self.app.basePath / path).resolve() for path in source_routes
            ]
            if loaded != declared:
                error_msg = (
                    f"Effective {context} routing paths differ from {editor.path}. "
                    "Cannot safely reconcile the existing registration."
                )
                raise ValueError(error_msg)
        if not routes:
            routes = source_routes
            if routes is None:
                error_msg = (
                    f"Cannot resolve dynamic {context} routing paths in {editor.path}. "
                    "The application must expose its effective routing paths."
                )
                raise ValueError(error_msg)
        paths = [self.app.basePath / path for path in routes or []]
        if not paths:
            routes_directory = application_path(self.app, "routes")
            paths = [routes_directory / f"{context}.py"]
        return paths

    @staticmethod
    def _validate_route(path: Path) -> None:
        """
        Check existing routes with the same import rules as Application.

        Parameters
        ----------
        path : Path
            Route file to preserve and register if valid.

        Returns
        -------
        None
            Accept a missing file or validate the existing routing module.

        Raises
        ------
        ValueError
            If the existing resource cannot be loaded as a routing module.
        SyntaxError
            If existing Python source cannot be compiled.
        """
        # Reuse Application's import validation without executing user code.
        if not path.exists() and not path.is_symlink():
            return
        if not path.is_file():
            error_msg = f"Routing resource is not a regular file: {path}"
            raise ValueError(error_msg)
        compile(path.read_bytes(), str(path), "exec")
        if not ModuleInspector.fileImportsAny(
            path, {"orionis.support.facades"}, allow_empty=True,
        ):
            error_msg = (
                f"Routing file '{path}' does not contain valid routing "
                "definitions required by Application.withRouting()."
            )
            raise ValueError(error_msg)

    def routing(self, context: str) -> list[tuple[str, str]]:
        """
        Enable one routing context using the application's effective paths.

        Parameters
        ----------
        context : str
            API, AI, console, web, or websocket routing context.

        Returns
        -------
        list[tuple[str, str]]
            Resource actions, followed by the bootstrap integration result.

        Raises
        ------
        ValueError
            If the context or bootstrap structure is unsafe.
        """
        # Resolve only the component paths associated with the requested context.
        if context not in _CONTEXT_PATHS:
            error_msg = f"Unknown bootstrap routing context: {context}"
            raise ValueError(error_msg)
        editor = self._editor()
        paths = self._routing_paths(editor, context)

        # Validate the edit before making any filesystem changes.
        source = editor.routing(
            context,
            paths if len(paths) > 1 else paths[0],
            registered=bool(self.app.routingPaths(context)),
        )
        content = Stub(f"bootstrap_{context}", context).render()
        compile(content, str(paths[0]), "exec")
        for path in paths:
            self._validate_route(path)
        # Generate resources only after the edit and existing files are validated.
        actions = [self._file(path, content) for path in paths]
        actions.extend(
            self._directory(application_path(self.app, key))
            for key in _CONTEXT_PATHS[context]
        )
        if source is None:
            actions.append(("SKIPPED", "Routing already registered"))
        else:
            editor.commit(source)
            actions.append(("UPDATED", display_path(self.app, editor.path)))
        return actions

    def lifespan(self) -> list[tuple[str, str]]: # NOSONAR
        """
        Create and register native lifecycle callbacks before application boot.

        Returns
        -------
        list[tuple[str, str]]
            Resource actions and the bootstrap integration result.

        Raises
        ------
        ValueError
            If an existing lifespan file does not expose its registration entry.
        """
        # Plan the registration before creating or modifying project resources.
        editor = self._editor()
        path = application_path(self.app, "bootstrap") / "lifespan.py"
        source = editor.lifespan(path)
        content = Stub("bootstrap_lifespan", "lifespan").render()
        if path.is_file():
            # Preserve existing callbacks and verify their registration entry.
            existing = path.read_bytes()
            compile(existing, str(path), "exec")
            tree = ast.parse(existing, filename=str(path))
            names = {
                node.name for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for node in tree.body:
                if (
                    source is not None
                    and isinstance(node, ast.AsyncFunctionDef)
                    and node.name == "register_lifespan_callbacks"
                ):
                    error_msg = (
                        f"Lifespan registration in {path} is asynchronous; "
                        "cannot insert an unawaited registration call."
                    )
                    raise ValueError(error_msg)
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names.update(alias.asname or alias.name for alias in node.names)
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    targets = (
                        node.targets if isinstance(node, ast.Assign) else [node.target]
                    )
                    names.update(t.id for t in targets if isinstance(t, ast.Name))
            if "register_lifespan_callbacks" not in names:
                error_msg = f"Lifespan registration function is missing in {path}"
                raise ValueError(error_msg)
        # Compile the template before publishing the file or bootstrap update.
        compile(content, str(path), "exec")
        actions = [self._file(path, content)]
        if source is None:
            actions.append(("SKIPPED", "Lifespan callbacks already registered"))
        else:
            editor.commit(source)
            actions.append(("UPDATED", display_path(self.app, editor.path)))
        return actions
