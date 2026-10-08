from pathlib import Path
from orionis import Application
from app.console.scheduler import Scheduler
from app.exceptions.handler import ExceptionHandler
from app.http.middleware.global_middleware import GlobalMiddleware
from app.providers.app_service_provider import AppServiceProvider
from bootstrap.lifespan import register_lifespan_callbacks

# Create the application instance with caching enabled.
app = Application(
    base_path=Path(__file__).parent.parent,
)

# Compile the application with caching and invalidation paths.
app.compile(
    path="storage/framework/bootstrap",
    invalidation_paths=[
        "app",
        "bootstrap",
        "config",
        "database",
        "resources",
        "routes",
        ".env",
    ],
)

# Register callbacks for a specific application lifespan event.
register_lifespan_callbacks(app)

# Register route files for the different runtime contexts.
app.withRouting(
    ai="routes/ai.py",
    api="routes/api.py",
    console="routes/console.py",
    web="routes/web.py",
    websocket="routes/websocket.py",
    health="/up",
)

# Attach the scheduler for scheduled CLI jobs.
app.withScheduler(Scheduler)

# Set the global exception handler for unhandled exceptions.
app.withExceptionHandler(ExceptionHandler)

# Register service providers for dependency injection.
app.withProviders(
    AppServiceProvider,
    # ...
)

# Register global middleware for HTTP request processing.
app.withMiddleware(
    GlobalMiddleware,
    # ...
)

# Boot the application and prepare the runtime environment.
app.create()
