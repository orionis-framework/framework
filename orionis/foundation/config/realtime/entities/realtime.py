from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_integer, validate_seconds
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, slots=True, kw_only=True)
class RealtimeConfig(BaseEntity):
    """
    Configure finite per-connection RPC budgets and broadcast concurrency.

    Stream lifetimes are unlimited unless their invoke envelope supplies a
    timeout. Ordinary invocations use ``invocation_timeout``; client-result
    calls use ``client_result_timeout``. Neither limits connection lifetime.
    """

    max_message_size: int = field(
        default_factory=lambda: Env.get("REALTIME_MAX_MESSAGE_SIZE", 1024 * 1024),
        metadata={
            "description": "Maximum incoming message size in bytes.",
            "default": 1024 * 1024,
        },
    )

    max_concurrent_invocations: int = field(
        default_factory=lambda: Env.get("REALTIME_MAX_CONCURRENT_INVOCATIONS", 16),
        metadata={
            "description": "Maximum concurrent invocations per connection.",
            "default": 16,
        },
    )

    max_pending_client_invocations: int = field(
        default_factory=lambda: Env.get(
            "REALTIME_MAX_PENDING_CLIENT_INVOCATIONS", 32,
        ),
        metadata={
            "description": "Maximum pending client-result calls per connection.",
            "default": 32,
        },
    )

    invocation_timeout: float = field(
        default_factory=lambda: Env.get("REALTIME_INVOCATION_TIMEOUT", 30.0),
        metadata={
            "description": "Timeout in seconds for ordinary invocations.",
            "default": 30.0,
        },
    )

    client_result_timeout: float = field(
        default_factory=lambda: Env.get("REALTIME_CLIENT_RESULT_TIMEOUT", 30.0),
        metadata={
            "description": "Timeout in seconds for client-result calls.",
            "default": 30.0,
        },
    )

    broadcast_concurrency: int = field(
        default_factory=lambda: Env.get("REALTIME_BROADCAST_CONCURRENCY", 32),
        metadata={
            "description": "Maximum concurrent broadcast deliveries.",
            "default": 32,
        },
    )

    max_groups_per_connection: int = field(
        default_factory=lambda: Env.get("REALTIME_MAX_GROUPS_PER_CONNECTION", 64),
        metadata={
            "description": "Maximum group memberships per connection.",
            "default": 64,
        },
    )

    def __post_init__(self) -> None:
        """
        Reject boolean counts, nonpositive budgets and nonfinite timeouts.

        Returns
        -------
        None
            Complete configuration validation.

        Raises
        ------
        TypeError
            If a budget or timeout has the wrong type.
        ValueError
            If a count is nonpositive or a timeout is not finite and positive.
        """
        for name in (
            "max_message_size", "max_concurrent_invocations",
            "max_pending_client_invocations", "broadcast_concurrency",
            "max_groups_per_connection",
        ):
            validate_integer(getattr(self, name), name, minimum=1)
        validate_seconds(self.invocation_timeout, "invocation_timeout", positive=True)
        validate_seconds(
            self.client_result_timeout, "client_result_timeout", positive=True,
        )
