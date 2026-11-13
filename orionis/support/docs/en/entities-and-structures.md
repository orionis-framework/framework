# Entities and data structures

Use a dataclass for an application result with known fields; `BaseEntity` adds recursive serialization and metadata. Use `DotDict` or `StdClass` when keys are determined at runtime. These utilities do not validate untrusted input like a Schema. The examples are independent of one another.

## Common workflows

### Define a serializable entity

```python
from dataclasses import dataclass, field
from enum import Enum

from orionis.support.entities import BaseEntity


class Status(Enum):
    ACTIVE = "active"


@dataclass
class Account(BaseEntity):
    name: str
    status: Status = Status.ACTIVE
    tags: list[str] = field(default_factory=list)


account = Account("Ada", tags=["admin"])
assert account.toDict() == {
    "name": "Ada",
    "status": "active",
    "tags": ["admin"],
}
assert [item["name"] for item in account.getFields()] == ["name", "status", "tags"]
```

### Use attribute-oriented data

```python
from orionis.support.types import DotDict, StdClass

settings = DotDict({"mail": {"driver": "smtp"}})
assert settings.mail.driver == "smtp"
assert settings.unknown is None

user = StdClass(name="Ada", active=True)
user.update(role="admin")
assert user.toDict()["role"] == "admin"
assert settings.export() == {"mail": {"driver": "smtp"}}
```

`DotDict.get(key, default)` returns the default unchanged when the key is absent and does not insert it. `copy()` deeply copies mutable contents, including nested lists, while retaining shared references and cycles within the copy. `MISSING` preserves its canonical identity through shallow copy, deep copy and pickle round trips.

`StdClass` computes its hash from its current attributes. Keep those attributes unchanged while the object is a dictionary key or set member.

### Freeze configuration snapshots

```python
from types import MappingProxyType

from orionis.support.structures.freezer import FreezeThaw

source = {"hosts": ["a.example", "b.example"], "options": {"tls": True}}
frozen = FreezeThaw.freeze(source)

assert isinstance(frozen, MappingProxyType)
assert frozen["hosts"] == ("a.example", "b.example")
assert FreezeThaw.thaw(frozen) == source
```

`FreezeThaw.freeze()` preserves shared references and cycles that pass through dictionaries, including dictionary/list cycles. Cycles made only of lists and tuples raise `ValueError`, because the frozen tuples cannot represent that cycle. An input `MappingProxyType` is already considered frozen and is returned unchanged; its existing mutable contents are not inspected. Other object types retain their identity. `thaw()` builds mutable dictionaries and lists while preserving graph references.

`BaseEntity.toDict()` serializes direct enum fields to their values; enums nested inside ordinary containers remain enum objects. Each entity class owns its field metadata cache; subclasses have separate entries, and temporary classes can be collected even when their fields refer to the class itself.

## Evidence and next steps

[base.py](../../entities/base.py) · [dot_dict.py](../../types/dot_dict.py) · [std.py](../../types/std.py) · [freezer.py](../../structures/freezer.py)

[Return to the module index](README.md).
