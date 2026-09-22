from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from time import monotonic

@dataclass(slots=True)
class _RateLimitBucket:
    """Track accepted timestamps and the time the last one expires."""

    expires_at: float
    timestamps: deque[float] = field(default_factory=deque)

class MemoryRateLimitStore:

    __slots__ = ("__keys", "__storage", "__ticks")

    # Inspect a bounded group of keys after each group of request attempts.
    _GC_INTERVAL: int = 16
    _GC_BATCH_SIZE: int = 64

    def __init__(self) -> None:
        """Initialize an empty rate-limit store.

        Returns
        -------
        None
        """
        self.__storage: dict[str, _RateLimitBucket] = {}
        self.__keys: deque[str] = deque()
        self.__ticks: int = 0

    async def hit( # NOSONAR
        self,
        key: str,
        limit: int,
        window: int,
    ) -> bool:
        """Record a request attempt and decide whether it is allowed.

        Implements a sliding window over accepted attempts. Inactive keys are
        reclaimed incrementally during subsequent attempts, including rejected
        attempts. Each key should use a consistent window. Calls on one event
        loop run atomically because this method contains no suspension points.

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
        now = monotonic()
        self.__ticks += 1
        if self.__ticks >= self._GC_INTERVAL:
            self.__ticks = 0
            self.__gc(now)

        if limit <= 0:
            return False

        entry = self.__storage.get(key)
        if entry is None:
            entry = _RateLimitBucket(now + window)
            self.__storage[key] = entry
            self.__keys.append(key)
        bucket = entry.timestamps
        cutoff = now - window

        # Discard accepted attempts outside this key's sliding window.
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= limit:
            entry.expires_at = bucket[-1] + window
            return False

        bucket.append(now)
        entry.expires_at = now + window
        return True

    def __gc(self, now: float) -> None:
        """Inspect the next group of keys and remove expired buckets.

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
                del storage[key]
            else:
                keys.append(key)

