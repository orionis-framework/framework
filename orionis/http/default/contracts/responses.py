from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from orionis.http.enums.status import HTTPStatus

if TYPE_CHECKING:
    from orionis.http.request import Request
    from orionis.http.responses import (
        FileResponse,
        HTMLResponse,
        JSONResponse,
        Response,
    )

class IDefaultResponses(ABC):

    __slots__ = ()

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    async def sitemapXml(self) -> FileResponse | Response:
        """
        Return the public sitemap.xml file, or a 404 response when absent.

        Retain the selected path and read its current metadata for each response.

        Returns
        -------
        FileResponse or Response
            FileResponse with sitemap.xml if found, otherwise Response with status 404.
        """

    @abstractmethod
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

    @abstractmethod
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
            Content of the error to display. A str is used as the message;
            a dict is serialised directly into the JSON payload or extracted
            via its ``message`` key for HTML rendering. The HTML description
            is escaped text; JSON preserves the supplied values.
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

    @abstractmethod
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

    @abstractmethod
    def asset(self, path: str) -> FileResponse | Response:
        """Return an allowlisted framework asset, or a 404 response.

        Parameters
        ----------
        path : str
            Asset path relative to the framework's public asset prefix.

        Returns
        -------
        FileResponse or Response
            Packaged static file when allowed and present, otherwise a 404.
        """
