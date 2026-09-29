# Orionis Inspirational

> Un servicio pequeño y sin dependencias externas que devuelve una frase
> inspiradora al azar.
>
> 🇬🇧 English version: [README.md](README.md)

`orionis.inspirational` es un módulo utilitario incluido con el Orionis
Framework. Trae una colección curada de frases y un servicio mínimo,
`Inspire`, que elige una al azar. Se usa, entre otras cosas, en el comando
de consola `app:inspire` que se genera por defecto en todo proyecto nuevo de
Orionis, como ejemplo tipo "hola mundo" de un comando con un servicio
inyectado.

---

## Tabla de contenidos

1. [Requisitos](#requisitos)
2. [Qué problema resuelve](#qué-problema-resuelve)
3. [Estructura del módulo](#estructura-del-módulo)
4. [Referencia de la API](#referencia-de-la-api)
   - [`IInspire` (contrato)](#iinspire-contrato)
   - [`Inspire`](#inspire)
   - [`INSPIRATIONAL_QUOTES`](#inspirational_quotes)
5. [Ejemplos de uso](#ejemplos-de-uso)
6. [Notas de diseño](#notas-de-diseño)
7. [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
8. [Notas de compatibilidad](#notas-de-compatibilidad)

---

## Requisitos

No se necesita ningún paso de instalación adicional más allá de
`pip install orionis`. El módulo solo utiliza la biblioteca estándar de
Python (`secrets`, `typing`, `abc`) — no tiene dependencias de terceros.

## Qué problema resuelve

Las aplicaciones (y el propio andamiaje del framework) a veces necesitan un
pequeño elemento de "texto decorativo" autocontenido — una frase motivadora
para imprimir en un comando de consola, una pantalla de bienvenida, un
banner de logs, etc. `orionis.inspirational` resuelve esto de la forma más
simple posible:

- Un conjunto de datos de solo lectura con frases curadas (`quotes.py`).
- Un servicio mínimo (`Inspire`) que expone una única operación: elegir una
  frase al azar.
- Un contrato abstracto (`IInspire`) para que el servicio pueda tipar
  dependencias, simularse (mocks) o sustituirse por una implementación
  personalizada (por ejemplo, una que obtenga frases de una API remota) sin
  tocar el código que lo consume.

Es intencionalmente minimalista: no hay caché, no hay persistencia y no
hay acceso a red involucrado.

## Estructura del módulo

```
orionis/inspirational/
├── __init__.py          # Re-exportación pública: Inspire
├── inspire.py             # Implementación del servicio Inspire
├── quotes.py               # Dataset INSPIRATIONAL_QUOTES (361 frases curadas)
└── contracts/
    ├── __init__.py         # Re-exportación pública: IInspire
    └── inspire.py           # Contrato abstracto IInspire
```

Dirección de dependencia interna: `inspire.py` depende de
`contracts/inspire.py` (para implementar `IInspire`) y de `quotes.py` (como
su dataset por defecto). No existen otras dependencias internas ni externas.

## Referencia de la API

### `IInspire` (contrato)

`orionis.inspirational.contracts.inspire.IInspire`

Clase base abstracta (`abc.ABC`) que define el contrato público que debe
seguir cualquier implementación de "inspire".

```python
class IInspire(ABC):
    @abstractmethod
    def random(self) -> dict: ...
```

| Miembro | Descripción |
| --- | --- |
| `random() -> dict` | Debe devolver un diccionario con las claves `quote` (`str`) y `author` (`str`). Las implementaciones siempre deben devolver una frase válida, recurriendo a una frase por defecto cuando no hay datos disponibles. |

Usa este contrato para tipar dependencias
(`def handle(self, inspire: IInspire)`) o para proveer una implementación
alternativa (para pruebas, o una fuente de datos distinta a la lista
incluida).

### `Inspire`

`orionis.inspirational.inspire.Inspire(IInspire)`

Implementación concreta y sin dependencias externas de `IInspire`. Declara
`__slots__` (`_count`, `_quotes`), por lo que las instancias no tienen
`__dict__` y no pueden ganar atributos arbitrarios en tiempo de ejecución.

```python
Inspire(quotes: list[dict] | None = None) -> None
```

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `quotes` | `list[dict] \| None` | Colección personalizada opcional de frases. Cada elemento debe ser un `dict` que contenga al menos `quote` (`str`) y `author` (`str`). Si es `None` o una lista vacía, se usa en su lugar el dataset incluido `INSPIRATIONAL_QUOTES` (361 entradas). |

Excepciones:

| Excepción | Cuándo ocurre |
| --- | --- |
| `TypeError` | Algún elemento de `quotes` no es un `dict`. |
| `ValueError` | Algún elemento de `quotes` no tiene la clave `quote` o `author`. |

La validación solo se ejecuta cuando se pasa un argumento `quotes`
personalizado — el dataset por defecto es confiable y no se revalida en
cada instanciación.

#### `Inspire.random() -> dict`

Devuelve una frase al azar como un diccionario con las claves `quote` y
`author`.

- Usa `secrets.choice(...)` (un generador aleatorio criptográficamente
  seguro) para elegir un elemento de la lista interna — no `random.choice`.
- Si la colección interna de frases está vacía (solo posible si la
  instancia fue mutada después de construida, ya que el constructor nunca
  permite llegar a un estado final vacío por la vía por defecto), se
  devuelve una frase de respaldo fija en lugar de lanzar una excepción:

  ```python
  {
      "quote": "Greatness is not measured by what you build, "
               "but by what you inspire others to create.",
      "author": "Raul M. Uñate",
  }
  ```

Este método nunca lanza excepciones ni devuelve `None` — siempre retorna un
`dict` válido con ambas claves pobladas.

### `INSPIRATIONAL_QUOTES`

`orionis.inspirational.quotes.INSPIRATIONAL_QUOTES: tuple[dict, ...]`

Una tupla inmutable de 361 diccionarios `{"quote": str, "author": str}`
curados, usada como dataset por defecto por `Inspire` cuando no se
proporciona una lista personalizada. Se expone a nivel de módulo para que
pueda importarse directamente si solo se necesitan los datos crudos (por
ejemplo, para poblar una base de datos, construir un selector
personalizado, etc.).

```python
from orionis.inspirational.quotes import INSPIRATIONAL_QUOTES

len(INSPIRATIONAL_QUOTES)  # 361
```

## Ejemplos de uso

### Uso básico — frase aleatoria con el dataset por defecto

```python
from orionis.inspirational import Inspire

inspire = Inspire()
result = inspire.random()

print(f"{result['quote']} — {result['author']}")
```

### Proveer una lista personalizada de frases

```python
from orionis.inspirational import Inspire

my_quotes = [
    {"quote": "Ship it.", "author": "Anonymous"},
    {"quote": "Done is better than perfect.", "author": "Sheryl Sandberg"},
]

inspire = Inspire(quotes=my_quotes)
print(inspire.random())  # uno de los dos dicts anteriores, elegido al azar
```

### Una entrada inválida lanza la excepción de inmediato

```python
from orionis.inspirational import Inspire

# TypeError: los elementos deben ser diccionarios.
Inspire(quotes=["not a dict"])

# ValueError: cada diccionario debe contener 'quote' y 'author'.
Inspire(quotes=[{"quote": "Missing author"}])
```

### Dependiendo del contrato abstracto

```python
from orionis.inspirational.contracts.inspire import IInspire
from orionis.inspirational import Inspire


def print_daily_quote(service: IInspire) -> None:
    data = service.random()
    print(f"\"{data['quote']}\"\n— {data['author']}")


print_daily_quote(Inspire())
```

### Uso real: comando de consola con el servicio inyectado

Así es como el módulo se usa en el comando incluido `app:inspire`
(`app/console/commands/inspire_command.py`). El contenedor de Orionis
resuelve `Inspire` automáticamente porque es una clase concreta cuyos
parámetros de constructor son todos opcionales, por lo que no se requiere
ningún registro (binding) explícito:

```python
from orionis.console.base import BaseCommand
from orionis.inspirational import Inspire


class InspireCommand(BaseCommand):
    signature: str = "app:inspire"
    description: str = "Prints a random inspirational quote."

    async def handle(self, inspire: Inspire) -> None:
        quote, author = inspire.random().values()
        print(f"{quote} — {author}")
```

## Notas de diseño

Las siguientes son notas informativas sobre decisiones de diseño ya
existentes en este módulo — describen *por qué* el código se comporta como
lo hace, no una propuesta de cambio.

- **`__slots__`**: `Inspire` declara `__slots__ = ("_count", "_quotes")`
  para evitar el costo de un `__dict__` por instancia, ya que el servicio no
  mantiene ningún estado dinámico más allá de la lista de frases y su
  longitud cacheada.
- **Longitud cacheada (`_count`)**: la cantidad de frases se calcula una
  sola vez en la construcción y se reutiliza en cada llamada a `random()`
  para evitar invocar `len(...)` repetidamente y para que la comprobación de
  "lista vacía" sea una simple comparación de enteros.
- **Fallback como `ClassVar`**: `_FALLBACK` se declara como `ClassVar[dict]`,
  compartido por todas las instancias en lugar de duplicarse por instancia,
  ya que se trata de datos constantes.
- **`secrets.choice` en lugar de `random.choice`**: el módulo prefiere el
  generador criptográficamente seguro del módulo `secrets` para seleccionar
  frases. Esto no tiene implicaciones de seguridad prácticas para este caso
  de uso (las frases no son datos sensibles), pero es el generador
  realmente usado por la implementación, así que quienes consuman el
  módulo no deben asumir propiedades estadísticas específicas del módulo
  `random` de Python (por ejemplo, fijar la semilla con
  `random.seed(...)` no tiene ningún efecto sobre `Inspire.random()`).
- **Diseño orientado a contrato**: `Inspire` implementa `IInspire`, un
  `ABC` con un único método abstracto. Esto permite sustituir el servicio
  por una implementación distinta (por ejemplo, frases desde una fuente
  externa) en cualquier lugar donde se tipe como `IInspire`, sin cambiar el
  código consumidor.
- **Sin proveedor/facade**: a diferencia de otros servicios de Orionis, este
  módulo no incluye un service provider ni un facade. `Inspire` está
  pensado para usarse mediante instanciación directa o inyección por
  constructor, apoyándose en la capacidad del contenedor de construir
  automáticamente clases concretas que no exponen argumentos de constructor
  obligatorios.

## Consideraciones de rendimiento y concurrencia

- `Inspire.random()` es una operación síncrona, ligada a CPU y de bajo
  costo de asignación de memoria (una única llamada a `secrets.choice`
  sobre una secuencia en memoria). No realiza ningún I/O, por lo que no
  necesita ser esperada (`await`) y no bloquea un event loop de ninguna
  forma relevante en la práctica.
- Las instancias de `Inspire` son seguras para compartir y reutilizar;
  tanto `_quotes` como `_count` se fijan una sola vez en `__init__` y ningún
  método público las muta después. Las llamadas concurrentes a `random()`
  desde múltiples hilos o tareas asíncronas sobre la misma instancia son
  seguras siempre que el código externo no acceda a los atributos privados
  (`_quotes`, `_count`) y los mute directamente.
- El dataset por defecto `INSPIRATIONAL_QUOTES` es una tupla a nivel de
  módulo construida una sola vez al importar, y compartida por cada
  instancia de `Inspire()` creada sin un argumento `quotes` personalizado —
  no se hace ninguna copia por instancia.
- La validación de listas `quotes` personalizadas es `O(n)` respecto a la
  cantidad de elementos y solo se ejecuta una vez, en la construcción — no
  en cada llamada a `random()`.

## Notas de compatibilidad

- **Versión mínima de Python**: 3.14+ (requerida por el Orionis Framework
  en su conjunto; este módulo en particular solo depende de
  características de la biblioteca estándar disponibles desde versiones
  mucho anteriores).
- **Dependencias**: ninguna más allá de la biblioteca estándar de Python
  (`secrets`, `typing`, `abc`).
- **Anotaciones de tipos**: el módulo usa la sintaxis de uniones de PEP 604
  (`list[dict] | None`) y `ClassVar` de `typing`.
