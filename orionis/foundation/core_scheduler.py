"""Provide foundation operations through ``get_core_scheduler_mapping``."""

from types import MappingProxyType

def get_core_scheduler_mapping() -> MappingProxyType:
    """
    Return an immutable mapping with core scheduler module and class information.

    Returns
    -------
    types.MappingProxyType
        Immutable mapping containing the 'module' and 'class' keys, referencing
        the BaseScheduler's module and class name.
    """
    return MappingProxyType(
        {"module": "orionis.console.base.scheduler", "class": "BaseScheduler"},
    )

CORE_SCHEDULER: MappingProxyType = get_core_scheduler_mapping()
"""Core scheduler used by ``core_scheduler``."""
