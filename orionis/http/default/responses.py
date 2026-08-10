import json
import platform
import re
from pathlib import Path
from typing import ClassVar
from orionis.foundation.contracts.directory import IDirectory
from orionis.foundation.directory import Directory
from orionis.foundation.contracts.application import IApplication
from orionis.http.default.contracts.responses import IDefaultResponses
from orionis.http.enums.status import HTTPStatus
from orionis.http.request import Request
from orionis.http.response import FileResponse, HTMLResponse, JSONResponse, Response
from orionis.metadata import VERSION
from orionis.support.facades.datetime import DateTime
from orionis.support.formatter.exceptions.parser import ExceptionParser

# Dynamic placeholders substituted on every generic error page render.
_ERROR_PLACEHOLDER_RE: re.Pattern = re.compile(
    r"\{\{(0|1|2|error|message|description)\}\}",
)

# Human-readable status labels resolved once per HTTP status code.
_STATUS_MESSAGES: dict[int, str] = {}

def _compile_placeholders(
    template: str,
    pattern: re.Pattern,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """
    Split a template into literal chunks and the placeholder keys between them.

    Parameters
    ----------
    template : str
        Raw template text containing ``{{key}}`` placeholders.
    pattern : re.Pattern
        Compiled pattern whose first group captures the placeholder key.

    Returns
    -------
    tuple[tuple[str, ...], tuple[str, ...]]
        The literal chunks and the ordered placeholder keys, so rendering
        becomes a single join instead of one full copy per placeholder.
    """
    literals: list[str] = []
    keys: list[str] = []
    cursor = 0

    for match in pattern.finditer(template):
        literals.append(template[cursor:match.start()])
        keys.append(match.group(1))
        cursor = match.end()

    literals.append(template[cursor:])
    return tuple(literals), tuple(keys)

class DefaultResponses(IDefaultResponses):

    # ruff: noqa: TC001

    _FAVICON_CACHE_CONTROL_AGE: str = "public, max-age=31536000, immutable"
    _ROBOTS_TXT_CACHE_CONTROL_AGE: str = "public, max-age=3600"
    _SITEMAP_XML_CACHE_CONTROL_AGE: str = "public, max-age=600"
    _GENERAL_CACHE_CONTROL: str = "no-cache, no-store, must-revalidate"

    # Template placeholder constants used across multiple page renderers
    _TPL_APP_NAME: str = "{{app_name}}"
    _TPL_LOCALE: str = "{{locale}}"

    # Directory paths resolved once at class definition time
    _ASSETS_DIR: Path = Path(__file__).parent / "assets"
    _PAGES_DIR: Path = Path(__file__).parent / "pages"

    # Ordered favicon candidates; tuple avoids per-call dict allocation
    _FAVICON_CANDIDATES: tuple[tuple[str, str], ...] = (
        ("favicon.ico", "image/x-icon"),
        ("favicon.png", "image/png"),
        ("favicon.svg", "image/svg+xml"),
    )

    # Lookup table mapping maintenance flag to all health-state constants
    _HEALTH_STATES: ClassVar[dict[bool, tuple[HTTPStatus, str, str, str, str]]] = {
        False: (
            HTTPStatus.OK, "Online Application", "up",
            "http_200:json", "state_page_200:html",
        ),
        True: (
            HTTPStatus.SERVICE_UNAVAILABLE, "Application in Maintenance", "down",
            "http_503:json", "state_page_503:html",
        ),
    }

    def __init__(
        self,
        app: IApplication,
        directory: Directory,
    ) -> None:
        """
        Initialize instance with application and directory dependencies.

        Parameters
        ----------
        app : IApplication
            The application instance providing configuration and services.
        directory : IDirectory
            The directory service for accessing storage paths.

        Returns
        -------
        None
            This constructor does not return a value.
        """
        # Store application and directory dependencies
        self.__app: IApplication = app
        self.__directory: IDirectory = directory

        # Cache frequently accessed configuration values
        self.__app_name: str = self.__app.config("app.name")
        self.__app_locale: str = self.__app.config("app.locale")

        # Initialize memory cache for static asset responses
        self.__memory_cache: dict[str, object] = {}

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

    def favicon(self) -> FileResponse | Response:
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
        # Return the cached favicon response on subsequent requests
        cache = self.__memory_cache
        cached = cache.get("favicon")
        if cached is not None:
            return cached  # type: ignore[return-value]

        public_storage: Path = self.__directory.storagePublic()
        cc_age = self._FAVICON_CACHE_CONTROL_AGE

        # Search for favicon using precomputed candidate tuples
        for file_name, content_type in self._FAVICON_CANDIDATES:
            favicon_path = public_storage / file_name
            if favicon_path.exists():
                response = FileResponse(
                    path=favicon_path,
                    headers={"content-type": content_type, "cache-control": cc_age},
                )
                cache["favicon"] = response
                return response

        # Fall back to the internal framework favicon asset
        fallback_path = self._ASSETS_DIR / "favicon.ico"
        if fallback_path.exists():
            response = FileResponse(
                path=fallback_path,
                headers={"content-type": "image/x-icon", "cache-control": cc_age},
            )
            cache["favicon"] = response
            return response

        # Return 404 if no favicon is found anywhere
        return self.error(
            status_code=HTTPStatus.NOT_FOUND,
            content="Favicon Not Found",
            expects_json=False,
            headers={"cache-control": self._GENERAL_CACHE_CONTROL},
        )

    def robotsTxt(self) -> FileResponse | Response:
        """
        Return the robots.txt file or a 404 response if not found.

        Search for a robots.txt file in the public storage directory. If not
        found, check for a fallback file. Cache the result for future calls.

        Returns
        -------
        FileResponse or Response
            FileResponse with robots.txt if found, otherwise Response with 404.
        """
        # Return the cached robots.txt response on subsequent requests
        cache = self.__memory_cache
        cached = cache.get("robots_txt")
        if cached is not None:
            return cached  # type: ignore[return-value]

        public_storage: Path = self.__directory.storagePublic()
        robots_path = public_storage / "robots.txt"

        if robots_path.exists():
            response = FileResponse(
                path=robots_path,
                headers={
                    "content-type": "text/plain",
                    "cache-control": self._ROBOTS_TXT_CACHE_CONTROL_AGE,
                },
            )
            cache["robots_txt"] = response
            return response

        # Fall back to the internal framework robots.txt asset
        fallback_path = self._ASSETS_DIR / "robots.txt"
        if fallback_path.exists():
            response = FileResponse(
                path=fallback_path,
                headers={
                    "content-type": "text/plain",
                    "cache-control": self._ROBOTS_TXT_CACHE_CONTROL_AGE,
                },
            )
            cache["robots_txt"] = response
            return response

        # Return 404 if robots.txt is not found anywhere
        return self.error(
            status_code=HTTPStatus.NOT_FOUND,
            content="Robots.txt Not Found",
            expects_json=False,
            headers={"cache-control": self._GENERAL_CACHE_CONTROL},
        )

    def sitemapXml(self) -> FileResponse | Response:
        """
        Return the sitemap.xml file or a 404 response if found, else 404.

        Search for a sitemap.xml file in the public storage directory. If not found,
        check for a fallback file. Cache the result for future calls.

        Returns
        -------
        FileResponse or Response
            FileResponse with sitemap.xml if found, otherwise Response with status 404.
        """
        # Return the cached sitemap.xml response on subsequent requests
        cache = self.__memory_cache
        cached = cache.get("sitemap_xml")
        if cached is not None:
            return cached  # type: ignore[return-value]

        public_storage: Path = self.__directory.storagePublic()
        sitemap_path = public_storage / "sitemap.xml"

        if sitemap_path.exists():
            response = FileResponse(
                path=sitemap_path,
                headers={
                    "content-type": "application/xml",
                    "cache-control": self._SITEMAP_XML_CACHE_CONTROL_AGE,
                },
            )
            cache["sitemap_xml"] = response
            return response

        # Return 404 if sitemap.xml is not found
        return self.error(
            status_code=HTTPStatus.NOT_FOUND,
            content="Sitemap Not Found",
            expects_json=False,
            headers={"cache-control": self._GENERAL_CACHE_CONTROL},
        )

    def health(self, request: Request) -> HTMLResponse | JSONResponse:
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

        # Resolve all state-dependent constants with a single table lookup
        app_state, state_label, template_page, key_json, key_html = (
            self._HEALTH_STATES[config_maintenance]
        )

        cache = self.__memory_cache

        if request.wantsJson():
            # Return cached JSON health response for this maintenance state
            cached = cache.get(key_json)
            if cached is not None:
                return cached  # type: ignore[return-value]
            response = JSONResponse(
                content={"message": state_label},
                status_code=app_state,
                headers={"cache-control": self._GENERAL_CACHE_CONTROL},
            )
            cache[key_json] = response
            return response

        # Build and cache the HTML state page for the current maintenance state
        cached = cache.get(key_html)
        if cached is not None:
            return cached  # type: ignore[return-value]

        state_page_path = self._PAGES_DIR / f"{template_page}.html"
        with state_page_path.open() as f:
            raw_html = f.read()
        html: str = (
            raw_html.replace(self._TPL_APP_NAME, self.__app_name)
                    .replace(self._TPL_LOCALE, self.__app_locale)
        )
        response = HTMLResponse(
            content=html,
            status_code=app_state,
            headers={"cache-control": self._GENERAL_CACHE_CONTROL},
        )
        cache[key_html] = response
        return response

    def error(
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
            HTTP status code to display on the error page.
        content : str | dict
            Content of the error to display.
        expects_json : bool
            If True, returns a JSON response; otherwise, returns HTML.
        headers : dict[str, str] | None, optional
            Additional headers to include in the response.

        Returns
        -------
        HTMLResponse or JSONResponse
            HTMLResponse with rendered error page, or JSONResponse if
            expects_json is True.
        """
        # Convert HTTPStatus enum to raw integer value
        if isinstance(status_code, HTTPStatus):
            status_code = status_code.value

        # Ensure cache-control header is always present
        if headers is None:
            headers = {"cache-control": self._GENERAL_CACHE_CONTROL}
        elif "cache-control" not in headers:
            headers["cache-control"] = self._GENERAL_CACHE_CONTROL

        if expects_json:
            # Build JSON payload, reusing the caller dict for dict content
            data: dict = content if isinstance(content, dict) else {"message": content}
            return JSONResponse(content=data, status_code=status_code, headers=headers)

        cache = self.__memory_cache

        # Build the chunked render plan once, with static placeholders resolved
        plan: tuple[tuple[str, ...], tuple[str, ...]] | None = cache.get(
            "error_page_plan",
        )  # type: ignore[assignment]
        if plan is None:
            error_page_path = self._PAGES_DIR / "error.html"
            with error_page_path.open() as f:
                raw = f.read()
            template = (
                raw.replace(self._TPL_APP_NAME, self.__app_name)
                   .replace(self._TPL_LOCALE, self.__app_locale)
            )
            plan = _compile_placeholders(template, _ERROR_PLACEHOLDER_RE)
            cache["error_page_plan"] = plan

        # Compute status string once to eliminate repeated int-to-str conversions
        status_str = str(status_code)
        message: str | None = _STATUS_MESSAGES.get(status_code)
        if message is None:
            message = HTTPStatus(status_code).name.replace("_", " ").title()
            _STATUS_MESSAGES[status_code] = message
        description: str = (
            content.get("message", json.dumps(content))
            if isinstance(content, dict)
            else content
        )

        values: dict[str, str] = {
            "0": status_str[0],
            "1": status_str[1],
            "2": status_str[2],
            "error": status_str,
            "message": message,
            "description": description,
        }

        literals, keys = plan
        pieces: list[str] = []
        for index, key in enumerate(keys):
            pieces.append(literals[index])
            pieces.append(values[key])
        pieces.append(literals[-1])
        html: str = "".join(pieces)

        # Return the rendered error page with the specified status code and headers
        return HTMLResponse(content=html, status_code=status_code, headers=headers)

    def exception(
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
        cache = self.__memory_cache

        # Load and pre-substitute all static values into the template on first use
        template: str | None = cache.get("exception_page_template")  # type: ignore[assignment]
        if template is None:
            exception_page_path = self._PAGES_DIR / "exception.html"
            with exception_page_path.open() as f:
                raw = f.read()
            debug_status: str = (
                "Enabled" if self.__app.config("app.debug") else "Disabled"
            )
            template = (
                raw.replace("{{framework_version}}", f"v{VERSION}")
                   .replace("{{python_version}}", platform.python_version())
                   .replace("{{environment}}", self.__app.config("app.env"))
                   .replace("{{debug_mode}}", debug_status)
                   .replace("{{timezone}}", DateTime.getTimezone())
                   .replace("{{interface}}", self.__app.config("app.interface").upper())
                   .replace(self._TPL_LOCALE, self.__app_locale)
                   .replace(self._TPL_APP_NAME, self.__app_name)
            )
            cache["exception_page_template"] = template

        # Parse the exception and extract the error type into a local variable
        traceback_data = ExceptionParser(exception).toDict()
        error_type: str = traceback_data["error_type"]

        # Render dynamic request and exception details into the pre-built template
        html: str = (
            template.replace("{{path}}", request_path)
                    .replace("{{request_method}}", request_method)
                    .replace("{{error_context}}", error_type)
                    .replace('"{{traceback}}"', json.dumps(traceback_data))
                    .replace("{{exception}}", error_type)
        )

        # Return the rendered exception page with the specified status code
        return HTMLResponse(
            content=html,
            status_code=status_code,
            headers={"cache-control": self._GENERAL_CACHE_CONTROL},
        )
