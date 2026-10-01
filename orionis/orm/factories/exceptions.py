class FactoryException(Exception):
    """Base exception for model factory failures."""

class FactoryConfigurationException(FactoryException):
    """Report invalid model, count, locale, seed, or sequence configuration."""

class FactoryDefinitionException(FactoryException):
    """Report an absent definition or invalid generated attributes."""

class FactoryDependencyException(FactoryException):
    """Report an unavailable optional data provider."""

class FactoryPersistenceException(FactoryException):
    """Report a model event vetoing persistence."""

class FactoryConcurrencyException(FactoryException):
    """Report overlapping operations on the same factory instance."""
