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

## Evidence and next steps

[base.py](../../entities/base.py) · [dot_dict.py](../../types/dot_dict.py) · [std.py](../../types/std.py) · [freezer.py](../../structures/freezer.py)

[Return to the module index](README.md).
