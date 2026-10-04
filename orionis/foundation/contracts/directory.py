from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

class IDirectory(ABC):
    """Define access to the application directory paths."""

    __slots__ = ()

    @abstractmethod
    def root(self) -> Path:
        """Return the application root directory.

        Returns
        -------
        Path
            The configured application root directory.
        """

    @abstractmethod
    def app(self) -> Path:
        """Return the application directory.

        Returns
        -------
        Path
            The configured application directory.
        """

    @abstractmethod
    def appConsole(self) -> Path:
        """Return the application console directory.

        Returns
        -------
        Path
            The configured application console directory.
        """

    @abstractmethod
    def appConsoleCommands(self) -> Path:
        """Return the application console commands directory.

        Returns
        -------
        Path
            The configured application console commands directory.
        """

    @abstractmethod
    def appConsoleListeners(self) -> Path:
        """Return the application console listeners directory.

        Returns
        -------
        Path
            The configured application console listeners directory.
        """

    @abstractmethod
    def appExceptions(self) -> Path:
        """Return the application exceptions directory.

        Returns
        -------
        Path
            The configured application exceptions directory.
        """

    @abstractmethod
    def appHttp(self) -> Path:
        """Return the application HTTP directory.

        Returns
        -------
        Path
            The configured application HTTP directory.
        """

    @abstractmethod
    def appHttpControllers(self) -> Path:
        """Return the application controllers directory.

        Returns
        -------
        Path
            The configured application controllers directory.
        """

    @abstractmethod
    def appHttpMiddleware(self) -> Path:
        """Return the application HTTP middleware directory.

        Returns
        -------
        Path
            The configured application HTTP middleware directory.
        """

    @abstractmethod
    def appHttpSchemas(self) -> Path:
        """Return the application HTTP schemas directory.

        Returns
        -------
        Path
            The configured application HTTP schemas directory.
        """

    @abstractmethod
    def appHttpSchemasRules(self) -> Path:
        """Return the application HTTP schema rules directory.

        Returns
        -------
        Path
            The configured application HTTP schema rules directory.
        """

    @abstractmethod
    def appModels(self) -> Path:
        """Return the application models directory.

        Returns
        -------
        Path
            The configured application models directory.
        """

    @abstractmethod
    def appProviders(self) -> Path:
        """Return the application providers directory.

        Returns
        -------
        Path
            The configured application providers directory.
        """

    @abstractmethod
    def appNotifications(self) -> Path:
        """Return the application notifications directory.

        Returns
        -------
        Path
            The configured application notifications directory.
        """

    @abstractmethod
    def appServices(self) -> Path:
        """Return the application services directory.

        Returns
        -------
        Path
            The configured application services directory.
        """

    @abstractmethod
    def appFacades(self) -> Path:
        """Return the application facades directory.

        Returns
        -------
        Path
            The configured application facades directory.
        """

    @abstractmethod
    def appJobs(self) -> Path:
        """Return the application jobs directory.

        Returns
        -------
        Path
            The configured application jobs directory.
        """

    @abstractmethod
    def appContracts(self) -> Path:
        """Return the application contracts directory.

        Returns
        -------
        Path
            The configured application contracts directory.
        """

    @abstractmethod
    def bootstrap(self) -> Path:
        """Return the bootstrap directory.

        Returns
        -------
        Path
            The configured bootstrap directory.
        """

    @abstractmethod
    def config(self) -> Path:
        """Return the configuration directory.

        Returns
        -------
        Path
            The configured configuration directory.
        """

    @abstractmethod
    def database(self) -> Path:
        """Return the database directory.

        Returns
        -------
        Path
            The configured database directory.
        """

    @abstractmethod
    def databaseFactories(self) -> Path:
        """Return the database factories directory.

        Returns
        -------
        Path
            The configured database factories directory.
        """

    @abstractmethod
    def databaseMigrations(self) -> Path:
        """Return the database migrations directory.

        Returns
        -------
        Path
            The configured database migrations directory.
        """

    @abstractmethod
    def databaseSchemas(self) -> Path:
        """Return the database schemas directory.

        Returns
        -------
        Path
            The configured database schemas directory.
        """

    @abstractmethod
    def databaseSeeders(self) -> Path:
        """Return the database seeders directory.

        Returns
        -------
        Path
            The configured database seeders directory.
        """

    @abstractmethod
    def resources(self) -> Path:
        """Return the resources directory.

        Returns
        -------
        Path
            The configured resources directory.
        """

    @abstractmethod
    def resourcesCss(self) -> Path:
        """Return the resources CSS directory.

        Returns
        -------
        Path
            The configured resources CSS directory.
        """

    @abstractmethod
    def resourcesJs(self) -> Path:
        """Return the resources JavaScript directory.

        Returns
        -------
        Path
            The configured resources JavaScript directory.
        """

    @abstractmethod
    def resourcesLang(self) -> Path:
        """Return the resources language directory.

        Returns
        -------
        Path
            The configured resources language directory.
        """

    @abstractmethod
    def resourcesViews(self) -> Path:
        """Return the resources views directory.

        Returns
        -------
        Path
            The configured resources views directory.
        """

    @abstractmethod
    def routes(self) -> Path:
        """Return the routes directory.

        Returns
        -------
        Path
            The configured routes directory.
        """

    @abstractmethod
    def storage(self) -> Path:
        """Return the storage directory.

        Returns
        -------
        Path
            The configured storage directory.
        """

    @abstractmethod
    def storageApp(self) -> Path:
        """Return the storage application directory.

        Returns
        -------
        Path
            The configured storage application directory.
        """

    @abstractmethod
    def storageAppPrivate(self) -> Path:
        """Return the private storage application directory.

        Returns
        -------
        Path
            The configured private storage application directory.
        """

    @abstractmethod
    def storageAppPublic(self) -> Path:
        """Return the public storage application directory.

        Returns
        -------
        Path
            The configured public storage application directory.
        """

    @abstractmethod
    def storageFramework(self) -> Path:
        """Return the framework storage directory.

        Returns
        -------
        Path
            The configured framework storage directory.
        """

    @abstractmethod
    def storageLogs(self) -> Path:
        """Return the storage logs directory.

        Returns
        -------
        Path
            The configured storage logs directory.
        """

    @abstractmethod
    def tests(self) -> Path:
        """Return the tests directory.

        Returns
        -------
        Path
            The configured tests directory.
        """

    @abstractmethod
    def appMcp(self) -> Path:
        """Return the MCP application directory.

        Returns
        -------
        Path
            The configured application directory.
        """

    @abstractmethod
    def appMcpServers(self) -> Path:
        """Return the MCP server declarations directory.

        Returns
        -------
        Path
            The configured application directory.
        """

    @abstractmethod
    def appMcpTools(self) -> Path:
        """Return the MCP tool declarations directory.

        Returns
        -------
        Path
            The configured application directory.
        """

    @abstractmethod
    def appMcpResources(self) -> Path:
        """Return the MCP resource declarations directory.

        Returns
        -------
        Path
            The configured application directory.
        """

    @abstractmethod
    def appMcpPrompts(self) -> Path:
        """Return the MCP prompt declarations directory.

        Returns
        -------
        Path
            The configured application directory.
        """
