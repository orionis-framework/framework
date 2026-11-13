"""Provide foundation operations through ``get_core_kernels_mapping``."""

from types import MappingProxyType


def get_core_kernels_mapping() -> MappingProxyType:
    """
    Return an immutable mapping of core kernel class metadata.

    Create and return a MappingProxyType containing metadata for each core
    kernel class. The mapping includes the module and class name for each
    kernel.

    Returns
    -------
    types.MappingProxyType
        Immutable mapping with kernel type as key and a dictionary containing
        'module' and 'class' as values.
    """
    return MappingProxyType(
        {
            "KernelCLI": {"module": "orionis.console.kernel", "class": "KernelCLI"},
            "KernelHTTP": {"module": "orionis.http.kernel", "class": "KernelHTTP"},
        },
    )


CORE_KERNELS: MappingProxyType = get_core_kernels_mapping()
"""Core kernels used by ``core_kernels``."""
