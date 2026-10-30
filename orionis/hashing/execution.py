from orionis.support.concurrency import BoundedExecutor

# Shared across Argon2 and bcrypt instances. Running work retains its permit
# until the native function finishes, including when its caller is cancelled.
HASH_WORKERS = BoundedExecutor(2, max_pending=14, name="orionis-hash")
