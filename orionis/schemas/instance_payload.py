import msgspec

_PLANS: dict[type, tuple] = {}

def instance_payload(value: object) -> object:
    """
    Expand structs using their wire names, tags and container shape.

    Include default values and preserve native leaves so validation cannot
    skip existing struct fields or accept values coerced by serialization.

    Parameters
    ----------
    value : object
        Struct, supported container or native value to prepare for validation.

    Returns
    -------
    object
        Expanded dictionaries and lists, or the original native leaf value.
    """
    if isinstance(value, msgspec.Struct):
        klass = type(value)
        plan = _PLANS.get(klass)
        if plan is None:
            config = klass.__struct_config__
            plan = (
                tuple((f.name, f.encode_name) for f in msgspec.structs.fields(klass)),
                config.array_like, config.tag, config.tag_field,
            )
            _PLANS[klass] = plan
        fields, array_like, tag, tag_field = plan
        if array_like:
            result = [tag] if tag is not None else []
            result.extend(instance_payload(getattr(value, name)) for name, _ in fields)
            return result
        result = {tag_field: tag} if tag is not None else {}
        result.update(
            (encoded, instance_payload(getattr(value, name)))
            for name, encoded in fields
        )
        return result
    if isinstance(value, dict):
        return {key: instance_payload(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [instance_payload(item) for item in value]
    return value
