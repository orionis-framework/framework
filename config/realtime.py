from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.realtime import RealtimeConfig

@dataclass(frozen=True, slots=True, kw_only=True)
class BootstrapRealtime(RealtimeConfig):
    # ----------------------------------------------------------------------------------
    # max_message_size : int, optional
    # --- Maximum incoming message size in bytes. Defaults to the value of the
    # --- 'REALTIME_MAX_MESSAGE_SIZE' environment variable or 1048576.
    # ----------------------------------------------------------------------------------
    max_message_size: int = field(
        default_factory=lambda: Env.get("REALTIME_MAX_MESSAGE_SIZE", 1024 * 1024),
    )

    # ----------------------------------------------------------------------------------
    # max_concurrent_invocations : int, optional
    # --- Maximum concurrent invocations per connection. Defaults to the value of the
    # --- 'REALTIME_MAX_CONCURRENT_INVOCATIONS' environment variable or 16.
    # ----------------------------------------------------------------------------------
    max_concurrent_invocations: int = field(
        default_factory=lambda: Env.get("REALTIME_MAX_CONCURRENT_INVOCATIONS", 16),
    )

    # ----------------------------------------------------------------------------------
    # max_pending_client_invocations : int, optional
    # --- Maximum pending client-result calls per connection. Defaults to the value
    # --- of the 'REALTIME_MAX_PENDING_CLIENT_INVOCATIONS' environment variable or 32.
    # ----------------------------------------------------------------------------------
    max_pending_client_invocations: int = field(
        default_factory=lambda: Env.get(
            "REALTIME_MAX_PENDING_CLIENT_INVOCATIONS", 32,
        ),
    )

    # ----------------------------------------------------------------------------------
    # invocation_timeout : float, optional
    # --- Timeout in seconds for ordinary invocations, not connection or stream
    # --- lifetimes. Defaults to 'REALTIME_INVOCATION_TIMEOUT' or 30.0.
    # ----------------------------------------------------------------------------------
    invocation_timeout: float = field(
        default_factory=lambda: Env.get("REALTIME_INVOCATION_TIMEOUT", 30.0),
    )

    # ----------------------------------------------------------------------------------
    # client_result_timeout : float, optional
    # --- Timeout in seconds for client-result calls, not connection lifetimes.
    # --- Defaults to 'REALTIME_CLIENT_RESULT_TIMEOUT' or 30.0.
    # ----------------------------------------------------------------------------------
    client_result_timeout: float = field(
        default_factory=lambda: Env.get("REALTIME_CLIENT_RESULT_TIMEOUT", 30.0),
    )

    # ----------------------------------------------------------------------------------
    # broadcast_concurrency : int, optional
    # --- Maximum concurrent broadcast deliveries. Defaults to the value of the
    # --- 'REALTIME_BROADCAST_CONCURRENCY' environment variable or 32.
    # ----------------------------------------------------------------------------------
    broadcast_concurrency: int = field(
        default_factory=lambda: Env.get("REALTIME_BROADCAST_CONCURRENCY", 32),
    )

    # ----------------------------------------------------------------------------------
    # max_groups_per_connection : int, optional
    # --- Maximum group memberships per connection. Defaults to the value of the
    # --- 'REALTIME_MAX_GROUPS_PER_CONNECTION' environment variable or 64.
    # ----------------------------------------------------------------------------------
    max_groups_per_connection: int = field(
        default_factory=lambda: Env.get("REALTIME_MAX_GROUPS_PER_CONNECTION", 64),
    )
