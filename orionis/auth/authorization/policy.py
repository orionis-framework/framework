from orionis.auth.contracts.policy import IPolicy

class Policy(IPolicy):
    """
    Base class for resource policies.

    Subclasses declare one method per ability. Every ability receives the
    authenticated identity first and the resource second. Methods may be
    synchronous or asynchronous::

        class PostPolicy(Policy):
            async def update(self, identity, post) -> bool:
                return post.user_id == identity.getAuthIdentifier()

    Policies are resolved through the container, so they may declare
    dependencies in their constructor. Each evaluation receives a fresh
    instance built in the current request scope; only class lookups are cached.
    """

    __slots__ = ()

    async def before(self, identity: object, ability: str) -> bool | None:  # noqa: ARG002
        """
        Short circuit the policy before the ability method runs.

        The default implementation never short circuits. Override it to
        grant every ability to a super administrator, for instance.

        Parameters
        ----------
        identity : object
            Authenticated identity being evaluated.
        ability : str
            Name of the ability requested on the resource.

        Returns
        -------
        bool | None
            ``None`` so the ability method decides the outcome.
        """
        return None
