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
        """Return the application root directory."""

    @abstractmethod
    def app(self) -> Path:
        """Return the application directory."""

    @abstractmethod
    def appConsole(self) -> Path:
        """Return the application console directory."""

    @abstractmethod
    def appConsoleCommands(self) -> Path:
        """Return the application console commands directory."""

    @abstractmethod
    def appConsoleListeners(self) -> Path:
        """Return the application console listeners directory."""

    @abstractmethod
    def appExceptions(self) -> Path:
        """Return the application exceptions directory."""

    @abstractmethod
    def appHttp(self) -> Path:
        """Return the application HTTP directory."""

    @abstractmethod
    def appHttpControllers(self) -> Path:
        """Return the application controllers directory."""

    @abstractmethod
    def appHttpMiddleware(self) -> Path:
        """Return the application HTTP middleware directory."""

    @abstractmethod
    def appHttpSchemas(self) -> Path:
        """Return the application HTTP schemas directory."""

    @abstractmethod
    def appModels(self) -> Path:
        """Return the application models directory."""

    @abstractmethod
    def appProviders(self) -> Path:
        """Return the application providers directory."""

    @abstractmethod
    def appEmails(self) -> Path:
        """Return the application emails directory."""

    @abstractmethod
    def appServices(self) -> Path:
        """Return the application services directory."""

    @abstractmethod
    def appJobs(self) -> Path:
        """Return the application jobs directory."""

    @abstractmethod
    def bootstrap(self) -> Path:
        """Return the bootstrap directory."""

    @abstractmethod
    def config(self) -> Path:
        """Return the configuration directory."""

    @abstractmethod
    def database(self) -> Path:
        """Return the database directory."""

    @abstractmethod
    def databaseFactories(self) -> Path:
        """Return the database factories directory."""

    @abstractmethod
    def databaseMigrations(self) -> Path:
        """Return the database migrations directory."""

    @abstractmethod
    def databaseSchemas(self) -> Path:
        """Return the database schemas directory."""

    @abstractmethod
    def databaseSeeders(self) -> Path:
        """Return the database seeders directory."""

    @abstractmethod
    def resources(self) -> Path:
        """Return the resources directory."""

    @abstractmethod
    def resourcesCss(self) -> Path:
        """Return the resources CSS directory."""

    @abstractmethod
    def resourcesJs(self) -> Path:
        """Return the resources JavaScript directory."""

    @abstractmethod
    def resourcesLang(self) -> Path:
        """Return the resources language directory."""

    @abstractmethod
    def resourcesViews(self) -> Path:
        """Return the resources views directory."""

    @abstractmethod
    def routes(self) -> Path:
        """Return the routes directory."""

    @abstractmethod
    def storage(self) -> Path:
        """Return the storage directory."""

    @abstractmethod
    def storageApp(self) -> Path:
        """Return the storage application directory."""

    @abstractmethod
    def storageAppPrivate(self) -> Path:
        """Return the private storage application directory."""

    @abstractmethod
    def storageAppPublic(self) -> Path:
        """Return the public storage application directory."""

    @abstractmethod
    def storageFramework(self) -> Path:
        """Return the framework storage directory."""

    @abstractmethod
    def storageLogs(self) -> Path:
        """Return the storage logs directory."""

    @abstractmethod
    def tests(self) -> Path:
        """Return the tests directory."""
