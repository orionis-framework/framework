# Orionis Structures (`orionis.support.structures`)

> Utilidad recursiva de congelado/descongelado profundo que preserva referencias para estructuras anidadas `dict`/`list`/`tuple`/`MappingProxyType`.
>
> 🇬🇧 English version: [README.md](README.md)

`orionis.support.structures` es un módulo utilitario minúsculo y sin
dependencias, construido alrededor de una sola clase, `FreezeThaw`, que
convierte contenedores mutables anidados en contenedores completamente
inmutables (y viceversa). Se usa internamente en el framework (por
ejemplo en `orionis.foundation.application.Application`) para tomar una
instantánea inmutable de árboles de configuración y obtener copias de
trabajo mutables e independientes de los mismos, pero no depende del
resto del framework y puede usarse de forma independiente en cualquier
proyecto.

---

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Descripción funcional del módulo](#descripción-funcional-del-módulo)
3. [Referencia de API](#referencia-de-api)
   - [`FreezeThaw`](#freezethaw-orionissupportstructuresfreezerfreezethaw)
4. [Ejemplos de uso](#ejemplos-de-uso)
5. [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
6. [Notas de diseño](#notas-de-diseño)
7. [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Requisitos

No se necesita instalación adicional además del propio framework:

```bash
pip install orionis
```

- **Python:** 3.14 o superior (el mismo mínimo que el resto del framework).
- **Dependencias:** ninguna más allá de la librería estándar de Python
  (`types.MappingProxyType`, `typing.Any`).

## Descripción funcional del módulo

| Tipo | Archivo | Propósito |
|---|---|---|
| `FreezeThaw` | [freezer.py](../freezer.py) | Clase utilitaria sin estado (todo `@staticmethod`) que convierte recursivamente estructuras `dict`/`list`/`tuple` en sus equivalentes inmutables (`freeze`) y estructuras `MappingProxyType`/`dict`/`list`/`tuple` de vuelta en estructuras mutables `dict`/`list` (`thaw`). |

`FreezeThaw` trata cuatro tipos como "contenedores": `dict`, `list`,
`tuple` y `MappingProxyType`. Todo lo demás (números, cadenas, `None`,
objetos personalizados, etc.) se trata como un escalar y se devuelve sin
cambios, por identidad, sin copiarlo ni envolverlo.

Correspondencia entre equivalentes mutables e inmutables usada por el
módulo:

| Mutable | Inmutable |
|---|---|
| `dict` | `MappingProxyType` |
| `list` | `tuple` |
| `tuple` | `tuple` (reconstruida para que cualquier contenido mutable anidado dentro también quede congelado) |

---

## Referencia de API

### `FreezeThaw` (`orionis.support.structures.freezer.FreezeThaw`)

Todos los miembros son `@staticmethod`; la clase nunca se instancia y no
mantiene estado propio.

| Método | Firma | Descripción |
|---|---|---|
| `_isContainer` | `_isContainer(obj: object) -> bool` | `True` si `obj` es un `dict`, `list`, `tuple` o `MappingProxyType`; `False` en caso contrario. Ayudante de clasificación interno (con prefijo de nombre privado, pero simple y sin efectos secundarios, por lo que también se ejercita directamente desde la suite de pruebas). |
| `freeze` | `freeze(obj: object) -> object` | Convierte recursivamente una estructura `dict`/`list`/`tuple` en su equivalente inmutable (`MappingProxyType`/`tuple`, incluyendo contenedores anidados). Las instancias de `MappingProxyType` y cualquier objeto que no sea contenedor se devuelven sin cambios. Devuelve `object` porque el tipo del resultado depende de la entrada (`MappingProxyType`, `tuple`, o el escalar original). |
| `thaw` | `thaw(obj: object) -> object` | Convierte recursivamente una estructura `MappingProxyType`/`dict`/`list`/`tuple` en un equivalente totalmente mutable (`dict`/`list`, incluyendo contenedores anidados). Cualquier objeto que no sea contenedor se devuelve sin cambios. Devuelve `object` porque el tipo del resultado depende de la entrada (`dict`, `list`, o el escalar original). |

Tanto `freeze()` como `thaw()`:

- Devuelven el objeto original **sin cambios** (misma identidad) para
  entradas que no son contenedores, incluyendo `None`.
- Devuelven un **nuevo** contenedor inmutable/mutable vacío para
  entradas vacías (`{}`/`MappingProxyType({})` para tipo diccionario,
  `()`/`[]` en los demás casos) — existe un camino rápido que se salta
  por completo la maquinaria de recorrido para contenedores vacíos.
- Preservan las **referencias compartidas**: si el mismo objeto anidado
  aparece más de una vez dentro de la entrada (por `id()`), cada
  ocurrencia se asigna al *mismo* objeto congelado/descongelado nuevo en
  lugar de duplicarse — esto también hace que las estructuras
  autorreferenciadas (un contenedor que se contiene a sí mismo) puedan
  procesarse de forma segura en lugar de provocar recursión infinita.
- Ninguno de los dos métodos lanza excepciones para los tipos de entrada
  soportados; no hay secciones `Raises` documentadas porque ninguna de
  las rutas de código para contenedores/escalares lanza excepciones por
  sí misma (mutar el *resultado* de `freeze()`, p. ej.
  `frozen["a"] = 1`, lanza el `TypeError` estándar de
  `MappingProxyType`/`tuple`, pero eso es comportamiento de la librería
  estándar, no algo que `FreezeThaw` lance por sí mismo).

---

## Ejemplos de uso

### Congelar un árbol de configuración

```python
from types import MappingProxyType
from orionis.support.structures.freezer import FreezeThaw

config = {
    "app": {"name": "Orionis", "debug": False},
    "allowed_hosts": ["localhost", "127.0.0.1"],
}

frozen = FreezeThaw.freeze(config)

print(isinstance(frozen, MappingProxyType))        # True
print(isinstance(frozen["app"], MappingProxyType)) # True
print(isinstance(frozen["allowed_hosts"], tuple))  # True

try:
    frozen["app"]["debug"] = True
except TypeError as exc:
    print(f"no se puede mutar la configuración congelada: {exc}")
```

### Descongelar para obtener una copia de trabajo mutable

```python
from orionis.support.structures.freezer import FreezeThaw

# `frozen` del ejemplo anterior
working_copy = FreezeThaw.thaw(frozen)

working_copy["app"]["debug"] = True
working_copy["allowed_hosts"].append("example.com")

print(working_copy["app"]["debug"])        # True
print(working_copy["allowed_hosts"])       # ["localhost", "127.0.0.1", "example.com"]
```

### Las referencias compartidas se preservan, no se duplican

```python
from orionis.support.structures.freezer import FreezeThaw

shared = {"role": "admin"}
data = {"user_a": shared, "user_b": shared}

frozen = FreezeThaw.freeze(data)
print(frozen["user_a"] is frozen["user_b"])  # True: misma instancia MappingProxyType
```

### Los escalares y las entradas ya inmutables pasan intactos

```python
from types import MappingProxyType
from orionis.support.structures.freezer import FreezeThaw

print(FreezeThaw.freeze(42) == 42)              # True (identidad, sin envolver)
print(FreezeThaw.freeze(None) is None)          # True

already_frozen = MappingProxyType({"a": 1})
print(FreezeThaw.freeze(already_frozen) is already_frozen)  # True
```

---

## Consideraciones de rendimiento y concurrencia

- Tanto `freeze()` como `thaw()` usan un **recorrido iterativo basado en
  pila** (una `list` explícita usada como pila LIFO) en lugar de
  llamadas a función recursivas, de modo que procesar una estructura muy
  anidada (por ejemplo, un árbol de configuración grande y profundamente
  anidado) no corre el riesgo de alcanzar el límite de recursión de
  Python como lo haría una implementación recursiva ingenua.
- Ambos métodos usan una caché indexada por `id()` (`dict[int, Any]`)
  para visitar cada objeto contenedor distinto una sola vez, dando
  tiempo y memoria `O(n)` en relación con el número total de nodos
  contenedores (más los escalares, que se visitan pero no se
  cachean). Las subestructuras compartidas/alias se convierten una sola
  vez y luego se reutilizan por referencia en cada lugar donde aparecen.
- `thaw()` además mantiene una lista `fixups` que contiene solo los
  pares padre/clave cuyo valor es a su vez un contenedor, de modo que la
  segunda pasada de "corregir referencias" cuesta `O(N_contenedores)` en
  lugar de volver a recorrer cada par clave/valor.
- `freeze()` corrige las referencias durante una pasada de abajo hacia
  arriba sobre la caché en orden inverso de inserción (hijos antes que
  padres), lo cual es correcto por construcción, ya que el recorrido
  basado en pila siempre inserta un padre en la caché antes que
  cualquiera de sus hijos.
- Los contenedores vacíos (`{}`, `[]`, `()`, `MappingProxyType({})`) y
  los escalares que no son contenedores toman un camino rápido `O(1)`
  sin ningún recorrido.
- `FreezeThaw` **no tiene locks, ni estado mutable compartido a nivel de
  módulo, ni E/S** — las dos constantes a nivel de módulo
  (`_CONTAINER_TYPES`, `_MUTABLE_TYPES`) son tuplas de tipos de solo
  lectura. Tanto `freeze()` como `thaw()` son funciones planas,
  síncronas y limitadas por CPU, y es seguro llamarlas concurrentemente
  desde varios hilos o tareas de `asyncio` siempre que la estructura de
  **entrada** no esté siendo mutada concurrentemente por otro hilo
  mientras se congela/descongela.

## Notas de diseño

- **Clase utilitaria sin estado**: `FreezeThaw` solo expone
  `@staticmethod`s y nunca está pensada para instanciarse; existe
  puramente para agrupar dos operaciones relacionadas y simétricas
  (`freeze`/`thaw`) bajo un mismo espacio de nombres.
- **DFS iterativo con pila explícita**: elegido en lugar de recursión
  específicamente para soportar estructuras arbitrariamente profundas
  (por ejemplo, diccionarios de configuración grandes y muy anidados)
  sin provocar `RecursionError`.
- **Memoización basada en identidad (caché por `id()`)**: ambas
  operaciones indexan su caché por `id(obj)` en lugar de por igualdad de
  valores, lo cual es lo que permite preservar (no duplicar) las
  referencias compartidas y lo que hace seguro procesar contenedores
  autorreferenciados en lugar de ciclar indefinidamente.
- **Simetría de tipos, no simetría perfecta**: `freeze()` convierte
  `dict` en `MappingProxyType` y `list`/`tuple` en `tuple`; `thaw()`
  convierte `MappingProxyType`/`dict` en `dict` y `list`/`tuple` en
  `list`. Una `tuple` congelada y luego descongelada se convierte en una
  `list`, no en una `tuple` — el ciclo completo preserva los *valores*,
  no el tipo de contenedor original exacto para las tuplas.
- **La entrada ya inmutable corta el proceso**: `MappingProxyType` se
  excluye deliberadamente de `_MUTABLE_TYPES`, así que `freeze()` la
  devuelve sin cambios (por identidad) en lugar de volver a envolverla —
  esto también explica por qué un valor `MappingProxyType` anidado
  dentro de un `dict` mutable se deja tal cual por `freeze()` en lugar
  de recorrerlo más a fondo.

## Notas de compatibilidad

- Requiere **Python 3.14+**, en línea con el resto del framework
  `orionis` (`requires-python = ">=3.14"` en `pyproject.toml`).
- Sin dependencias de terceros; solo usa `types.MappingProxyType` y
  `typing.Any` de la librería estándar.
- Sin comportamiento específico de plataforma; Python puro sin
  dependencias a nivel de sistema operativo.
- Se usa internamente en `orionis.foundation.application.Application`
  para congelar/descongelar árboles de configuración centrales durante
  el arranque, pero el módulo en sí no importa ni depende de ninguna
  otra parte del framework.
