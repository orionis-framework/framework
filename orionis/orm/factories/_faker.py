from importlib import import_module
from locale import normalize
from orionis.foundation.application import Application
from orionis.orm.factories.exceptions import FactoryDependencyException
from orionis.orm.factories.fake import Fake

def _application_locale() -> str:
    """
    Read the configured locale without initializing an application.

    Returns
    -------
    str
        Current ``app.locale``, or English if configuration is unavailable.
    """
    app = Application.current()
    if app is None:
        return "en_US"
    try:
        locale = app.config("app.locale")
    except RuntimeError:
        # Application.config() is unavailable before configuration is loaded.
        return "en_US"
    return locale if isinstance(locale, str) and locale.strip() else "en_US"

def create_faker(locale: str | None, seed: int | None) -> Fake:
    """
    Create the optional provider with an independent random generator.

    Parameters
    ----------
    locale : str or None
        Explicit locale override, or None to read ``app.locale``.
        Unsupported locales fall back to English (``en_US``).
    seed : int or None
        Reproducible seed, or system entropy when omitted.

    Returns
    -------
    Fake
        Typed Orionis facade over the instance-local data provider.

    Raises
    ------
    FactoryDependencyException
        If the optional factories extra is not installed.
    """
    try:
        provider = import_module("faker")
    except ModuleNotFoundError as exc:
        if exc.name != "faker":
            raise
        error_msg = "Install factory support with: uv add 'orionis[factories]'"
        raise FactoryDependencyException(error_msg) from exc
    requested = _application_locale() if locale is None else locale
    normalized = normalize(requested.replace("-", "_")).split(".")[0]
    available = import_module("faker.config").AVAILABLE_LOCALES
    selected = normalized if normalized in available else "en_US"
    fake = provider.Faker(locale=selected)
    # Calling this even for None detaches Faker's shared random generator.
    fake.seed_instance(seed)
    return Fake(fake)
