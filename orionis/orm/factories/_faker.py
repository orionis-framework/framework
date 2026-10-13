from locale import normalize
from faker import Faker
from faker.config import AVAILABLE_LOCALES
from orionis.foundation.application import Application
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
    Create the data provider with an independent random generator.

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

    """
    requested = _application_locale() if locale is None else locale
    normalized = normalize(requested.replace("-", "_")).split(".")[0]
    selected = normalized if normalized in AVAILABLE_LOCALES else "en_US"
    fake = Faker(locale=selected)
    # Calling this even for None detaches Faker's shared random generator.
    fake.seed_instance(seed)
    return Fake(fake)
