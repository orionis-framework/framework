from orionis.console.commands.make._base import MakeStubCommand

class MakeRealtimeSocket(MakeStubCommand):
    """Generate an invokable realtime WebSocket handler."""

    timestamps: bool = False
    signature: str = "make:realtime-socket"
    description: str = "Creates a new realtime WebSocket handler."
    template_name: str = "realtime_socket"
    path_key: str = "app_realtime_sockets"
    success_label: str = "Realtime socket"
    postfix: str | None = "Socket"

class MakeRealtimeHub(MakeStubCommand):
    """Generate a realtime hub with a typed remote operation."""

    timestamps: bool = False
    signature: str = "make:realtime-hub"
    description: str = "Creates a new realtime hub."
    template_name: str = "realtime_hub"
    path_key: str = "app_realtime_hubs"
    success_label: str = "Realtime hub"
    postfix: str | None = "Hub"
