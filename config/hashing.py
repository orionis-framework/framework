from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.hashing import (
    Argon2,
    Bcrypt,
    Drivers,
    Hashing,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapHashing(Hashing):

    # ----------------------------------------------------------------------------------
    # driver : Drivers | str, optional
    # --- The default password hashing driver.
    # --- Defaults to the HASH_DRIVER env var or "argon2" (Argon2id) if not set.
    # ----------------------------------------------------------------------------------
    driver: Drivers | str = field(
        default_factory=lambda: Env.get("HASH_DRIVER", Drivers.ARGON2),
    )

    # ----------------------------------------------------------------------------------
    # argon2 : Argon2 | dict, optional
    # --- Cost parameters applied by the Argon2id driver.
    # --- memory is expressed in kibibytes, time is the iteration count.
    # ----------------------------------------------------------------------------------
    argon2: Argon2 | dict = field(
        default_factory=lambda: Argon2(
            memory=Env.get("ARGON_MEMORY", 65536),
            threads=Env.get("ARGON_THREADS", 4),
            time=Env.get("ARGON_TIME", 3),
        ),
    )

    # ----------------------------------------------------------------------------------
    # bcrypt : Bcrypt | dict, optional
    # --- Cost parameters applied by the bcrypt driver.
    # --- rounds is the base-2 logarithm of the iteration count (4 to 31).
    # ----------------------------------------------------------------------------------
    bcrypt: Bcrypt | dict = field(
        default_factory=lambda: Bcrypt(
            rounds=Env.get("BCRYPT_ROUNDS", 12),
        ),
    )
