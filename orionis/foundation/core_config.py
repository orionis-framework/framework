from dataclasses import asdict
from importlib import import_module
from types import MappingProxyType

# ruff: noqa: E501
_CONFIG_ENTITIES: tuple[tuple[str, str, str], ...] = (
    ("app", "orionis.foundation.config.app.entities.app", "App"),
    ("auth", "orionis.foundation.config.auth.entities.auth", "Auth"),
    ("cache", "orionis.foundation.config.cache.entities.cache", "Cache"),
    ("database", "orionis.foundation.config.database.entities.database", "Database"),
    ("filesystems", "orionis.foundation.config.filesystems.entitites.filesystems", "Filesystems"),
    ("hashing", "orionis.foundation.config.hashing.entities.hashing", "Hashing"),
    ("http", "orionis.foundation.config.http.entitites.http", "HTTP"),
    ("logging", "orionis.foundation.config.logging.entities.logging", "Logging"),
    ("mail", "orionis.foundation.config.mail.entities.mail", "Mail"),
    ("queue", "orionis.foundation.config.queue.entities.queue", "Queue"),
    ("scheduler", "orionis.foundation.config.scheduler.entities.scheduler", "Scheduler"),
    ("session", "orionis.foundation.config.session.entities.session", "Session"),
    ("testing", "orionis.foundation.config.testing.entities.testing", "Testing"),
    ("view", "orionis.foundation.config.view.entities.view", "View"),
)

def get_core_config_mapping() -> MappingProxyType:
    """Build independent configuration defaults from their declared entities.

    Returns
    -------
    MappingProxyType
        Read-only outer mapping containing newly created nested configuration
        dictionaries. Entity modules are imported on the first call.
    """
    return MappingProxyType(
        {
            key: asdict(getattr(import_module(module), name)())
            for key, module, name in _CONFIG_ENTITIES
        },
    )

def __getattr__(name: str) -> object:
    """Build and cache the compatibility configuration export on first access.

    Parameters
    ----------
    name : str
        Attribute requested from this module.

    Returns
    -------
    object
        Core configuration defaults or an exported entity class.

    Raises
    ------
    AttributeError
        If the attribute is not one of the declared exports.
    """
    if name == "CORE_CONFIG":
        value = get_core_config_mapping()
    else:
        for _, module, attribute in _CONFIG_ENTITIES:
            if name == attribute:
                value = getattr(import_module(module), attribute)
                break
        else:
            message = f"module {__name__!r} has no attribute {name!r}"
            raise AttributeError(message)
    globals()[name] = value
    return value

def __dir__() -> list[str]:
    """List loaded attributes and configuration exports.

    Returns
    -------
    list[str]
        Sorted names including the deferred configuration defaults.
    """
    return sorted(
        globals().keys() | {"CORE_CONFIG"} | {name for _, _, name in _CONFIG_ENTITIES},
    )
