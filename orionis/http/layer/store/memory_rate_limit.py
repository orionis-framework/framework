from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from time import monotonic
from orionis.foundation.config.validation import validate_integer

@dataclass(slots=True)
class _RateLimitBucket:
    """Track accepted timestamps and the time the last one expires."""

    expires_at: float
    timestamps: deque[float] = field(default_factory=deque)

class MemoryRateLimitStore:

    __slots__ = (
        "__keys", "__lock", "__max_events", "__max_keys", "__storage",
        "__ticks", "__total_events",
    )

    # Inspect a bounded group of keys after each group of request attempts.
    _GC_INTERVAL: int = 16
    _GC_BATCH_SIZE: int = 64

    def __init__(
        self,
        *,
        max_keys: int = 10_000,
        max_events: int = 100_000,
    ) -> None:
        """
        Initialize an empty rate-limit store.

        Parameters
        ----------
        max_keys : int, optional
            Maximum number of retained client buckets.
        max_events : int, optional
            Maximum number of accepted timestamps retained across all clients.

        Returns
        -------
        None
        """
        validate_integer(max_keys, "max_keys", minimum=1)
        validate_integer(max_events, "max_events", minimum=1)
        self.__max_keys = max_keys
        self.__max_events = max_events
        self.__lock = Lock()
        self.__total_events = 0
        self.__storage: dict[str, _RateLimitBucket] = {}
        self.__keys: deque[str] = deque()
        self.__ticks: int = 0

    async def hit( # NOSONAR
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
        """
        Record a request attempt and decide whether it is allowed.

        Implements a sliding window over accepted attempts. Inactive keys are
        reclaimed incrementally during subsequent attempts, including rejected
        attempts. Each key should use a consistent window. A lock serializes
        updates across event loops and threads. Capacity exhaustion rejects
        attempts without evicting active quotas or retaining rejected clients.

        Parameters
        ----------
        key : str
            Unique identifier for the rate-limited entity (e.g. IP,
            user id, route).
        limit : int
            Maximum number of requests allowed within ``window``.
        window : int
            Length of the sliding window in seconds.

        Returns
        -------
        bool
            ``True`` when the request is within the limit,
            ``False`` when the quota is exceeded.
        """
        with self.__lock:
            return self.__hit(key, limit, window)

    def __hit(self, key: str, limit: int, window: int) -> bool:
        """
        Update quota and capacity counters while holding the store lock.

        Parameters
        ----------
        key : str
            Client identity whose timestamps are retained.
        limit : int
            Maximum accepted attempts per client window.
        window : int
            Sliding-window duration in seconds.

        Returns
        -------
        bool
            Whether quota and retained-object capacity permit this attempt.
        """
        now = monotonic()
        self.__ticks += 1
        if self.__ticks >= self._GC_INTERVAL:
            self.__ticks = 0
            self.__gc(now)

        if limit <= 0:
            return False

        entry = self.__storage.get(key)
        if entry is None:
            entry = self.__newBucket(key, now, window)
            if entry is None:
                return False
        bucket = entry.timestamps
        cutoff = now - window

        # Discard accepted attempts outside this key's sliding window.
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
            self.__total_events -= 1

        if len(bucket) >= limit:
            entry.expires_at = bucket[-1] + window
            return False

        if self.__total_events >= self.__max_events:
            self.__gc(now)
            if self.__total_events >= self.__max_events:
                return False

        # Collection may have removed this client's expired bucket.
        if key not in self.__storage:
            self.__storage[key] = entry
            self.__keys.append(key)

        bucket.append(now)
        self.__total_events += 1
        entry.expires_at = now + window
        return True

    def __newBucket(
        self, key: str, now: float, window: int,
    ) -> _RateLimitBucket | None:
        """
        Create a bucket only when bounded reclamation makes room for it.

        Parameters
        ----------
        key : str
            Client identity to retain.
        now : float
            Current monotonic timestamp.
        window : int
            Sliding-window duration in seconds.

        Returns
        -------
        _RateLimitBucket | None
            New empty bucket, or None when the store cannot retain more clients.
        """
        if self.__atCapacity():
            self.__gc(now)
            if self.__atCapacity():
                return None
        entry = _RateLimitBucket(now + window)
        self.__storage[key] = entry
        self.__keys.append(key)
        return entry

    def __atCapacity(self) -> bool:
        """
        Report whether admitting a new client would exceed either bound.

        Returns
        -------
        bool
            Whether client or timestamp capacity is exhausted.
        """
        return (
            len(self.__storage) >= self.__max_keys
            or self.__total_events >= self.__max_events
        )

    def __gc(self, now: float) -> None:
        """
        Inspect the next group of keys and remove expired buckets.

        Parameters
        ----------
        now : float
            Current monotonic timestamp.

        Returns
        -------
        None
        """
        keys = self.__keys
        storage = self.__storage
        for _ in range(min(len(keys), self._GC_BATCH_SIZE)):
            key = keys.popleft()
            if storage[key].expires_at <= now:
                self.__total_events -= len(storage[key].timestamps)
                del storage[key]
            else:
                keys.append(key)

