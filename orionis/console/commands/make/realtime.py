"""Provide console commands make operations.

Includes ``MakeRealtimeSocket``, ``MakeRealtimeHub``.
"""

from orionis.console.commands.make._base import MakeStubCommand


class MakeRealtimeSocket(MakeStubCommand):
    """Generate an invokable realtime WebSocket handler."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeRealtimeSocket``."""
    signature: str = "make:realtime-socket"
    """Signature identifier: ``make:realtime-socket``."""
    description: str = "Creates a new realtime WebSocket handler."
    """Description identifier: ``Creates a new realtime WebSocket handler.``."""
    template_name: str = "realtime_socket"
    """Template name identifier: ``realtime_socket``."""
    path_key: str = "app_realtime_sockets"
    """Path key identifier: ``app_realtime_sockets``."""
    success_label: str = "Realtime socket"
    """Success label identifier: ``Realtime socket``."""
    postfix: str | None = "Socket"
    """Postfix identifier: ``Socket``."""


class MakeRealtimeHub(MakeStubCommand):
    """Generate a realtime hub with a typed remote operation."""

    timestamps: bool = False
    """Timestamps flag used by ``MakeRealtimeHub``."""
    signature: str = "make:realtime-hub"
    """Signature identifier: ``make:realtime-hub``."""
    description: str = "Creates a new realtime hub."
    """Description identifier: ``Creates a new realtime hub.``."""
    template_name: str = "realtime_hub"
    """Template name identifier: ``realtime_hub``."""
    path_key: str = "app_realtime_hubs"
    """Path key identifier: ``app_realtime_hubs``."""
    success_label: str = "Realtime hub"
    """Success label identifier: ``Realtime hub``."""
    postfix: str | None = "Hub"
    """Postfix identifier: ``Hub``."""
