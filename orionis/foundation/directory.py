from typing import TYPE_CHECKING
from orionis.foundation.contracts.application import IApplication  # noqa: TC001
from orionis.foundation.contracts.directory import IDirectory

if TYPE_CHECKING:
    from pathlib import Path

class Directory(IDirectory):
    """Expose the configured application directories."""

    __slots__ = ("_all_paths",)

    def __init__(self, app: IApplication) -> None:
        """Cache all application paths resolved by the application.

        Parameters
        ----------
        app : IApplication
            Application instance that owns the configured paths.

        Returns
        -------
        None
            The directory accessors are initialized.
        """
        keys = (
            "app", "app_console", "app_console_commands",
            "app_console_listeners", "app_exceptions",
            "app_http", "app_http_controllers", "app_http_middleware",
            "app_http_schemas", "app_models", "app_providers", "app_emails",
            "app_services", "app_jobs", "bootstrap", "config", "database",
            "database_factories", "database_migrations", "database_schemas",
            "database_seeders", "resources", "resources_css", "resources_js",
            "resources_lang", "resources_views", "routes", "storage",
            "storage_app", "storage_app_private", "storage_app_public",
            "storage_framework", "storage_logs", "tests",
        )
        self._all_paths = {"root": app.path("root")}
        self._all_paths.update({key: app.path(key) for key in keys})

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
        """Return the application root directory."""
        return self._path("root")

    def app(self) -> Path:
        """Return the application directory."""
        return self._path("app")

    def appConsole(self) -> Path:
        """Return the application console directory."""
        return self._path("app_console")

    def appConsoleCommands(self) -> Path:
        """Return the application console commands directory."""
        return self._path("app_console_commands")

    def appConsoleListeners(self) -> Path:
        """Return the application console listeners directory."""
        return self._path("app_console_listeners")

    def appExceptions(self) -> Path:
        """Return the application exceptions directory."""
        return self._path("app_exceptions")

    def appHttp(self) -> Path:
        """Return the application HTTP directory."""
        return self._path("app_http")

    def appHttpControllers(self) -> Path:
        """Return the application controllers directory."""
        return self._path("app_http_controllers")

    def appHttpMiddleware(self) -> Path:
        """Return the application HTTP middleware directory."""
        return self._path("app_http_middleware")

    def appHttpSchemas(self) -> Path:
        """Return the application HTTP schemas directory."""
        return self._path("app_http_schemas")

    def appModels(self) -> Path:
        """Return the application models directory."""
        return self._path("app_models")

    def appProviders(self) -> Path:
        """Return the application providers directory."""
        return self._path("app_providers")

    def appEmails(self) -> Path:
        """Return the application emails directory."""
        return self._path("app_emails")

    def appServices(self) -> Path:
        """Return the application services directory."""
        return self._path("app_services")

    def appJobs(self) -> Path:
        """Return the application jobs directory."""
        return self._path("app_jobs")

    def bootstrap(self) -> Path:
        """Return the bootstrap directory."""
        return self._path("bootstrap")

    def config(self) -> Path:
        """Return the configuration directory."""
        return self._path("config")

    def database(self) -> Path:
        """Return the database directory."""
        return self._path("database")

    def databaseFactories(self) -> Path:
        """Return the database factories directory."""
        return self._path("database_factories")

    def databaseMigrations(self) -> Path:
        """Return the database migrations directory."""
        return self._path("database_migrations")

    def databaseSchemas(self) -> Path:
        """Return the database schemas directory."""
        return self._path("database_schemas")

    def databaseSeeders(self) -> Path:
        """Return the database seeders directory."""
        return self._path("database_seeders")

    def resources(self) -> Path:
        """Return the resources directory."""
        return self._path("resources")

    def resourcesCss(self) -> Path:
        """Return the resources CSS directory."""
        return self._path("resources_css")

    def resourcesJs(self) -> Path:
        """Return the resources JavaScript directory."""
        return self._path("resources_js")

    def resourcesLang(self) -> Path:
        """Return the resources language directory."""
        return self._path("resources_lang")

    def resourcesViews(self) -> Path:
        """Return the resources views directory."""
        return self._path("resources_views")

    def routes(self) -> Path:
        """Return the routes directory."""
        return self._path("routes")

    def storage(self) -> Path:
        """Return the storage directory."""
        return self._path("storage")

    def storageApp(self) -> Path:
        """Return the storage application directory."""
        return self._path("storage_app")

    def storageAppPrivate(self) -> Path:
        """Return the private storage application directory."""
        return self._path("storage_app_private")

    def storageAppPublic(self) -> Path:
        """Return the public storage application directory."""
        return self._path("storage_app_public")

    def storageFramework(self) -> Path:
        """Return the framework storage directory."""
        return self._path("storage_framework")

    def storageLogs(self) -> Path:
        """Return the storage logs directory."""
        return self._path("storage_logs")

    def tests(self) -> Path:
        """Return the tests directory."""
        return self._path("tests")
