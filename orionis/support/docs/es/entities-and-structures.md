# Entidades y estructuras de datos

Usa una dataclass para representar un resultado de aplicación con campos conocidos; `BaseEntity` añade serialización recursiva y metadatos. Usa `DotDict` o `StdClass` cuando las claves se conocen durante la ejecución. Estas utilidades no validan datos externos como un Schema. Los ejemplos son independientes entre sí.

## Flujos de trabajo comunes

### Definir una entidad serializable

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

### Usar datos orientados a atributos

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

### Congelar instantáneas de configuración

```python
from types import MappingProxyType

from orionis.support.structures.freezer import FreezeThaw

source = {"hosts": ["a.example", "b.example"], "options": {"tls": True}}
frozen = FreezeThaw.freeze(source)

assert isinstance(frozen, MappingProxyType)
assert frozen["hosts"] == ("a.example", "b.example")
assert FreezeThaw.thaw(frozen) == source
```

## Fuentes y siguientes pasos

[base.py](../../entities/base.py) · [dot_dict.py](../../types/dot_dict.py) · [std.py](../../types/std.py) · [freezer.py](../../structures/freezer.py)

[Volver al índice del módulo](README.md).
