# ruff: noqa: TC001
# Keep constructor annotations available to runtime dependency inspection.
"""Render templates asynchronously through the configured Jinja2 environment."""

from collections import OrderedDict
from threading import Lock, RLock
from typing import Any, Self
from weakref import ref
import jinja2
from orionis.support.concurrency import BoundedExecutor
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.environment import IViewEnvironment
from orionis.view.exceptions import ViewRenderException, ViewTemplateNotFoundException

# Template extension appended when the identifier carries no extension
_DEFAULT_EXT: str = ".html"
"""Template extension appended when the identifier carries no extension."""

# Store recently normalized template identifiers and their loader paths.
_PATH_CACHE: OrderedDict[str, str] = OrderedDict()
"""Store recently normalized template identifiers and their loader paths."""
_PATH_CACHE_MAX = 1024
"""Path cache max value used by ``engine``."""
_PATH_CACHE_LOCK = Lock()
"""Synchronization primitive controlling access to path cache lock."""
_TEMPLATE_WORKERS = BoundedExecutor(2, max_pending=64, name="orionis-template")
"""Template workers used by ``engine``."""


class Jinja2Engine(IViewEngine):
    """
    Render templates with Jinja2 through the view-engine contract.

    Converts dot-notation template names to filesystem paths and delegates
    all rendering to Jinja2's async rendering pipeline (``render_async``).
    The synchronous ``render`` method of Jinja2 is **never** called from
    this class.
    """

    __slots__ = ("_environment", "_jinja", "_load_lock")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self: Self, environment: IViewEnvironment) -> None:
        """
        Initialise the engine with the configured view environment.

        Parameters
        ----------
        environment : orionis.view.contracts.environment.IViewEnvironment
            View environment providing the configured Jinja2
            ``Environment`` instance.

        Returns
        -------
        None
            No return value.
        """
        self._environment: IViewEnvironment = environment
        """
        View environment providing the configured Jinja2 ``Environment``
        instance.
        """
        # The environment instance is built once and mutated in place, so the
        # reference stays valid for the whole application lifetime.
        self._jinja: jinja2.Environment = environment.getJinjaEnvironment()
        """
        The environment instance is built once and mutated in place, so the
        reference stays valid for the whole application lifetime.
        """
        self._load_lock = RLock()
        """Synchronization primitive controlling access to load lock."""

    def _load(self: Self, path: str) -> jinja2.Template:
        """
        Serialize loader and compiler access to this environment.

        Parameters
        ----------
        path : str
            Template path resolved within the configured environment.

        Returns
        -------
        ``jinja2.Template``
            Loaded and compiled template from the environment cache or loader.
        """
        with self._load_lock:
            return self._jinja.get_template(path)

    async def warmup(self: Self, *templates: str) -> None:
        """
        Compile known templates before serving requests, without rendering globals.

        Parameters
        ----------
        *templates : str
            Template identifiers, including known includes and parent templates.

        Returns
        -------
        None
            No return value.
        """
        for template in templates:
            await _TEMPLATE_WORKERS.run(self._load, self._normalisePath(template))

    async def render(self: Self, template: str, context: dict[str, Any]) -> str:
        """
        Render a template asynchronously using Jinja2.

        Interpret identifiers without ``/`` as dot notation, including their
        final segment (``'users.index'`` becomes ``'users/index.html'``).
        Include ``/`` to pass a relative filename with an extension directly.

        Parameters
        ----------
        template : str
            Template identifier using dot notation or a direct relative
            path.  A ``.html`` suffix is appended when absent.
        context : dict[str, typing.Any]
            Variables made available inside the template during rendering.

        Returns
        -------
        str
            Rendered HTML string.

        Raises
        ------
        orionis.view.exceptions.ViewTemplateNotFoundException
            When the template file cannot be located by the configured
            loaders.
        orionis.view.exceptions.ViewRenderException
            When Jinja2 raises a template error while loading or rendering.
        orionis.support.concurrency.WorkQueueFullError
            When the bounded template workers cannot admit a cold load.
        """
        # Normalise template identifier to a filesystem path
        _path: str = _PATH_CACHE.get(template) or self._normalisePath(template)

        _jinja: jinja2.Environment = self._jinja

        try:
            _tmpl = None
            if (
                type(_jinja) is jinja2.Environment
                and not _jinja.auto_reload
                and _jinja.cache is not None
                and _jinja.loader is not None
            ):
                # Match Jinja's cache identity; clearing its cache remains effective.
                _tmpl = _jinja.cache.get((ref(_jinja.loader), _path))
            if _tmpl is None:
                _tmpl = await _TEMPLATE_WORKERS.run(self._load, _path)
        except jinja2.TemplateNotFound as exc:
            error_msg: str = (  # NOSONAR(S1110) - Preserve multiline grouping.
                f"Template not found: '{_path}'.  Check the configured view paths."
            )
            raise ViewTemplateNotFoundException(error_msg) from exc
        except jinja2.TemplateError as exc:
            error_msg = f"Load error in template '{_path}': {exc}"
            raise ViewRenderException(error_msg) from exc

        try:
            return await _tmpl.render_async(**context)
        except jinja2.TemplateError as exc:
            error_msg = f"Render error in template '{_path}': {exc}"
            raise ViewRenderException(error_msg) from exc

    @staticmethod
    def _normalisePath(template: str) -> str:
        """
        Convert a template identifier to a Jinja2-loader-compatible path.

        Rules applied in order
        ----------------------
        1. If the identifier already contains ``/`` it is treated as a direct
           path and returned unchanged (except for extension injection).
        2. Otherwise dot separators are converted to slashes.
        3. A ``'.html'`` extension is appended when no file extension is
           present.

        Parameters
        ----------
        template : str
            Raw template identifier supplied by the caller.

        Returns
        -------
        str
            Normalised template path suitable for
            ``jinja2.Environment.get_template``.
        """
        # Preserve direct paths (e.g. 'partials/nav.html')
        _path: str = template if "/" in template else template.replace(".", "/")
        # Append default extension only when none is present
        if "." not in _path.rsplit("/", 1)[-1]:
            _path += _DEFAULT_EXT
        # Insert a new path and discard the oldest entry when full.
        with _PATH_CACHE_LOCK:
            cached = _PATH_CACHE.get(template)
            if cached is not None:
                return cached
            if len(_PATH_CACHE) >= _PATH_CACHE_MAX:
                _PATH_CACHE.popitem(last=False)
            _PATH_CACHE[template] = _path
            return _path
