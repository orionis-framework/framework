from pathlib import Path
from orionis.foundation.application import Application

app = (
    Application(base_path=Path(__file__).resolve().parents[2])
    .withRouting(web="tests/realtime/_granian_routes.py", health="/up")
    .withConfigApp(debug=False)
    .create()
)
