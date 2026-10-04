from typing import TYPE_CHECKING, cast
from orionis.foundation.contracts.application import IApplication  # noqa: TC001
from orionis.foundation.contracts.directory import IDirectory

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

class Directory(IDirectory):
    """Expose the configured application directories."""

    __slots__ = ("_all_paths",)

    def __init__(self, app: IApplication) -> None:
        """Snapshot all resolved application paths from their shared mapping.

        Parameters
        ----------
        app : IApplication
            Application instance that owns the configured paths.

        Returns
        -------
        None
            Initialize directory accessors with an independent path mapping.
        """
        self._all_paths = dict(cast("Mapping[str, Path]", app.path()))

    def _path(self, key: str) -> Path:
        """Return a cached path for a configured key.

        Parameters
        ----------
        key : str
            Key registered in the application path configuration.

        Returns
        -------
        Path
            Configured path for ``key``.
        """
        return self._all_paths[key]

    def root(self) -> Path:
        """Return the application root directory.

        Returns
        -------
        Path
            The configured application root directory.
        """
        return self._path("root")

    def app(self) -> Path:
        """Return the application directory.

        Returns
        -------
        Path
            The configured application directory.
        """
        return self._path("app")

    def appConsole(self) -> Path:
        """Return the application console directory.

        Returns
        -------
        Path
            The configured application console directory.
        """
        return self._path("app_console")

    def appConsoleCommands(self) -> Path:
        """Return the application console commands directory.

        Returns
        -------
        Path
            The configured application console commands directory.
        """
        return self._path("app_console_commands")

    def appConsoleListeners(self) -> Path:
        """Return the application console listeners directory.

        Returns
        -------
        Path
            The configured application console listeners directory.
        """
        return self._path("app_console_listeners")

    def appExceptions(self) -> Path:
        """Return the application exceptions directory.

        Returns
        -------
        Path
            The configured application exceptions directory.
        """
        return self._path("app_exceptions")

    def appHttp(self) -> Path:
        """Return the application HTTP directory.

        Returns
        -------
        Path
            The configured application HTTP directory.
        """
        return self._path("app_http")

    def appHttpControllers(self) -> Path:
        """Return the application controllers directory.

        Returns
        -------
        Path
            The configured application controllers directory.
        """
        return self._path("app_http_controllers")

    def appHttpMiddleware(self) -> Path:
        """Return the application HTTP middleware directory.

        Returns
        -------
        Path
            The configured application HTTP middleware directory.
        """
        return self._path("app_http_middleware")

    def appHttpSchemas(self) -> Path:
        """Return the application HTTP schemas directory.

        Returns
        -------
        Path
            The configured application HTTP schemas directory.
        """
        return self._path("app_http_schemas")

    def appHttpSchemasRules(self) -> Path:
        """Return the application HTTP schema rules directory.

        Returns
        -------
        Path
            The configured application HTTP schema rules directory.
        """
        return self._path("app_http_schemas_rules")

    def appModels(self) -> Path:
        """Return the application models directory.

        Returns
        -------
        Path
            The configured application models directory.
        """
        return self._path("app_models")

    def appMcp(self) -> Path:
        """Return the MCP application directory.

        Returns
        -------
        Path
            The configured application directory.
        """
        return self._path("app_mcp")

    def appMcpServers(self) -> Path:
        """Return the MCP server declaration directory.

        Returns
        -------
        Path
            The configured MCP declarations directory.
        """
        return self._path("app_mcp_servers")

    def appMcpTools(self) -> Path:
        """Return the MCP tool declaration directory.

        Returns
        -------
        Path
            The configured MCP declarations directory.
        """
        return self._path("app_mcp_tools")

    def appMcpResources(self) -> Path:
        """Return the MCP resource declaration directory.

        Returns
        -------
        Path
            The configured MCP declarations directory.
        """
        return self._path("app_mcp_resources")

    def appMcpPrompts(self) -> Path:
        """Return the MCP prompt declaration directory.

        Returns
        -------
        Path
            The configured MCP declarations directory.
        """
        return self._path("app_mcp_prompts")

    def appProviders(self) -> Path:
        """Return the application providers directory.

        Returns
        -------
        Path
            The configured application providers directory.
        """
        return self._path("app_providers")

    def appNotifications(self) -> Path:
        """Return the application notifications directory.

        Returns
        -------
        Path
            The configured application notifications directory.
        """
        return self._path("app_notifications")

    def appServices(self) -> Path:
        """Return the application services directory.

        Returns
        -------
        Path
            The configured application services directory.
        """
        return self._path("app_services")

    def appFacades(self) -> Path:
        """Return the application facades directory.

        Returns
        -------
        Path
            The configured application facades directory.
        """
        return self._path("app_facades")

    def appJobs(self) -> Path:
        """Return the application jobs directory.

        Returns
        -------
        Path
            The configured application jobs directory.
        """
        return self._path("app_jobs")

    def appContracts(self) -> Path:
        """Return the application contracts directory.

        Returns
        -------
        Path
            The configured application contracts directory.
        """
        return self._path("app_contracts")

    def bootstrap(self) -> Path:
        """Return the bootstrap directory.

        Returns
        -------
        Path
            The configured bootstrap directory.
        """
        return self._path("bootstrap")

    def config(self) -> Path:
        """Return the configuration directory.

        Returns
        -------
        Path
            The configured configuration directory.
        """
        return self._path("config")

    def database(self) -> Path:
        """Return the database directory.

        Returns
        -------
        Path
            The configured database directory.
        """
        return self._path("database")

    def databaseFactories(self) -> Path:
        """Return the database factories directory.

        Returns
        -------
        Path
            The configured database factories directory.
        """
        return self._path("database_factories")

    def databaseMigrations(self) -> Path:
        """Return the database migrations directory.

        Returns
        -------
        Path
            The configured database migrations directory.
        """
        return self._path("database_migrations")

    def databaseSchemas(self) -> Path:
        """Return the database schemas directory.

        Returns
        -------
        Path
            The configured database schemas directory.
        """
        return self._path("database_schemas")

    def databaseSeeders(self) -> Path:
        """Return the database seeders directory.

        Returns
        -------
        Path
            The configured database seeders directory.
        """
        return self._path("database_seeders")

    def resources(self) -> Path:
        """Return the resources directory.

        Returns
        -------
        Path
            The configured resources directory.
        """
        return self._path("resources")

    def resourcesCss(self) -> Path:
        """Return the resources CSS directory.

        Returns
        -------
        Path
            The configured resources CSS directory.
        """
        return self._path("resources_css")

    def resourcesJs(self) -> Path:
        """Return the resources JavaScript directory.

        Returns
        -------
        Path
            The configured resources JavaScript directory.
        """
        return self._path("resources_js")

    def resourcesLang(self) -> Path:
        """Return the resources language directory.

        Returns
        -------
        Path
            The configured resources language directory.
        """
        return self._path("resources_lang")

    def resourcesViews(self) -> Path:
        """Return the resources views directory.

        Returns
        -------
        Path
            The configured resources views directory.
        """
        return self._path("resources_views")

    def routes(self) -> Path:
        """Return the routes directory.

        Returns
        -------
        Path
            The configured routes directory.
        """
        return self._path("routes")

    def storage(self) -> Path:
        """Return the storage directory.

        Returns
        -------
        Path
            The configured storage directory.
        """
        return self._path("storage")

    def storageApp(self) -> Path:
        """Return the storage application directory.

        Returns
        -------
        Path
            The configured storage application directory.
        """
        return self._path("storage_app")

    def storageAppPrivate(self) -> Path:
        """Return the private storage application directory.

        Returns
        -------
        Path
            The configured private storage application directory.
        """
        return self._path("storage_app_private")

    def storageAppPublic(self) -> Path:
        """Return the public storage application directory.

        Returns
        -------
        Path
            The configured public storage application directory.
        """
        return self._path("storage_app_public")

    def storageFramework(self) -> Path:
        """Return the framework storage directory.

        Returns
        -------
        Path
            The configured framework storage directory.
        """
        return self._path("storage_framework")

    def storageLogs(self) -> Path:
        """Return the storage logs directory.

        Returns
        -------
        Path
            The configured storage logs directory.
        """
        return self._path("storage_logs")

    def tests(self) -> Path:
        """Return the tests directory.

        Returns
        -------
        Path
            The configured tests directory.
        """
        return self._path("tests")
