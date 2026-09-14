from orionis.auth.contracts.policy import IPolicy

# Sentinel distinguishing "not cached yet" from a cached ``None`` result.
_MISSING: object = object()

class PolicyRegistry:
    """Map resource classes to the policy classes protecting them.

    Lookups walk the method resolution order once and memoise the result,
    so an inherited policy costs a single dictionary read after the first
    request that needed it.

    Concurrency
    -----------
    Registration happens during application boot. The lookup cache is a
    pure function of the registry, so a concurrent first lookup may
    compute the same value twice without any observable difference.
    """

    __slots__ = ("__lookup", "__policies")

    def __init__(self) -> None:
        """Initialise an empty registry.

        Returns
        -------
        None
            The registry starts without any policy binding.
        """
        self.__policies: dict[type, type[IPolicy]] = {}
        self.__lookup: dict[type, type[IPolicy] | None] = {}

    def register(self, resource: type, policy: type[IPolicy]) -> None:
        """Bind a policy class to a resource class.

        Parameters
        ----------
        resource : type
            Resource class protected by the policy.
        policy : type[IPolicy]
            Policy class implementing the abilities.

        Returns
        -------
        None
            The binding is stored as a side effect.

        Raises
        ------
        TypeError
            If either argument is not a class.
        """
        if not isinstance(resource, type):
            error_msg = "The policy resource must be a class."
            raise TypeError(error_msg)
        if not isinstance(policy, type) or not issubclass(policy, IPolicy):
            error_msg = "The policy must be a class implementing IPolicy."
            raise TypeError(error_msg)

        self.__policies[resource] = policy

        # Inherited lookups may now resolve differently.
        self.__lookup.clear()

    def policyFor(self, resource: type) -> type[IPolicy] | None:
        """Return the policy protecting a resource class.

        Parameters
        ----------
        resource : type
            Resource class to look a policy up for.

        Returns
        -------
        type[IPolicy] | None
            Registered policy class, or ``None`` when the resource and
            none of its ancestors declare one.
        """
        cached = self.__lookup.get(resource, _MISSING)
        if cached is not _MISSING:
            return cached

        policies = self.__policies
        resolved: type[IPolicy] | None = None
        for ancestor in resource.__mro__:
            candidate = policies.get(ancestor)
            if candidate is not None:
                resolved = candidate
                break

        self.__lookup[resource] = resolved
        return resolved

    def bindings(self) -> dict[type, type[IPolicy]]:
        """Return a copy of the registered resource to policy bindings.

        Returns
        -------
        dict[type, type[IPolicy]]
            Shallow copy, so callers cannot mutate the registry.
        """
        return dict(self.__policies)
