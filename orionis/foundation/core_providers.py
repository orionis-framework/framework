from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.container.contracts.service_provider import IServiceProvider

CORE_PROVIDER_METADATA: tuple[tuple[str, str], ...] = (
    ("orionis.auth.provider", "AuthProvider"),
    ("orionis.cache.provider", "CacheProvider"),
    ("orionis.failure.provider", "CatchProvider"),
    ("orionis.database.provider", "ConnectionManagerProvider"),
    ("orionis.encrypter.provider", "EncrypterProvider"),
    ("orionis.hashing.provider", "HashProvider"),
    ("orionis.localization.provider", "LocalizationProvider"),
    ("orionis.logging.provider", "LoggerProvider"),
    ("orionis.mail.provider", "MailProvider"),
    ("orionis.orm.provider", "QueryBuilderProvider"),
    ("orionis.console.reactor_provider", "ReactorProvider"),
    ("orionis.http.routes.provider", "RouterProvider"),
    ("orionis.console.scheduler_provider", "ScheduleProvider"),
    ("orionis.database.schema_provider", "SchemaProvider"),
    ("orionis.storage.provider", "StorageProvider"),
    ("orionis.test.provider", "TestingProvider"),
    ("orionis.view.provider", "ViewServiceProvider"),
)

def get_core_providers_mapping() -> tuple[type[IServiceProvider], ...]:
    """Load the built-in provider classes in registration order.

    Returns
    -------
    tuple[type[IServiceProvider], ...]
        Provider classes whose modules are cached by the import system.
    """
    return tuple(
        getattr(import_module(module), name) for module, name in CORE_PROVIDER_METADATA
    )

def __getattr__(name: str) -> object:
    """Expose the built-in provider tuple on its first explicit access.

    Parameters
    ----------
    name : str
        Attribute requested from this module.

    Returns
    -------
    object
        Cached provider tuple or an exported provider class.

    Raises
    ------
    AttributeError
        If the attribute is not one of the declared exports.
    """
    if name == "CORE_PROVIDERS":
        value = get_core_providers_mapping()
    else:
        for module, attribute in CORE_PROVIDER_METADATA:
            if name == attribute:
                value = getattr(import_module(module), attribute)
                break
        else:
            message = f"module {__name__!r} has no attribute {name!r}"
            raise AttributeError(message)
    globals()[name] = value
    return value

def __dir__() -> list[str]:
    """List loaded attributes and provider exports.

    Returns
    -------
    list[str]
        Sorted names including the deferred provider tuple.
    """
    return sorted(
        globals().keys()
        | {"CORE_PROVIDERS"}
        | {name for _, name in CORE_PROVIDER_METADATA},
    )
