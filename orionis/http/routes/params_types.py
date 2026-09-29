import uuid

PARAM_TYPES = {
    "str": {
        "pattern": r"[^/]+",
        "converter": str,
    },
    "slug": {
        "pattern": r"[a-z0-9-]+",
        "converter": str,
    },
    "int": {
        "pattern": r"\d+",
        "converter": int,
    },
    "uuid": {
        "pattern": (
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
        ),
        "converter": uuid.UUID,
    },
}
