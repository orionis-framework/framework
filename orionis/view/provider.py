from typing import Any
from orionis.container.providers.service_provider import ServiceProvider
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.environment import IViewEnvironment
from orionis.view.contracts.factory import IViewFactory
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment
from orionis.view.extensions import CsrfExtension
from orionis.view.factory import ViewFactory
from orionis.view.filters import (
    _filter_json,
    _filter_markdown,
)
from orionis.view.globals import (
    _global_app,
    _global_asset,
    _global_cache,
    _global_choice,
    _global_collect,
    _global_config,
    _global_csrf_field,
    _global_csrf_token,
    _global_dump,
    _global_decrypt,
    _global_encrypt,
    _global_framework_version,
    _global_locale,
    _global_locales,
    _global_now,
    _global_old,
    _global_python_version,
    _global_request,
    _global_route,
    _global_secure_asset,
    _global_secure_url,
    _global_session,
    _global_stringable,
    _global_today,
    _global_trans,
    _global_url,
)
from orionis.support.facades.view import View as ViewFacade

class ViewServiceProvider(ServiceProvider):
    """
    Register and boot the view system into the application container.

    Registration phase
    ------------------
    Binds :class:`IViewEnvironment` → :class:`ViewEnvironment`,
    :class:`IViewEngine` → :class:`Jinja2Engine`, and
    :class:`IViewFactory` → :class:`ViewFactory` as singletons.

    Boot phase
    ----------
    Registers template globals, filters, and extensions with the
    :class:`ViewEnvironment` singleton, then pins the :class:`View`
    facade for zero-resolution access on the hot path.
    """

    def register(self) -> None:
        """
        Bind view services as singletons in the application container.

        Returns
        -------
        None
        """
        # Environment wraps and owns the Jinja2 Environment instance
        self.app.singleton(IViewEnvironment, ViewEnvironment)

        # Engine uses the environment to perform async rendering
        self.app.singleton(IViewEngine, Jinja2Engine)

        # Factory is the public entry-point for controllers
        self.app.singleton(IViewFactory, ViewFactory)

    async def boot(self) -> None:
        """
        Register globals, filters, and extensions; then pin the facade.

        Returns
        -------
        None
        """
        # Resolve the shared environment singleton
        _env: IViewEnvironment = await self.app.make(IViewEnvironment)

        # Build every template global bound to the application instance
        _globals: dict[str, Any] = {
            "app": _global_app(self.app),
            "asset": _global_asset(self.app),
            "cache": _global_cache(self.app),
            "choice": _global_choice(),
            "collect": _global_collect(),
            "config": _global_config(self.app),
            "csrf_field": _global_csrf_field(self.app),
            "csrf_token": _global_csrf_token(self.app),
            "dump": _global_dump(),
            "decrypt": _global_decrypt(self.app),
            "encrypt": _global_encrypt(self.app),
            "framework_version": _global_framework_version(),
            "locale": _global_locale(),
            "locales": _global_locales(),
            "now": _global_now(),
            "old": _global_old(self.app),
            "python_version": _global_python_version(),
            "request": _global_request(self.app),
            "route": _global_route(self.app),
            "secure_asset": _global_secure_asset(self.app),
            "secure_url": _global_secure_url(self.app),
            "session": _global_session(self.app),
            "stringable": _global_stringable(),
            "today": _global_today(),
            "url": _global_url(self.app),
        }

        # ``__`` is the conventional alias of the translation global
        _translate = _global_trans()
        _globals["trans"] = _translate
        _globals["__"] = _translate

        # Register all template globals
        for _name, _value in _globals.items():
            _env.addGlobal(_name, _value)

        # Build every template filter
        _filters: dict[str, Any] = {
            "json": _filter_json(),
            "markdown": _filter_markdown(),
        }

        # Register all template filters
        for _name, _callback in _filters.items():
            _env.addFilter(_name, _callback)

        # Register all Jinja2 extensions
        _extensions: tuple[Any, ...] = (
            CsrfExtension,
        )

        for _extension in _extensions:
            _env.addExtension(_extension)

        # Pin the facade for direct attribute access without DI overhead
        await ViewFacade.pin()
