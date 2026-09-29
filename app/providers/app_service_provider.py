from orionis.container.providers import ServiceProvider

class AppServiceProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register application services.

        This method is intended to bind services or dependencies into the
        application's service container.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Register application-specific services here.

    async def boot(self) -> None:
        """
        Bootstrap application services.

        This asynchronous method is called after all services have been
        registered, allowing for any necessary initialization.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Perform any asynchronous bootstrapping tasks here.
