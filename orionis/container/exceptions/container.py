class CircularDependencyException(Exception):
    """
    Raise when a circular dependency is detected in the Orionis container.

    This exception signals a circular reference among services or components,
    preventing proper dependency resolution.

    Returns
    -------
    None
        This exception does not return a value.
    """
