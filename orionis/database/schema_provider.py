from orionis.container.providers.service_provider import ServiceProvider
from orionis.database.contracts.schema import ISchema
from orionis.database.schema.schema import Schema

class SchemaProvider(ServiceProvider):

    def register(self) -> None:
        """
        Bind the `ISchema` contract to the `Schema` implementation.

        A new instance is resolved on every request (transient lifetime),
        since `Schema` stores the explicit connection selection for
        subsequent schema operations.

        Returns
        -------
        None
            The binding is registered as a side effect.
        """
        # Register a transient binding to avoid leaking state between uses
        self.app.transient(ISchema, Schema)
