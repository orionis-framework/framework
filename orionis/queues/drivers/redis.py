from typing import TYPE_CHECKING
from uuid import uuid4
import msgspec
from redis.asyncio import Redis
from redis.exceptions import RedisError
from orionis.foundation.config.queue import Redis as RedisConfig
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.entities.reserved_job import ReservedJob
from orionis.queues.exceptions import QueueStorageError
from orionis.queues.functions import current_time, validate_name, validate_seconds

if TYPE_CHECKING:
    from orionis.queues.entities.envelope import JobEnvelope

_ENCODER = msgspec.json.Encoder()
_RESERVATION_FIELDS = 3

# Validate key types before any transition can remove persisted queue state.
_CHECK_TYPES = """
local expected = {'zset', 'zset', 'hash', 'hash', 'hash'}
for index, key in ipairs(KEYS) do
    local actual = redis.call('TYPE', key)['ok']
    if actual ~= 'none' and actual ~= expected[index] then
        return redis.error_reply('Queue key has invalid Redis type')
    end
end
"""

# Store the envelope and availability together without exposing partial state.
_PUSH = _CHECK_TYPES + """
if redis.call('HEXISTS', KEYS[3], ARGV[1]) == 1 then return 0 end
redis.call('HSET', KEYS[3], ARGV[1], ARGV[2])
redis.call('HSET', KEYS[4], ARGV[1], 0)
redis.call('ZADD', KEYS[1], ARGV[3], ARGV[1])
return 1
"""

# Reclaim expired leases and move one due job into an owned reservation.
_RESERVE = _CHECK_TYPES + """
local expired = redis.call('ZRANGEBYSCORE', KEYS[2], '-inf', ARGV[1],
                           'LIMIT', 0, 100)
local due = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, 1)
local id = due[1] or expired[1]
if not id then return {} end
local payload = redis.call('HGET', KEYS[3], id)
if not payload then return redis.error_reply('Queue payload is missing') end
if not redis.call('HGET', KEYS[4], id) then
    return redis.error_reply('Queue attempt counter is missing')
end
local attempts = redis.call('HINCRBY', KEYS[4], id, 1)
for _, expired_id in ipairs(expired) do
    redis.call('ZREM', KEYS[2], expired_id)
    redis.call('HDEL', KEYS[5], expired_id)
    redis.call('ZADD', KEYS[1], ARGV[1], expired_id)
end
redis.call('ZREM', KEYS[1], id)
redis.call('HSET', KEYS[5], id, ARGV[3])
redis.call('ZADD', KEYS[2], ARGV[2], id)
return {id, payload, attempts}
"""

# Release only a token that still owns an unexpired lease.
_RELEASE = _CHECK_TYPES + """
local lease = redis.call('ZSCORE', KEYS[2], ARGV[1])
if redis.call('HGET', KEYS[5], ARGV[1]) ~= ARGV[2]
   or not lease or tonumber(lease) <= tonumber(ARGV[3]) then return 0 end
redis.call('ZREM', KEYS[2], ARGV[1])
redis.call('HDEL', KEYS[5], ARGV[1])
redis.call('ZADD', KEYS[1], ARGV[4], ARGV[1])
return 1
"""

# Remove only a token that still owns an unexpired lease.
_DELETE = _CHECK_TYPES + """
local lease = redis.call('ZSCORE', KEYS[2], ARGV[1])
if redis.call('HGET', KEYS[5], ARGV[1]) ~= ARGV[2]
   or not lease or tonumber(lease) <= tonumber(ARGV[3]) then return 0 end
redis.call('ZREM', KEYS[2], ARGV[1])
redis.call('HDEL', KEYS[3], ARGV[1])
redis.call('HDEL', KEYS[4], ARGV[1])
redis.call('HDEL', KEYS[5], ARGV[1])
return 1
"""

# Remove a queue's complete state and report its previous number of jobs.
_CLEAR = """
local count = redis.call('HLEN', KEYS[3])
redis.call('DEL', unpack(KEYS))
return count
"""

