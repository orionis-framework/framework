from __future__ import annotations
from typing import Any, TYPE_CHECKING
from orionis.http.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from orionis.support.facades.view import View

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, Iterable, Mapping
    from pathlib import Path
    from orionis.background.task import BackgroundTask
    from orionis.http.enums.status import HTTPStatus
    from orionis.view.pending import PendingView

class ResponseFactory:
    """
    Build every kind of HTTP response from a single entry-point.

    Controllers use the module-level :data:`response` instance so they do
    not need to import a different class for each response type::

        return response.view("users.index", users=users)
        return response.json({"ok": True})
        return response.redirect("/login")
    """

    # ruff: noqa: ANN401, PLR0913

    __slots__ = ()

    def view(self, template: str, **context: Any) -> PendingView:
        """
        Render a template as an awaitable, chainable HTML response.

        Parameters
        ----------
        template : str
            Template name using dot notation (e.g. ``'users.index'``) or a
            relative path (e.g. ``'users/index.html'``).
        **context : Any
            Keyword arguments forwarded as template variables.

        Returns
        -------
        PendingView
            Awaitable proxy that resolves to an :class:`HTMLResponse` and
            accepts chained mutators such as ``withErrors()``.
        """
        return View.make(template, **context)

    def html(
        self,
        content: str | bytes = "",
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> HTMLResponse:
        """
        Build a response carrying raw HTML content.

        Parameters
        ----------
        content : str | bytes, optional
            HTML content to send.
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        HTMLResponse
            The configured HTML response.
        """
        return HTMLResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            background=background,
        )

    def json(
        self,
        content: Any,
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
        *,
        indent: int | None = None,
        ensure_ascii: bool = False,
        separators: tuple[str, str] | None = None,
        default: Any | None = None,
    ) -> JSONResponse:
        """
        Build a response serialising the content as JSON.

        Parameters
        ----------
        content : Any
            Content to serialise as JSON.
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.
        indent : int | None, optional
            Indentation level for pretty-printing JSON.
        ensure_ascii : bool, optional
            Whether to escape non-ASCII characters.
        separators : tuple[str, str] | None, optional
            Item and key separators for JSON output.
        default : Any | None, optional
            Custom encoder for unsupported types.

        Returns
        -------
        JSONResponse
            The configured JSON response.
        """
        return JSONResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            background=background,
            indent=indent,
            ensure_ascii=ensure_ascii,
            separators=separators,
            default=default,
        )

    def text(
        self,
        content: str | bytes = "",
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> PlainTextResponse:
        """
        Build a response carrying plain text content.

        Parameters
        ----------
        content : str | bytes, optional
            Plain text content to send.
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        PlainTextResponse
            The configured plain text response.
        """
        return PlainTextResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            background=background,
        )

    def redirect(
        self,
        url: str,
        status_code: HTTPStatus | int = 302,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> RedirectResponse:
        """
        Build a response redirecting the client to another URL.

        Parameters
        ----------
        url : str
            Target URL for the redirection.
        status_code : HTTPStatus | int, optional
            Redirect status code (301, 302, 303, 307, 308).
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        RedirectResponse
            The configured redirect response.
        """
        return RedirectResponse(
            url=url,
            status_code=status_code,
            headers=headers,
            background=background,
        )

    def stream(
        self,
        content: AsyncIterable[bytes] | Iterable[bytes],
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> StreamingResponse:
        """
        Build a response streaming byte chunks to the client.

        Parameters
        ----------
        content : AsyncIterable[bytes] | Iterable[bytes]
            Streaming content source.
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        media_type : str | None, optional
            Media type advertised for the stream.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        StreamingResponse
            The configured streaming response.
        """
        return StreamingResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

    def file(
        self,
        path: str | Path,
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
        chunk_size: int = 64 * 1024,
        background: BackgroundTask | None = None,
    ) -> FileResponse:
        """
        Build a response streaming a file from disk.

        Parameters
        ----------
        path : str | Path
            Path to the file to serve.
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        media_type : str | None, optional
            Media type of the file; guessed from the path when omitted.
        filename : str | None, optional
            Name advertised in the ``Content-Disposition`` header.
        chunk_size : int, optional
            Size of the chunks read from disk.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        FileResponse
            The configured file response.
        """
        return FileResponse(
            path=path,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            filename=filename,
            chunk_size=chunk_size,
            background=background,
        )

    def download(
        self,
        path: str | Path,
        filename: str | None = None,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> FileResponse:
        """
        Build a file response forced to be downloaded as an attachment.

        Parameters
        ----------
        path : str | Path
            Path to the file to serve.
        filename : str | None, optional
            Name advertised to the client; defaults to the file name.
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        media_type : str | None, optional
            Media type of the file; guessed from the path when omitted.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        FileResponse
            The configured attachment response.
        """
        file_response = FileResponse(
            path=path,
            headers=headers,
            media_type=media_type,
            background=background,
        )
        name = filename or file_response.getPath().name
        file_response.setHeader(
            "content-disposition",
            f'attachment; filename="{name}"',
        )
        return file_response

    def noContent(
        self,
        status_code: HTTPStatus | int = 204,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> Response:
        """
        Build an empty response, typically for ``204 No Content``.

        Parameters
        ----------
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        Response
            The configured empty response.
        """
        return Response(
            status_code=status_code,
            headers=headers,
            background=background,
        )

    def make(
        self,
        content: Any = None,
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> Response:
        """
        Build a bare response with full control over its content.

        Parameters
        ----------
        content : Any, optional
            The response content or stream.
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Extra headers to include.
        media_type : str | None, optional
            Media type advertised for the content.
        background : BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        Response
            The configured response.
        """
        return Response(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

# Stateless factory shared by every controller; safe to import directly.
response: ResponseFactory = ResponseFactory()
