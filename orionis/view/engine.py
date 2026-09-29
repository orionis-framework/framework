from typing import Any
import jinja2
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.environment import IViewEnvironment
from orionis.view.exceptions import ViewRenderException, ViewTemplateNotFoundException

# Template extension appended when the identifier carries no extension
_DEFAULT_EXT: str = ".html"

# Memoised template identifier to loader path mapping; the set of template
# names an application renders is bounded and stable at runtime.
# Lock-free on purpose: entries are pure functions of their key, so a racing
# writer can only store the value another thread would have computed.
_PATH_CACHE: dict[str, str] = {}

class Jinja2Engine(IViewEngine):
    """
    Jinja2-based implementation of :class:`IViewEngine`.

    Converts dot-notation template names to filesystem paths and delegates
    all rendering to Jinja2's async rendering pipeline (``render_async``).
    The synchronous ``render`` method of Jinja2 is **never** called from
    this class.
    """

    # ruff: noqa: TC001

    __slots__ = ("_environment", "_jinja")

    def __init__(self, environment: IViewEnvironment) -> None:
        """
        Initialise the engine with the configured view environment.

        Parameters
        ----------
        environment : IViewEnvironment
            View environment providing the configured Jinja2
            :class:`Environment` instance.

        Returns
        -------
        None
        """
        self._environment: IViewEnvironment = environment
        # The environment instance is built once and mutated in place, so the
        # reference stays valid for the whole application lifetime.
        self._jinja: jinja2.Environment = environment.getJinjaEnvironment()

    async def render(self, template: str, context: dict[str, Any]) -> str:
        """
        Render a template asynchronously using Jinja2.

        Dot-notation identifiers are converted to slash-delimited paths
        with a ``.html`` suffix automatically appended when the name
        carries no extension (e.g. ``'users.index'`` → ``'users/index.html'``).

        Parameters
        ----------
        template : str
            Template identifier using dot notation or a direct relative
            path.  A ``.html`` suffix is appended when absent.
        context : dict[str, Any]
            Variables made available inside the template during rendering.

        Returns
        -------
        str
            Rendered HTML string.

        Raises
        ------
        ViewTemplateNotFoundException
            When the template file cannot be located by the configured
            loaders.
        ViewRenderException
            When Jinja2 raises any error during rendering.
        """
        # Normalise template identifier to a filesystem path
        _path: str = _PATH_CACHE.get(template) or self._normalisePath(template)

        _jinja: jinja2.Environment = self._jinja

        try:
            _tmpl: jinja2.Template = _jinja.get_template(_path)
        except jinja2.TemplateNotFound as exc:
            error_msg: str = (
                f"Template not found: '{_path}'.  "
                f"Check the configured view paths."
            )
            raise ViewTemplateNotFoundException(error_msg) from exc

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
            :meth:`jinja2.Environment.get_template`.
        """
        # Preserve direct paths (e.g. 'partials/nav.html')
        _path: str = (
            template if "/" in template else template.replace(".", "/")
        )
        # Append default extension only when none is present
        if "." not in _path.rsplit("/", 1)[-1]:
            _path += _DEFAULT_EXT
        _PATH_CACHE[template] = _path
        return _path