class RedisQueueDriver(IQueueDriver):
    """Persist delayed jobs and fenced reservations through atomic Lua scripts."""

    __slots__ = ("_client", "_owns_client", "_prefix")

    def __init__(
        self,
        config: RedisConfig | None = None,
        *,
        client: Redis | None = None,
    ) -> None:
        """
        Configure a lazy Redis transport and queue key namespace.

        Parameters
        ----------
        config : RedisConfig | None, optional
            Validated host, port, database, password, and namespace settings.
            Use the configuration entity's environment defaults when omitted.
        client : Redis or None, optional
            Externally owned async client, primarily for explicit test fakes.

        Returns
        -------
        None
            Initialize a lazy transport without opening network connections.

        Raises
        ------
        QueueStorageError
            If the configuration type or queue namespace is invalid.
        TypeError
            If an environment default has an invalid type.
        ValueError
            If an environment default fails its configuration validation.
        """
        settings = RedisConfig() if config is None else config
        if not isinstance(settings, RedisConfig):
            message = "Redis queue settings must be a Redis configuration entity."
            raise QueueStorageError(message)
        prefix = settings.prefix
        if not isinstance(prefix, str) or not prefix or "{" in prefix or "}" in prefix:
            message = "Redis queue prefixes must be nonempty without braces."
            raise QueueStorageError(message)
        self._prefix = prefix
        self._owns_client = client is None
        self._client = client if client is not None else Redis(
            host=settings.endpoint,
            port=settings.port,
            db=settings.db,
            password=settings.password,
        )

    def _keys(self, queue: str) -> tuple[str, ...]:
        """
        Return colocated keys for one logical queue.

        Parameters
        ----------
        queue : str
            Logical queue name used as a Redis hash tag.

        Returns
        -------
        tuple of str
            Ready, reserved, envelope, attempts, and token keys.
        """
        validate_name(queue, "queue")
        base = f"{self._prefix}:{{{queue}}}"
        return tuple(
            f"{base}:{suffix}"
            for suffix in ("ready", "reserved", "payloads", "attempts", "tokens")
        )

    async def _executeScript(
        self,
        script: str,
        keys: tuple[str, ...],
        arguments: tuple[str | bytes | float, ...],
    ) -> object:
        """
        Execute one atomic Redis transition and translate transport errors.

        Parameters
        ----------
        script : str
            Framework-owned Lua transition source.
        keys : tuple of str
            Redis keys touched by the transition.
        arguments : tuple
            Bound transition arguments.

        Returns
        -------
        object
            Redis reply supplied by the executed script.

        Raises
        ------
        QueueStorageError
            If Redis cannot perform the transition.
        """
        try:
            return await self._client.eval(script, len(keys), *keys, *arguments)
        except RedisError as exception:
            message = "Unable to execute the atomic Redis queue transition."
            raise QueueStorageError(message) from exception

    async def push(self, envelope: JobEnvelope, delay: float = 0) -> str:
        """
        Store an envelope and its availability atomically.

        Parameters
        ----------
        envelope : JobEnvelope
            Immutable serialized job configuration and state.
        delay : float, optional
            Seconds before the job becomes available.

        Returns
        -------
        str
            Persisted job identifier.

        Raises
        ------
        QueueStorageError
            If the identifier already exists or persistence fails.
        """
        delay = validate_seconds(delay, "delay")
        result = await self._executeScript(
            _PUSH, self._keys(envelope.queue),
            (envelope.id, _ENCODER.encode(envelope), current_time() + delay),
        )
        if result != 1:
            message = f"Queued job {envelope.id!r} already exists."
            raise QueueStorageError(message)
        return envelope.id

    async def reserve(
        self, queues: tuple[str, ...], retry_after: float,
    ) -> ReservedJob | None:
        """
        Claim one due job in queue priority order.

        Parameters
        ----------
        queues : tuple of str
            Logical queues ordered from highest to lowest priority.
        retry_after : float
            Lease duration in seconds.

        Returns
        -------
        ReservedJob or None
            Acquired reservation, or no available job.

        Raises
        ------
        QueueStorageError
            If Redis returns invalid reservation data.
        """
        retry_after = validate_seconds(retry_after, "retry_after", positive=True)
        for queue in queues:
            now = current_time()
            reserved_until = now + retry_after
            token = uuid4().hex
            result = await self._executeScript(
                _RESERVE, self._keys(queue), (now, reserved_until, token),
            )
            if result == []:
                continue
            if (
                not isinstance(result, list) or len(result) != _RESERVATION_FIELDS
                or not isinstance(result[0], bytes)
                or not isinstance(result[1], bytes)
                or not isinstance(result[2], int) or result[2] < 1
            ):
                message = "Redis returned an invalid queue reservation."
                raise QueueStorageError(message)
            try:
                job_id = result[0].decode("utf-8")
            except UnicodeDecodeError as exception:
                message = "Redis returned an invalid job identifier."
                raise QueueStorageError(message) from exception
            return ReservedJob(
                id=job_id, payload=result[1], queue=queue,
                attempts=result[2], token=token, reserved_until=reserved_until,
            )
        return None

    async def release(self, reserved: ReservedJob, delay: float = 0) -> bool:
        """
        Release a currently owned reservation with optional delay.

        Parameters
        ----------
        reserved : ReservedJob
            Reservation owned by the releasing worker.
        delay : float, optional
            Seconds before the job becomes available again.

        Returns
        -------
        bool
            Whether an owned, unexpired reservation was released.
        """
        delay = validate_seconds(delay, "delay")
        now = current_time()
        return await self._executeScript(
            _RELEASE, self._keys(reserved.queue),
            (reserved.id, reserved.token, now, now + delay),
        ) == 1

    async def delete(self, reserved: ReservedJob) -> bool:
        """
        Acknowledge a currently owned reservation atomically.

        Parameters
        ----------
        reserved : ReservedJob
            Reservation owned by the acknowledging worker.

        Returns
        -------
        bool
            Whether an owned, unexpired reservation was removed.
        """
        return await self._executeScript(
            _DELETE, self._keys(reserved.queue),
            (reserved.id, reserved.token, current_time()),
        ) == 1

    async def size(self, queue: str) -> int:
        """
        Count ready, delayed, and reserved jobs in one queue.

        Parameters
        ----------
        queue : str
            Logical queue whose jobs are counted.

        Returns
        -------
        int
            Total persisted jobs in the queue.
        """
        try:
            return await self._client.hlen(self._keys(queue)[2])
        except RedisError as exception:
            message = "Unable to count Redis queue jobs."
            raise QueueStorageError(message) from exception

    async def clear(self, queue: str) -> int:
        """
        Remove every job and reservation in one queue atomically.

        Parameters
        ----------
        queue : str
            Logical queue whose jobs are removed.

        Returns
        -------
        int
            Number of removed jobs, including active reservations.
        """
        result = await self._executeScript(_CLEAR, self._keys(queue), ())
        if not isinstance(result, int):
            message = "Redis returned an invalid queue size."
            raise QueueStorageError(message)
        return result

    async def close(self) -> None:
        """
        Close the transport only when this driver owns its Redis client.

        Returns
        -------
        None
            Release driver-owned pooled Redis connections.
        """
        if self._owns_client:
            await self._client.aclose()
