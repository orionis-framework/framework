from orionis.support.types.collection import Collection

# The ORM returns query results using the framework-wide Collection type;
# this module re-exports it so ORM consumers import from a single place.
ModelCollection = Collection

__all__ = [
    "Collection",
    "ModelCollection",
]
