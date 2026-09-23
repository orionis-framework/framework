import json
import platform
from pathlib import Path
from typing import ClassVar
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.contracts.directory import IDirectory
from orionis.foundation.directory import Directory
from orionis.http.default.assistance import build_chatgpt_url
from orionis.http.default.contracts.responses import IDefaultResponses
from orionis.http.enums.status import HTTPStatus
from orionis.http.request import Request
from orionis.http.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    Response,
)
from orionis.metadata import VERSION
from orionis.view.contracts.engine import IViewEngine
from orionis.support.facades.datetime import DateTime
from orionis.support.formatter.exceptions.parser import ExceptionParser

# Human-readable labels for validated HTTP status codes.
_STATUS_MESSAGES: dict[int, str] = {}
_MIN_STATUS_CODE: int = 100
_MAX_STATUS_CODE: int = 599
_FRAMEWORK_VERSION: str = f"v{VERSION}"
_PYTHON_VERSION: str = platform.python_version()
_LOCALE_CONFIG_KEY: str = "app.locale"

def _validate_status_code(status_code: int | HTTPStatus) -> int:
    """
    Validate an HTTP status before either response format is rendered.

    Parameters
    ----------
    status_code : int | HTTPStatus
        HTTP status supplied to the default error response.

    Returns
    -------
    int
        Validated status, converting an HTTPStatus member to its value.

    Raises
    ------
    TypeError
        If status_code is not an integer.
    ValueError
        If status_code is outside the range 100 to 599.
    """
    if not isinstance(status_code, int):
        error_msg = "status_code must be an integer"
        raise TypeError(error_msg)
    if not _MIN_STATUS_CODE <= status_code <= _MAX_STATUS_CODE:
        error_msg = "status_code must be between 100 and 599"
        raise ValueError(error_msg)
    return status_code.value if isinstance(status_code, HTTPStatus) else status_code

def _status_message(status_code: int) -> str:
    """Return the display label for a validated HTTP status.

    Parameters
    ----------
    status_code : int
        Validated HTTP status whose label is needed by the error template.

    Returns
    -------
    str
        Enum label or a numeric label for an unlisted status.
    """
    message = _STATUS_MESSAGES.get(status_code)
    if message is None:
        try:
            message = HTTPStatus(status_code).name.replace("_", " ").title()
        except ValueError:
            message = f"HTTP {status_code}"
        _STATUS_MESSAGES[status_code] = message
    return message

