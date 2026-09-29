class ValidationMetadata:
    """
    Root marker for all Orionis field-level annotations.

    Every metadata class that can be applied to a ``Schema`` field must
    inherit—directly or indirectly—from this class. This allows the
    ``MetaCompiler`` and other framework components to identify Orionis
    metadata at runtime through instance checks.

    Notes
    -----
    ``__slots__ = ()`` is declared so that frozen dataclass subclasses
    that use ``slots=True`` do not encounter ``__dict__``/slot conflicts.
    """

    __slots__ = ()
