"""Group the realtime contracts components and public imports."""

from orionis.realtime.contracts.connection import RealtimeConnectionLike
from orionis.realtime.contracts.manager import IConnectionManager

__all__ = ["IConnectionManager", "RealtimeConnectionLike"]
