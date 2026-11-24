"""Static regression cases for completions across public Orionis APIs."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import assert_type
    from orionis import IApplication
    from orionis.aio import Loop
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.cache.locks.lock import CacheLock
    from orionis.console.enums.events import TaskEvent
    from orionis.console.fluent.contracts.task import ITask
    from orionis.environment.core.dot_env import DotEnv
    from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
    from orionis.http import Request
    from orionis.http.payload.uploaded_file import UploadedFile
    from orionis.introspection.reflection import Reflection
    from orionis.orm import Model, String
    from orionis.orm.factories.factory import Factory
    from orionis.realtime.hub import HubContext
    from orionis.schemas import Schema
    from orionis.schemas.validator import Schema as Validator
    from orionis.support.facades import (
        Application, Cache, Hash, Reactor, Route, Schedule, View,
    )
    from orionis.support.types.collection import Collection
    from orionis.support.types.stringable import Stringable
    from orionis.test.clients.mcp import McpTestResponse
    from orionis.view.pending import PendingView

    class Customer(Model):
        name = String()

    class Registration(Schema):
        email: str

    async def check_queries(customer: Customer, factory: Factory[Customer]) -> None:
        """
        Preserve model types across fluent queries and transformations.

        Parameters
        ----------
        customer : Customer
            Model instance used to check attributes and relation types.
        factory : Factory[Customer]
            Factory used to check single and collection result types.

        Returns
        -------
        None
            Assert the inferred types of model and collection operations.
        """
        assert_type(customer.name, str | None)
        assert_type(await Customer.findOrFail(1), Customer)
        assert_type(await Customer.where("id", 1).firstOrFail(), Customer)
        assert_type(customer.fill({"name": "Ana"}), Customer)
        assert_type(await customer.hasOne(Customer), Customer | None)
        assert_type(await customer.hasMany(Customer), Collection[Customer])
        page = await Customer.query().paginate()
        assert_type(page.items[0], Customer)
        customers = Collection([customer])
        assert_type(customers.filter(lambda c: c.name is not None)[0], Customer)
        assert_type(customers.map(lambda c: c.name or "").first(), str | None)
        assert_type(customers[:1], Collection[Customer])
        assert_type(customers.get(0), Customer | None)
        assert_type(next(factory.iterMake()), Customer)
        assert_type(factory.count(2).make(), Customer | Collection[Customer])

    async def check_services(app: IApplication, request: Request) -> None:
        """
        Preserve service types through resolution, validation and deferred views.

        Parameters
        ----------
        app : IApplication
            Application used to check service resolution and path types.
        request : Request
            Request used to check reflection, headers and parsed form types.

        Returns
        -------
        None
            Assert the inferred types of service and request operations.
        """
        assert_type(await app.make(DotEnv), DotEnv)
        assert_type(await app.build(DotEnv), DotEnv)
        assert_type(await Application.make(DotEnv), DotEnv)
        assert_type(await Loop.execute(DotEnv), DotEnv)
        assert_type(Reflection.instance(request).getInstance(), Request)
        assert_type(DotEnv(), DotEnv)
        assert_type(app.path("storage"), Path)
        assert_type(app.path("custom_location"), Path | None)
        assert_type((await Validator.validate({}, Registration)).email, str)
        assert_type(View.make("login").withCookie("key", "value"), PendingView)
        assert_type((await Cache.resolve()).store().lock("key"), CacheLock)
        assert_type(Hash.driver("argon2").setMemory(65536), Argon2Hasher)
        assert_type(request.headers.getAll(), dict[str, list[str]])
        assert_type((await request.formUrlEncoded())["name"], str)
        assert_type((await request.form()).files["photo"][0], UploadedFile)
        assert_type(Route.export()["routes"][0]["path"], str)
        assert_type((await Reactor.info())[0]["signature"], str)
        result = Stringable("name").when(condition=True, callback=lambda s: s.slug())
        assert_type(result, Stringable)

    async def check_events(context: HubContext, response: McpTestResponse) -> None:
        """
        Verify declared field types for task events, identities and MCP messages.

        Parameters
        ----------
        context : HubContext
            Hub context used to check the authenticated identity type.
        response : McpTestResponse
            MCP response used to check notification field types.

        Returns
        -------
        None
            Assert the inferred types of scheduled tasks and message fields.
        """
        task = Schedule.command("backup").on(
            TaskEvent.EXECUTED, lambda event: assert_type(event.signature, str),
        )
        assert_type(task, ITask)
        assert_type((await Schedule.info())[0]["start_date"], str | None)
        assert_type(context.user, IAuthenticatable | None)
        assert_type(response.notifications[0]["method"], str)
