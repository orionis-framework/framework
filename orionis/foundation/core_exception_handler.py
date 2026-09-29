from types import MappingProxyType

def get_core_exception_handler_mapping() -> MappingProxyType:
    """
    Return an immutable mapping for the default exception handler.

    Returns
    -------
    MappingProxyType
        An immutable mapping containing the 'module' and 'class' keys, referencing
        the default exception handler's module and class name.
    """
    return MappingProxyType(
        {"module": "orionis.failure.base.handler", "class": "BaseExceptionHandler"},
    )

CORE_EXCEPTION_HANDLER: MappingProxyType = get_core_exception_handler_mapping()
