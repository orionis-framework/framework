from orionis.container.facades.facade import Facade
from orionis.failure.contracts.catch import ICatch
from orionis.failure.entities.context import FailureContext, FailureReceipt
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from orionis.http.request import Request
from orionis.http.responses import Response

class Catch(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> str: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> ICatch: ...

    @classmethod
    async def capture(
        cls,
        exception: BaseException,
        *,
        context: FailureContext,
    ) -> FailureReceipt | None: ...

    @classmethod
    async def exception(
        cls,
        exception: BaseException,
        request: Request | TransportAdapter | None = None,
    ) -> Response | None: ...