class DefaultResponses(IDefaultResponses):

    # ruff: noqa: TC001

    __slots__ = (
        "__app", "__app_locale", "__app_name", "__asset_paths",
        "__directory", "__engine", "__memory_cache",
    )

    _FAVICON_CACHE_CONTROL_AGE: str = "public, max-age=31536000, immutable"
    _FAVICON_NAME: str = "favicon.ico"
    _FONT_CONTENT_TYPE: str = "font/ttf"
    _GENERAL_CACHE_CONTROL: str = "no-cache, no-store, must-revalidate"
    _NO_CACHE_HEADERS: ClassVar[dict[str, str]] = {
        "cache-control": _GENERAL_CACHE_CONTROL,
    }

    # Only these package-owned files can be served through the reserved URL.
    ASSET_PREFIX: str = "/_orionis/assets/"
    _ASSET_BASE: str = ASSET_PREFIX.rstrip("/")
    _ASSETS_DIR: Path = Path(__file__).parent / "assets"
    _ASSET_HEADERS: ClassVar[dict[str, dict[str, str]]] = {
        name: {
            "content-type": content_type,
            "cache-control": "public, max-age=3600",
            "x-content-type-options": "nosniff",
        }
        for name, content_type in (
            ("default.css", "text/css; charset=utf-8"),
            ("default.js", "text/javascript; charset=utf-8"),
            (_FAVICON_NAME, "image/x-icon"),
            ("fonts/orbitron.ttf", _FONT_CONTENT_TYPE),
            ("fonts/share-tech-mono.ttf", _FONT_CONTENT_TYPE),
            ("fonts/fira-code.ttf", _FONT_CONTENT_TYPE),
        )
    }

    # Favicon candidates in order of preference.
    _FAVICON_CANDIDATES: ClassVar[tuple[tuple[str, dict[str, str]], ...]] = (
        (_FAVICON_NAME, {
            "content-type": "image/x-icon",
            "cache-control": _FAVICON_CACHE_CONTROL_AGE,
        }),
        ("favicon.png", {
            "content-type": "image/png",
            "cache-control": _FAVICON_CACHE_CONTROL_AGE,
        }),
        ("favicon.svg", {
            "content-type": "image/svg+xml",
            "cache-control": _FAVICON_CACHE_CONTROL_AGE,
        }),
    )
    _ROBOTS_CANDIDATES: ClassVar[tuple[tuple[str, dict[str, str]], ...]] = (
        ("robots.txt", {
            "content-type": "text/plain",
            "cache-control": "public, max-age=3600",
        }),
    )
    _SITEMAP_CANDIDATES: ClassVar[tuple[tuple[str, dict[str, str]], ...]] = (
        ("sitemap.xml", {
            "content-type": "application/xml",
            "cache-control": "public, max-age=600",
        }),
    )

    _TEMPLATES: ClassVar[dict[str, str]] = {
        "up": "__orionis__/default/up.html",
        "down": "__orionis__/default/down.html",
        "error": "__orionis__/default/error.html",
        "exception": "__orionis__/default/exception.html",
    }

    # Map the maintenance flag to the health response metadata.
    _HEALTH_STATES: ClassVar[dict[bool, tuple[HTTPStatus, str, str, str]]] = {
        False: (
            HTTPStatus.OK, "Online Application", "up",
            "state_page_200:html",
        ),
        True: (
            HTTPStatus.SERVICE_UNAVAILABLE, "Application in Maintenance", "down",
            "state_page_503:html",
        ),
    }

    def __init__(
        self,
        app: IApplication,
        directory: Directory,
        engine: IViewEngine,
    ) -> None:
        """
        Initialize instance with application and directory dependencies.

        Parameters
        ----------
        app : IApplication
            The application instance providing configuration and services.
        directory : IDirectory
            The directory service for accessing storage paths.
        engine : IViewEngine
            Official asynchronous template rendering engine.

        Returns
        -------
        None
            This constructor does not return a value.
        """
        # Store application, directory and official view engine dependencies.
        self.__app: IApplication = app
        self.__directory: IDirectory = directory
        self.__engine: IViewEngine = engine

        # Store the application name and locale.
        self.__app_name: str = self.__app.config("app.name")
        self.__app_locale: str = self.__app.config(_LOCALE_CONFIG_KEY)

        # Initialize storage for asset paths and rendered page bodies.
        self.__memory_cache: dict[str, object] = {}
        self.__asset_paths: dict[str, Path] = {}

    def __getitem__(self, key: str) -> object | None:
        """
        Retrieve a cached value by key.

        Parameters
        ----------
        key : str
            The key to look up in the cache.

        Returns
        -------
        object or None
            The cached value if found, otherwise None.
        """
        # Return the value from the memory cache for the given key
        return self.__memory_cache.get(key)

    def __setitem__(self, key: str, value: object) -> None:
        """
        Store a value in the cache with the specified key.

        Parameters
        ----------
        key : str
            The key under which to store the value.
        value : object
            The value to store in the cache.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Set the value in the memory cache for the given key
        self.__memory_cache[key] = value

    def __contains__(self, key: str) -> bool:
        """
        Check if the cache contains the specified key.

        Parameters
        ----------
        key : str
            The key to check for existence in the cache.

        Returns
        -------
        bool
            True if the key exists in the cache, False otherwise.
        """
        # Return True if the key is present in the memory cache
        return key in self.__memory_cache

    def __delitem__(self, key: str) -> None:
        """
        Remove an item from the memory cache by key.

        Parameters
        ----------
        key : str
            The key to remove from the cache.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Remove the key from the cache if present
        self.__memory_cache.pop(key, None)

    async def favicon(self) -> FileResponse | Response:
        """
        Return the favicon file response or a 404 response if not found.

        Searches for a favicon in the public storage directory using common
        favicon file names and content types. If not found, attempts to use
        the framework's internal fallback favicon. Caches the result for
        subsequent calls.

        Returns
        -------
        FileResponse or Response
            A FileResponse containing the favicon if found, otherwise a
            Response with status 404.
        """
        return await self.__publicFile(
            "favicon", self._FAVICON_CANDIDATES, "Favicon Not Found",
            fallback=self._FAVICON_CANDIDATES[0],
        )

    async def robotsTxt(self) -> FileResponse | Response:
        """
        Return the robots.txt file or a 404 response if not found.

        Search for a robots.txt file in the public storage directory. If not
        found, check for a fallback file. Cache the result for future calls.

        Returns
        -------
        FileResponse or Response
            FileResponse with robots.txt if found, otherwise Response with 404.
        """
        return await self.__publicFile(
            "robots_txt", self._ROBOTS_CANDIDATES, "Robots.txt Not Found",
            fallback=self._ROBOTS_CANDIDATES[0],
        )

    async def sitemapXml(self) -> FileResponse | Response:
        """
        Return the public sitemap.xml file, or a 404 response when absent.

        Retain the selected path and read its current metadata for each response.

        Returns
        -------
        FileResponse or Response
            FileResponse with sitemap.xml if found, otherwise Response with status 404.
        """
        return await self.__publicFile(
            "sitemap_xml", self._SITEMAP_CANDIDATES, "Sitemap Not Found",
        )

    async def __publicFile(
        self,
        key: str,
        candidates: tuple[tuple[str, dict[str, str]], ...],
        missing_message: str,
        *,
        fallback: tuple[str, dict[str, str]] | None = None,
    ) -> FileResponse | HTMLResponse:
        """Select a public file and recover when a previously selected file vanishes.

        Parameters
        ----------
        key : str
            Cache entry for the selected path and headers.
        candidates : tuple[tuple[str, dict[str, str]], ...]
            Public filenames and headers in order of preference.
        missing_message : str
            Description displayed when no candidate is available.
        fallback : tuple[str, dict[str, str]] | None, optional
            Package filename and headers used when no public file exists.

        Returns
        -------
        FileResponse | HTMLResponse
            Independent file stream or an HTML error response.
        """
        cache = self.__memory_cache
        cached = cache.get(key)
        if cached is not None:
            path, headers = cached
            response = self.__fileResponse(path, headers)
            if response is not None:
                return response
            cache.pop(key, None)

        public_storage = self.__directory.storagePublic()
        for file_name, headers in candidates:
            path = public_storage / file_name
            response = self.__fileResponse(path, headers)
            if response is not None:
                cache[key] = (path, headers)
                return response

        if fallback is not None:
            file_name, headers = fallback
            path = self._ASSETS_DIR / file_name
            response = self.__fileResponse(path, headers)
            if response is not None:
                cache[key] = (path, headers)
                return response

        return await self.error(
            HTTPStatus.NOT_FOUND, missing_message, expects_json=False,
        )

    @staticmethod
    def __fileResponse(path: Path, headers: dict[str, str]) -> FileResponse | None:
        """Build an independent response for an available regular file.

        Parameters
        ----------
        path : Path
            Candidate file whose current metadata is read by FileResponse.
        headers : dict[str, str]
            Fixed file headers including its content type.

        Returns
        -------
        FileResponse | None
            New response, or None when the file is unavailable or not regular.
        """
        try:
            return FileResponse(
                path=path, headers=headers, media_type=headers["content-type"],
            )
        except (OSError, ValueError):
            return None

    async def health(self, request: Request) -> HTMLResponse | JSONResponse:
        """
        Render the application health state as an HTML or JSON response.

        Parameters
        ----------
        request : Request
            The HTTP request object.

        Returns
        -------
        HTMLResponse or JSONResponse
            HTMLResponse with the state page content or JSONResponse with the
            application status. Status is 200 if healthy, 503 if under
            maintenance.
        """
        config_maintenance: bool = self.__app.config("app.maintenance")

        # Select constants for the current maintenance state.
        app_state, state_label, template_page, key_html = (
            self._HEALTH_STATES[config_maintenance]
        )

        if request.wantsJson():
            # Render the current health state into a response.
            return JSONResponse(
                content={"message": state_label},
                status_code=app_state,
                headers=self._NO_CACHE_HEADERS,
            )

        # Render the HTML state page and retain its encoded body.
        self.__refreshContext()
        cache = self.__memory_cache
        cached = cache.get(key_html)
        if cached is not None:
            return HTMLResponse(
                content=cached,
                status_code=app_state,
                headers=self._NO_CACHE_HEADERS,
            )

        app_name = self.__app_name
        locale = self.__app_locale
        html = await self.__render(template_page, {})
        response = HTMLResponse(
            content=html,
            status_code=app_state,
            headers=self._NO_CACHE_HEADERS,
        )
        # Publish only bodies belonging to the current application identity.
        if self.__app_name == app_name and self.__app_locale == locale:
            cache[key_html] = response.getBody()
        return response

    async def error(
        self,
        status_code: int | HTTPStatus,
        content: str | dict,
        *,
        expects_json: bool,
        headers: dict[str, str] | None = None,
    ) -> HTMLResponse | JSONResponse:
        """
        Return an error page or JSON response for the specified status code.

        Parameters
        ----------
        status_code : int | HTTPStatus
            Integer HTTP status between 100 and 599. Unlisted codes use
            an ``HTTP <code>`` label on the HTML page.
        content : str | dict
            Content of the error to display. HTML renders the description
            as escaped text; JSON preserves the supplied values.
        expects_json : bool
            If True, returns a JSON response; otherwise, returns HTML.
        headers : dict[str, str] | None, optional
            Additional headers to include in the response.

        Returns
        -------
        HTMLResponse or JSONResponse
            HTMLResponse with rendered error page, or JSONResponse if
            expects_json is True.

        Raises
        ------
        TypeError
            If status_code is not an integer.
        ValueError
            If status_code is outside the range 100 to 599.
        """
        response_headers = self._NO_CACHE_HEADERS if headers is None else headers

        if expects_json:
            # JSONResponse validates the status before serializing the payload.
            if isinstance(status_code, HTTPStatus):
                status_code = status_code.value
            data: dict = content if isinstance(content, dict) else {"message": content}
            response = JSONResponse(
                content=data, status_code=status_code, headers=response_headers,
            )
        else:
            # Validate HTML statuses before inspecting content or rendering templates.
            status_code = _validate_status_code(status_code)
            if isinstance(content, dict):
                description = (
                    str(content["message"])
                    if "message" in content
                    else json.dumps(content)
                )
            else:
                # Error descriptions are text, including HTML-marked strings.
                description = str(content)

            html = await self.__render("error", {
                "error": status_code,
                "digits": str(status_code),
                "message": _status_message(status_code),
                "description": description,
            })
            response = HTMLResponse(
                content=html, status_code=status_code, headers=response_headers,
            )

        # Preserve caller cache policies using the response's normalized headers.
        if headers is not None and not response.hasHeader("cache-control"):
            response.setHeader("cache-control", self._GENERAL_CACHE_CONTROL)
        return response

    async def exception(
        self,
        request_path: str,
        request_method: str,
        exception: BaseException,
        status_code: int | HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
    ) -> HTMLResponse:
        """
        Render an exception page with request and traceback details.

        Parameters
        ----------
        request_path : str
            Path of the request that caused the exception.
        request_method : str
            HTTP method of the request that caused the exception.
        exception : BaseException
            Exception instance to be rendered.
        status_code : int | HTTPStatus, optional
            HTTP status code for the response. Defaults to 500.

        Returns
        -------
        HTMLResponse
            Rendered exception page as an HTMLResponse with the given status code.
        """
        status_code = _validate_status_code(status_code)
        traceback_data = ExceptionParser(exception).toDict()
        config = self.__app.config
        chatgpt_url, chatgpt_trace_truncated = build_chatgpt_url(
            traceback_data, config(_LOCALE_CONFIG_KEY), request_method, request_path,
        )
        html = await self.__render("exception", {
            "exception": traceback_data["error_type"],
            "traceback": traceback_data,
            "request_path": request_path,
            "request_method": request_method,
            "chatgpt_url": chatgpt_url,
            "chatgpt_trace_truncated": chatgpt_trace_truncated,
            "framework_version": _FRAMEWORK_VERSION,
            "python_version": _PYTHON_VERSION,
            "environment": config("app.env"),
            "debug_mode": "Enabled" if config("app.debug") else "Disabled",
            "timezone": DateTime.getTimezone(),
            "interface": config("app.interface").upper(),
        })
        return HTMLResponse(
            content=html,
            status_code=status_code,
            headers=self._NO_CACHE_HEADERS,
        )

    def __refreshContext(self) -> None:
        """Refresh application labels and expire health bodies when they change.

        Returns
        -------
        None
            Update the labels used by subsequent template renders.
        """
        config = self.__app.config
        app_name = config("app.name")
        locale = config(_LOCALE_CONFIG_KEY)
        if app_name != self.__app_name or locale != self.__app_locale:
            self.__app_name = app_name
            self.__app_locale = locale
            cache = self.__memory_cache
            cache.pop(self._HEALTH_STATES[False][3], None)
            cache.pop(self._HEALTH_STATES[True][3], None)

    async def __render(self, page: str, context: dict[str, object]) -> str:
        """
        Render a built-in template through the application's official engine.

        Parameters
        ----------
        page : str
            Internal template name, selected by this response service.
        context : dict[str, object]
            Owned request context, filled with common template values.

        Returns
        -------
        str
            Rendered HTML document.
        """
        self.__refreshContext()
        context["app_name"] = self.__app_name
        context["locale"] = self.__app_locale
        context["page"] = page
        context["asset_base"] = self._ASSET_BASE
        return await self.__engine.render(self._TEMPLATES[page], context)

    def asset(self, path: str) -> FileResponse | Response:
        """
        Serve a whitelisted package asset without exposing arbitrary files.

        Parameters
        ----------
        path : str
            Exact asset name relative to the reserved asset URL prefix.

        Returns
        -------
        FileResponse | Response
            Local asset with its fixed MIME type, or an empty 404 response.
        """
        headers = self._ASSET_HEADERS.get(path)
        if headers is None:
            return Response(status_code=HTTPStatus.NOT_FOUND)
        paths = self.__asset_paths
        asset_path = paths.get(path)
        if asset_path is None:
            asset_path = self._ASSETS_DIR / path
            paths[path] = asset_path
        response = self.__fileResponse(asset_path, headers)
        if response is None:
            return Response(status_code=HTTPStatus.NOT_FOUND)
        return response
