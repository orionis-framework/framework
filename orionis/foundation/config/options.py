# ruff: noqa: TC001
# Keep configuration annotations resolvable by runtime type inspection.
"""Keyword options for application bootstrap and the routing-path snapshot."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Literal
from typing_extensions import TypedDict
from orionis.foundation.config import (
    app,
    auth,
    cache,
    database,
    filesystems,
    http,
    logging,
    mail,
    queue,
    session,
    testing,
)


class AppOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the app configuration section."""

    name: str
    """The name of the application."""
    env: str | app.Environments
    """Deployment environment reported by the application."""
    debug: bool
    """Enable detailed diagnostic output."""
    timezone: str
    """Time zone applied to application date and time operations."""
    locale: str
    """The locale for the application."""
    fallback_locale: str
    """The locale used when a translation is missing."""
    language_path: str
    """Relative path to the JSON translation files."""
    cipher: str | app.Cipher
    """The authenticated cipher."""
    key: str | bytes | None
    """The encryption key for the application."""
    maintenance: bool
    """Indicates whether the application is in maintenance mode."""


class AuthOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the auth configuration section."""

    default: auth.Guards | str
    """Guard used when no explicit guard is named."""
    identity: auth.Identity | dict[str, Any]
    """Identity provider and credentials used for authentication."""
    session: auth.SessionAuth | dict[str, Any]
    """Session guard settings for browser authentication."""
    tokens: auth.Tokens | dict[str, Any]
    """Personal access token guard settings."""
    passwords: auth.PasswordReset | dict[str, Any]
    """Trusted reset URL, token table, lifetime and resend delay."""
    remember: auth.RememberAuth | dict[str, Any]
    """Optional persistent login cookie name, lifetime and HTTPS requirement."""


class McpOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the mcp configuration section."""

    max_request_size: int
    """Maximum serialized MCP request size in bytes."""
    default_page_size: int
    """Default entries returned by paginated list operations."""
    max_page_size: int
    """Maximum entries returned in one page."""
    max_concurrent_requests: int
    """Maximum concurrent MCP requests."""
    subscription_buffer_size: int
    """Maximum event buffer size per subscription."""
    max_subscriptions: int
    """Maximum total event-bus subscriptions."""
    max_resource_subscriptions: int
    """Maximum resource subscriptions per request or client context."""
    subscription_keepalive: float
    """Seconds between subscription keepalive messages."""
    allowed_origins: list[str]
    """
    Browser origins accepted by the MCP HTTP transport. An empty list rejects requests
    carrying an Origin header.
    """
    tool_search_max_results: int
    """Maximum results returned by a tool catalog search."""
    tool_search_max_calls: int
    """Maximum tool calls allowed in one catalog execution."""
    tool_search_max_output_bytes: int
    """Maximum serialized tool catalog output size in bytes."""
    max_response_size: int
    """Maximum serialized MCP response size in bytes."""
    max_metadata_size: int
    """Maximum serialized request or response metadata bytes."""


class CacheOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the cache configuration section."""

    default: cache.Drivers | str
    """Name of the cache store used when no store is selected."""
    prefix: str
    """Global key prefix applied to all cache entries."""
    stores: cache.Stores | dict[str, Any]
    """The configuration for available cache stores."""


class HttpOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the http configuration section."""

    monitor_disconnects: bool
    """Monitor client disconnects during handler execution."""
    body_limits: http.HTTPBodyLimits | dict[str, Any]
    """Request body, multipart and concurrency budgets."""
    websocket: http.HTTPWebSocket | dict[str, Any]
    """WebSocket connection and incoming message budgets."""
    proxies: http.HTTPProxies | dict[str, Any]
    """Trusted proxy resolution settings."""
    security: http.HTTPSecurity | dict[str, Any]
    """Security header validation settings."""
    rate_limit: http.HTTPRateLimit | dict[str, Any]
    """Global rate limiting settings."""
    cors: http.Cors | dict[str, Any]
    """CORS (Cross-Origin Resource Sharing) settings."""
    csrf: http.HTTPCsrf | dict[str, Any]
    """CSRF protection settings for web routes."""


class DatabaseOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the database configuration section."""

    default: database.ConnectionName | str
    """Name of the database connection used by default."""
    connections: database.Connections | dict[str, Any]
    """Named connections and their database driver settings."""


class FilesystemsOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the filesystems configuration section."""

    default: filesystems.DiskName | str
    """Name of the filesystem disk used by default."""
    disks: filesystems.Disks | dict[str, Any]
    """A collection of available filesystem disks."""


class LoggingOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the logging configuration section."""

    default: str
    """The default logging channel to use."""
    channels: logging.Channels | dict[str, Any]
    """A collection of available logging channels."""
    queue_capacity: int
    """Number of pending records per handler. Zero selects synchronous emission."""


class MailOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the mail configuration section."""

    default: str | mail.MailDriver
    """The default configured mailer name."""
    from_address: mail.FromAddress | dict[str, Any]
    """The global sender used when a message declares none."""
    mailers: mail.Mailers | dict[str, Any]
    """The available named mailer configurations."""


class QueueOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the queue configuration section."""

    default: str
    """Default queue connection name."""
    connections: (
        queue.Connections
        | dict[str, queue.Sync | queue.Database | queue.Redis | dict[str, Any]]
    )
    """Named queue connection settings."""
    failed: queue.Failed | dict[str, Any]
    """Failed-job database storage."""
    worker: queue.Worker | dict[str, Any]
    """Worker defaults for polling, retries, and timeouts."""


class SessionOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the session configuration section."""

    driver: str | session.SessionDriver
    """Backend used to persist session data."""
    lifetime: int
    """Session lifetime in minutes."""
    expire_on_close: bool
    """Expire session on browser close (omits Max-Age)."""
    track_previous_url: bool
    """Remember successful navigation URLs in the session."""
    renewal_interval: int
    """Minimum seconds between unchanged session renewals."""
    files: str | None
    """Path to session files."""
    connection: str | None
    """Database connection for session storage."""
    table: str | None
    """Database table for session storage."""
    cache: str | None
    """Cache store for session storage."""
    cookie: str
    """Name of the session cookie."""
    path: str
    """URL path on which the browser sends the session cookie."""
    domain: str | None
    """Cookie domain for cross-subdomain usage."""
    secure: bool
    """Restrict cookies to HTTPS."""
    http_only: bool
    """Prevent JavaScript from accessing the cookie."""
    same_site: str | session.SameSitePolicy
    """SameSite policy applied to the session cookie."""
    partitioned: bool
    """Send the Partitioned attribute on the session cookie."""


class TestingOptions(TypedDict, total=False, extra_items=object):
    """Built-in keyword overrides for the testing configuration section."""

    verbosity: int | testing.VerbosityMode
    """Level of detail emitted by the test runner."""
    fail_fast: bool
    """If True, stops execution at the first failure."""
    start_dir: str
    """Directory to search for tests."""
    file_pattern: str
    """Filename pattern to identify test files."""
    method_pattern: str
    """Pattern to filter specific test methods."""
    cache_results: bool
    """Save a JSON file with the test results."""


type CorePathName = Literal[
    "root",
    "app",
    "app_console",
    "app_console_commands",
    "app_console_listeners",
    "app_exceptions",
    "app_http",
    "app_http_controllers",
    "app_http_middleware",
    "app_http_schemas",
    "app_http_schemas_rules",
    "app_models",
    "app_mcp",
    "app_mcp_servers",
    "app_mcp_tools",
    "app_mcp_resources",
    "app_mcp_prompts",
    "app_realtime",
    "app_realtime_sockets",
    "app_realtime_hubs",
    "app_providers",
    "app_notifications",
    "app_services",
    "app_facades",
    "app_jobs",
    "app_contracts",
    "bootstrap",
    "config",
    "database",
    "database_factories",
    "database_migrations",
    "database_schemas",
    "database_seeders",
    "resources",
    "resources_css",
    "resources_js",
    "resources_lang",
    "resources_views",
    "routes",
    "storage",
    "storage_app",
    "storage_app_private",
    "storage_app_public",
    "storage_framework",
    "storage_logs",
    "tests",
]
"""Names guaranteed to exist in the application path mapping after configuration."""


type PathOverride = str | Path | None
"""
Directory override resolved during bootstrap. Strings are relative to the application
root and None uses the default.
"""


