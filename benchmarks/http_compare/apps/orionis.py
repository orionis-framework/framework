from pathlib import Path
from orionis import Application

def create_application() -> Application:
    """Create Orionis using the routes staged by the benchmark runner."""
    return (
        Application(base_path=Path.cwd())
        .withRouting(api="_http_compare_routes.py")
        .withConfigApp(env="production", debug=False, maintenance=False)
        .create()
    )
