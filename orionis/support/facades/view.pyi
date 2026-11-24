# ruff: noqa: ANN401
# Templates accept arbitrary context values.
from collections.abc import Mapping
from typing import Any
from orionis.background.task import BackgroundTask
from orionis.container.facades.facade import Facade
from orionis.http.enums.status import HTTPStatus
from orionis.view.contracts.factory import IViewFactory
from orionis.view.pending import PendingView

class View(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IViewFactory]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IViewFactory: ...

    @classmethod
    def make(
        cls,
        template: str,
        *,
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
        context: Mapping[str, Any] | None = None,
        **variables: Any,
    ) -> PendingView: ...
