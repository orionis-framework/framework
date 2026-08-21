from pathlib import Path
from typing import Any, TYPE_CHECKING
import jinja2
from orionis.view.cache import OrionisBytecodeCache
from orionis.view.contracts.environment import IViewEnvironment
from orionis.view.exceptions import ViewException
from orionis.foundation.config.view.entities.view import View as _ViewConfig
from orionis.foundation.contracts.application import IApplication

if TYPE_CHECKING:
    from collections.abc import Callable

class ViewEnvironment(IViewEnvironment):
    """
    Encapsulate and configure a Jinja2 :class:`Environment` instance.

    This is the single authorised class for configuring the underlying
    template engine.  All loaders, caches, globals, filters, tests and
    extensions must be registered through the public methods of this class.

    The Jinja2 :class:`Environment` is built once during construction and
    stored internally; no other class may access it directly except through
    :meth:`getJinjaEnvironment`.
    """

    # ruff: noqa: ANN401, TC001

    __slots__ = ("_jinja_env",)

    def __init__(self, app: IApplication) -> None:
        """
        Build the Jinja2 environment from the application view configuration.

        Parameters
        ----------
        app : IApplication
            Application container used to read view configuration and resolve
            the base path for relative template directories.

        Returns
        -------
        None
        """
        # Resolve and normalise configuration
        _raw: dict = app.config("view")
        _config: _ViewConfig = (
            _ViewConfig(**_raw) if isinstance(_raw, dict) else _raw
        )

        # Build loaders; resolve relative paths against the application base
        _base: Path = app.basePath
        _loaders: list[jinja2.FileSystemLoader] = [
            jinja2.FileSystemLoader(
                searchpath=str(
                    _base / path if not Path(path).is_absolute() else Path(path),
                ),
            )
            for path in _config.paths
        ]
        _loader: jinja2.BaseLoader = (
            jinja2.ChoiceLoader(_loaders) if len(_loaders) > 1 else _loaders[0]
        )

        # Optional bytecode cache for production deployments
        _bytecode_cache: jinja2.BytecodeCache | None = None
        if _config.cache_path is not None:
            _cache_path: Path = Path(_config.cache_path)
            _cache_dir: Path = (
                _base / _cache_path if not _cache_path.is_absolute() else _cache_path
            )
            _cache_dir.mkdir(parents=True, exist_ok=True)
            _bytecode_cache = OrionisBytecodeCache(str(_cache_dir))

        # Async rendering is not configurable: the engine only ever calls
        # render_async and every template global is awaited by Jinja2.
        self._jinja_env: jinja2.Environment = jinja2.Environment(
            loader=_loader,
            enable_async=True,
            autoescape=_config.autoescape,  # noqa: S701
            auto_reload=_config.auto_reload,
            cache_size=_config.cache_size,
            bytecode_cache=_bytecode_cache,
            undefined=jinja2.Undefined,
            keep_trailing_newline=True,
        )

    def addGlobal(self, name: str, value: Any) -> None:
        """
        Register a global variable or callable in all templates.

        Parameters
        ----------
        name : str
            Identifier used to reference the value inside templates.
        value : Any
            Value or callable to expose as a template global.

        Returns
        -------
        None
        """
        self._jinja_env.globals[name] = value

    def addFilter(self, name: str, callback: Callable) -> None:
        """
        Register a filter callable that templates can apply with ``|``.

        Parameters
        ----------
        name : str
            Filter name referenced inside template expressions (e.g. ``| slug``).
        callback : Callable
            Function applied to the piped value.

        Returns
        -------
        None
        """
        self._jinja_env.filters[name] = callback

    def addTest(self, name: str, callback: Callable) -> None:
        """
        Register a test callable used in Jinja2 ``is`` expressions.

        Parameters
        ----------
        name : str
            Test name referenced inside template ``is`` expressions.
        callback : Callable
            Function receiving the tested value and returning a bool.

        Returns
        -------
        None
        """
        self._jinja_env.tests[name] = callback

    def addExtension(self, extension: Any) -> None:
        """
        Register a Jinja2 extension class with the environment.

        Parameters
        ----------
        extension : Any
            A Jinja2 :class:`Extension` subclass or its dotted import path.

        Returns
        -------
        None

        Raises
        ------
        ViewException
            When the extension cannot be registered by Jinja2.
        """
        try:
            self._jinja_env.add_extension(extension)
        except Exception as exc:
            _name: str = getattr(extension, "__name__", str(extension))
            error_msg: str = (
                f"Failed to register Jinja2 extension '{_name}': {exc}"
            )
            raise ViewException(error_msg) from exc

    def getJinjaEnvironment(self) -> jinja2.Environment:
        """
        Return the configured Jinja2 :class:`Environment` instance.

        Returns
        -------
        jinja2.Environment
            The internal Jinja2 environment.  Treat as read-only outside
            this class; all mutations must flow through the typed helpers.
        """
        return self._jinja_env