class PathsOptions(TypedDict, total=False):
    """Paths accepted by Application.withConfigPaths."""

    app: PathOverride
    """Application source code directory. Defaults to ``app``."""
    app_console: PathOverride
    """Console components directory. Defaults to ``app/console``."""
    app_console_commands: PathOverride
    """Custom console commands directory. Defaults to ``app/console/commands``."""
    app_console_listeners: PathOverride
    """Console event listeners directory. Defaults to ``app/console/listeners``."""
    app_exceptions: PathOverride
    """Application exception handlers directory. Defaults to ``app/exceptions``."""
    app_http: PathOverride
    """HTTP components directory. Defaults to ``app/http``."""
    app_http_controllers: PathOverride
    """HTTP controllers directory. Defaults to ``app/http/controllers``."""
    app_http_middleware: PathOverride
    """HTTP middleware directory. Defaults to ``app/http/middleware``."""
    app_http_schemas: PathOverride
    """HTTP request schemas directory. Defaults to ``app/http/schemas``."""
    app_http_schemas_rules: PathOverride
    """
    Custom schema validation rules directory. Defaults to ``app/http/schemas/rules``.
    """
    app_models: PathOverride
    """ORM models directory. Defaults to ``app/models``."""
    app_mcp: PathOverride
    """MCP components directory. Defaults to ``app/mcp``."""
    app_mcp_servers: PathOverride
    """MCP servers directory. Defaults to ``app/mcp/servers``."""
    app_mcp_tools: PathOverride
    """MCP tools directory. Defaults to ``app/mcp/tools``."""
    app_mcp_resources: PathOverride
    """MCP resources directory. Defaults to ``app/mcp/resources``."""
    app_mcp_prompts: PathOverride
    """MCP prompts directory. Defaults to ``app/mcp/prompts``."""
    app_realtime: PathOverride
    """Realtime application components directory. Defaults to ``app/realtime``."""
    app_realtime_sockets: PathOverride
    """Realtime socket handlers directory. Defaults to ``app/realtime/sockets``."""
    app_realtime_hubs: PathOverride
    """Realtime hubs directory. Defaults to ``app/realtime/hubs``."""
    app_providers: PathOverride
    """Service providers directory. Defaults to ``app/providers``."""
    app_notifications: PathOverride
    """Application notifications directory. Defaults to ``app/notifications``."""
    app_services: PathOverride
    """Application services directory. Defaults to ``app/services``."""
    app_facades: PathOverride
    """Application-defined facades directory. Defaults to ``app/facades``."""
    app_jobs: PathOverride
    """Queue jobs directory. Defaults to ``app/jobs``."""
    app_contracts: PathOverride
    """Application service contracts directory. Defaults to ``app/contracts``."""
    bootstrap: PathOverride
    """Application bootstrap code directory. Defaults to ``bootstrap``."""
    config: PathOverride
    """Configuration modules directory. Defaults to ``config``."""
    database: PathOverride
    """Database assets directory. Defaults to ``database``."""
    database_factories: PathOverride
    """Model factories directory. Defaults to ``database/factories``."""
    database_migrations: PathOverride
    """Database migrations directory. Defaults to ``database/migrations``."""
    database_schemas: PathOverride
    """Database schema definitions directory. Defaults to ``database/schemas``."""
    database_seeders: PathOverride
    """Database seeders directory. Defaults to ``database/seeders``."""
    resources: PathOverride
    """Application resources directory. Defaults to ``resources``."""
    resources_css: PathOverride
    """Stylesheets directory. Defaults to ``resources/css``."""
    resources_js: PathOverride
    """JavaScript assets directory. Defaults to ``resources/js``."""
    resources_lang: PathOverride
    """Translation files directory. Defaults to ``resources/lang``."""
    resources_views: PathOverride
    """View templates directory. Defaults to ``resources/views``."""
    routes: PathOverride
    """Route declarations directory. Defaults to ``routes``."""
    storage: PathOverride
    """Application storage directory. Defaults to ``storage``."""
    storage_app: PathOverride
    """Application-managed files directory. Defaults to ``storage/app``."""
    storage_app_private: PathOverride
    """Private application files directory. Defaults to ``storage/app/private``."""
    storage_app_public: PathOverride
    """Public application files directory. Defaults to ``storage/app/public``."""
    storage_framework: PathOverride
    """Framework runtime state directory. Defaults to ``storage/framework``."""
    storage_logs: PathOverride
    """Application logs directory. Defaults to ``storage/logs``."""
    tests: PathOverride
    """Application tests directory. Defaults to ``tests``."""


class RoutingPaths(TypedDict, total=False):
    """Copies of configured route files and the optional health endpoint."""

    api: list[Path]
    """Files that declare HTTP API routes."""
    web: list[Path]
    """Files that declare browser routes."""
    console: list[Path]
    """Files that register console routes or commands."""
    ai: list[Path]
    """Files that register AI routes and services."""
    websocket: list[Path]
    """Files that declare WebSocket routes."""
    health: str | None
    """Configured path of the HTTP health-check endpoint."""
