# Orionis Patterns (`orionis.support.patterns`)

> Dos metaclases ligeras y sin dependencias — `Final` (bloquea la herencia) y `Singleton` (patrón singleton seguro para hilos y para `asyncio`) — usadas en todo el framework para reforzar garantías estructurales en el momento de definir la clase.
>
> 🇬🇧 English version: [README.md](README.md)

`orionis.support.patterns` no tiene servicios en tiempo de ejecución,
providers ni facades. Provee dos metaclases independientes que otras
clases del framework adoptan mediante `metaclass=Final` o
`metaclass=Singleton` para obtener una garantía reforzada por el propio
sistema de tipos: "esta clase no se puede heredar" o "esta clase solo
tiene una instancia". Ambas metaclases son Python puro, sin estado desde
la perspectiva de quien las usa, y seguras de usar en cualquier
proyecto, no solo dentro de Orionis.

---

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Descripción funcional del módulo](#descripción-funcional-del-módulo)
3. [Referencia de API](#referencia-de-api)
   - [`Final`](#final-orionissupportpatternsfinalmetafinal)
   - [`Singleton`](#singleton-orionissupportpatternssingletonmetasingleton)
4. [Ejemplos de uso](#ejemplos-de-uso)
5. [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
6. [Notas de diseño](#notas-de-diseño)
7. [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Requisitos

No se necesita instalación adicional además del propio framework:

```bash
uv add orionis
```

- **Python:** 3.14 o superior (el mismo mínimo que el resto del framework).
- **Dependencias:** ninguna más allá de la librería estándar de Python
  (`threading`, `asyncio`).

## Descripción funcional del módulo

| Tipo | Archivo | Tipo de componente | Propósito |
|---|---|---|---|
| `Final` | [final/meta.py](../final/meta.py) | Metaclase (subclase de `type`) | Marca una clase como no heredable; cualquier intento de heredar de ella lanza `TypeError` en el momento de definir la clase. |
| `Singleton` | [singleton/meta.py](../singleton/meta.py) | Metaclase (subclase de `type`) | Garantiza que una clase tenga exactamente una instancia, con una vía síncrona segura para hilos (`__call__`) y una vía asíncrona segura para `asyncio` (`__acall__`). |

Ambas se usan aplicándolas como el `metaclass=` de una clase, por
ejemplo `class Cookies(metaclass=Final): ...` (usado por
`orionis.http.payload.estructures.cookies.Cookies`,
`headers.Headers` y `query_params.QueryParams`) o
`class DotEnv(metaclass=Singleton): ...` (usado por
`orionis.environment.core.dot_env.DotEnv`).

---

## Referencia de API

### `Final` (`orionis.support.patterns.final.meta.Final`)

```python
class Final(type):
    def __new__(metacls, name, bases, namespace) -> type: ...
```

`Final` es una metaclase: se usa vía `metaclass=Final` en la definición
de una clase, no se llama directamente. Su `__new__` se ejecuta una sola
vez, en el momento de definir la clase:

| Comportamiento | Descripción |
|---|---|
| Marcado | Toda clase creada con `metaclass=Final` recibe `__is_final__ = True` establecido directamente en el nuevo objeto clase (vía `type.__setattr__`, evitando cualquier `__setattr__` personalizado). |
| Aplicación | Antes de crear una nueva clase, `Final.__new__` revisa el `__dict__` **propio** de cada clase base (no atributos heredados) buscando `__is_final__ = True`. Si alguna base es final, la creación de la clase lanza `TypeError`. |
| Mensaje de error | `f"Cannot inherit from orionis final class '{base.__name__}'"`. |

No existe ningún otro método público — `Final` solo participa en la
creación de clases a través de `__new__`.

### `Singleton` (`orionis.support.patterns.singleton.meta.Singleton`)

```python
class Singleton(type):
    def __init__(cls, name, bases, namespace) -> None: ...
    def __call__(cls, *args, **kwargs) -> object: ...
    async def __acall__(cls, *args, **kwargs) -> object: ...
```

`Singleton` es una metaclase: se aplica vía `metaclass=Singleton`. Cada
clase que la usa obtiene su propio estado de singleton — no hay ninguna
instancia compartida entre clases `Singleton` que no estén relacionadas.

| Miembro | Descripción |
|---|---|
| `__init__` | Se ejecuta una sola vez, en el momento de definir la clase. Inicializa `cls._singleton_instance` con un centinela interno de "aún no creado" y almacena un `threading.Lock` dedicado en la clase. |
| `__call__` | `MiClase(*args, **kwargs)` — constructor síncrono seguro para hilos. Devuelve la instancia existente si ya se creó una (camino rápido: una lectura de atributo + comprobación de identidad); si no, adquiere el lock dedicado de la clase y crea la instancia con double-checked locking. |
| `__acall__` | `await MiClase.__acall__(*args, **kwargs)` — constructor seguro para `asyncio`, **invocado explícitamente** (Python no llama a `__acall__` automáticamente desde `MiClase(...)`). Usa el `threading.Lock` de la clase para coordinar la creación con las llamadas síncronas. |

Tanto `__call__` como `__acall__` leen/escriben el mismo slot
subyacente `cls._singleton_instance`, así que la vía que cree la
instancia primero "gana", y la otra vía la verá en su siguiente
comprobación.

---

## Ejemplos de uso

### `Final`: impedir la herencia

```python
from orionis.support.patterns.final.meta import Final

class ImmutableHeaders(metaclass=Final):
    def __init__(self, data: dict[str, str]) -> None:
        self._data = dict(data)

    def get(self, key: str) -> str | None:
        return self._data.get(key)

headers = ImmutableHeaders({"content-type": "application/json"})
print(headers.get("content-type"))  # "application/json"

try:
    class CustomHeaders(ImmutableHeaders):
        pass
except TypeError as exc:
    print(exc)  # "Cannot inherit from orionis final class 'ImmutableHeaders'"
```

### `Singleton`: uso síncrono

```python
from orionis.support.patterns.singleton.meta import Singleton

class AppSettings(metaclass=Singleton):
    def __init__(self) -> None:
        self.debug = False

a = AppSettings()
b = AppSettings()
print(a is b)  # True: ambas variables referencian la misma instancia

a.debug = True
print(b.debug)  # True: `a` y `b` son el mismo objeto
```

### `Singleton`: uso asíncrono

```python
import asyncio
from orionis.support.patterns.singleton.meta import Singleton

class ConnectionPool(metaclass=Singleton):
    def __init__(self) -> None:
        self.connections: list[str] = []

async def main() -> None:
    pool_a = await ConnectionPool.__acall__()
    pool_b = await ConnectionPool.__acall__()
    print(pool_a is pool_b)  # True

asyncio.run(main())
```

---

## Consideraciones de rendimiento y concurrencia

- **`Final`**: la comprobación de herencia solo se ejecuta una vez, en
  el momento de definir la clase (`__new__`), y solo recorre la tupla
  `bases` directa de la clase que se está creando — no tiene ningún
  costo en tiempo de ejecución para el acceso normal a atributos o
  llamadas a métodos en instancias posteriormente. Usa
  `base.__dict__.get("__is_final__", False)` en lugar de `getattr`, lo
  cual evita un recorrido completo del MRO, ya que `__is_final__`
  siempre se establece directamente en el objeto clase que lo posee,
  nunca se hereda.
- **Vías de `Singleton` (`__call__` y `__acall__`)**: después de crear
  la primera instancia, las llamadas leen el atributo cacheado y hacen
  una comparación de identidad sin adquirir locks. La primera creación
  comprueba de nuevo el valor cacheado mientras mantiene un lock guardado
  en la clase. Ambas APIs comparten ese lock, por lo que las llamadas
  síncronas y asíncronas concurrentes no crean instancias duplicadas.
  Almacenar el lock en cada clase también permite recolectar clases
  dinámicas cuando dejan de usarse.
- Ninguna de las dos metaclases realiza E/S; ambas son operaciones
  puras, en memoria y limitadas por CPU.

## Notas de diseño

- **Metaclases como garantías estructurales opcionales**: tanto `Final`
  como `Singleton` se aplican vía `metaclass=...` en lugar de por
  herencia de una clase base, manteniendo el comportamiento reforzado
  (no heredable / instancia única) ortogonal a la jerarquía de herencia
  propia de la clase.
- **`__is_final__` almacenado por clase, no heredado**: `Final` lee
  `base.__dict__` directamente (no `getattr`) específicamente para que
  la bandera nunca se "vea" accidentalmente por herencia — siempre se
  establece de nuevo en cada clase creada con la metaclase.
- **Double-checked locking**: `Singleton.__call__`/`__acall__` primero
  leen la instancia cacheada y luego vuelven a comprobarla bajo el lock
  compartido de la clase antes de construirla.
- **Invocación explícita de `__acall__`**: el modelo de datos de Python
  no invoca `__acall__` automáticamente cuando se escribe `MiClase(...)`
  dentro de un contexto `async def`; debe esperarse explícitamente como
  `await MiClase.__acall__()`. Esta es una API deliberadamente explícita
  en lugar de un despacho "mágico" implícito basado en el contexto de
  llamada.
- **`type.__setattr__` usado explícitamente**: ambas metaclases escriben
  atributos de clase (`__is_final__`, `_singleton_instance`) vía
  `type.__setattr__(cls, ...)` en lugar de una asignación de atributo
  normal, lo cual evita cualquier `__setattr__` personalizado que una
  subclase de la metaclase (o de la clase objetivo) pudiera definir.

## Notas de compatibilidad

- Requiere **Python 3.14+**, en línea con el resto del framework
  `orionis` (`requires-python = ">=3.14"` en `pyproject.toml`).
- Sin dependencias de terceros; solo usa `threading` de la librería
  estándar.
- Sin comportamiento específico de plataforma; ambas metaclases dependen
  únicamente del protocolo estándar de creación de tipos de CPython y de
  `threading.Lock`.
- Se usan internamente en `orionis.http.payload.estructures` (`Cookies`,
  `Headers`, `QueryParams`, vía `Final`) y en
  `orionis.environment.core.dot_env.DotEnv` (vía `Singleton`), pero
  ninguna de las dos metaclases depende de ninguna otra parte del
  framework.
