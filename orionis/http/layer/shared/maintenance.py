from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.default.contracts.responses import IDefaultResponses
    from orionis.http.responses import Response

class UnderMaintenanceMiddleware:
    """Reject every incoming request with 503 while in maintenance mode.

    The response format (HTML or JSON) is selected by inspecting the
    ``Accept`` header of the incoming request via ``adapter.wantsJson()``.
    """

    __slots__ = ("__default_responses", "__under_maintenance")

    def __init__(
        self,
        *,
        under_maintenance: bool,
        default_responses: IDefaultResponses,
    ) -> None:
        """
        Initialize with the maintenance flag and default response handler.

        Parameters
        ----------
        under_maintenance : bool
            ``True`` when the application is in maintenance mode.
        default_responses : IDefaultResponses
            Handler used to build the 503 response.

        Returns
        -------
        None
        """
        self.__under_maintenance: bool = under_maintenance
        self.__default_responses: IDefaultResponses = default_responses

    def handle(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
        """
        Return a 503 response if the application is under maintenance.

        Parameters
        ----------
        adapter : TransportAdapter
            Transport adapter providing header access and client-preference
            detection via ``wantsJson()``.

        Returns
        -------
        Response | None
            A 503 response when the application is in maintenance mode,
            ``None`` otherwise.
        """
        if not self.__under_maintenance:
            return None

        return self.__default_responses.error(
            status_code=503,
            content="The application is currently under maintenance.",
            expects_json=adapter.wantsJson(),
        )
