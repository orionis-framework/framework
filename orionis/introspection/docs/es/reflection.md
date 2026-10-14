# Inspeccionar clases, funciones e instancias

## Inicio rápido

```python
from orionis.introspection import Reflection


def greet(name: str, punctuation: str = "!") -> str:
    """Build a greeting."""
    return f"Hello, {name}{punctuation}"


reflected = Reflection.callable(greet)
assert reflected.getName() == "greet"
assert list(reflected.getSignature().parameters) == ["name", "punctuation"]
assert reflected.getDocstring() == "Build a greeting."
print(reflected.getModuleWithCallableName())
```

## Conceptos principales

### Tipos de reflexión

`Reflection` es un punto de entrada estático. `callable()`, `abstract()`, `concrete()`, `instance()` y `module()` validan la entrada y devuelven un wrapper especializado. Los predicados reflejan `inspect` para funciones, métodos, clases, módulos, generadores, corrutinas, descriptores, frames, código, tracebacks y awaitables, y agregan comprobaciones de Orionis para clases concretas, instancias, genéricos, protocolos y construcciones de typing.

### Clasificación de miembros

Los wrappers de clase e instancia clasifican miembros públicos, protegidos, privados, dunder y “magic”. Los métodos se separan además entre instancia, clase y estáticos, y entre síncronos y asíncronos. Los nombres privados con mangling de Python se presentan sin el prefijo de clase, por lo que se usa el nombre del código fuente.

### Firmas de dependencias

`ReflectDependencies` convierte la firma de un constructor, método o callable en un `Signature` con mapas `resolved`, `unresolved` y ordenado por declaración de valores `Argument` inmutables. Se omiten `self`, `cls`, `*args` y `**kwargs`. Un parámetro con valor predeterminado se resuelve con el tipo de ese valor; una anotación no builtin se resuelve para buscar en el contenedor; un parámetro requerido sin anotación o solo builtin queda sin resolver. Las subclases de `msgspec.Struct` se marcan como schemas.

### Caché

Los wrappers guardan localmente scans, código fuente, archivos, anotaciones y firmas. El análisis de dependencias usa cachés LRU de módulo acotadas a 1.024 entradas. `ModuleInspector.loadClass()` también conserva clases por nombre totalmente calificado. La caché de métodos ligados evita retener instancias de controladores.

## Ejemplos

### Clasificar una clase concreta

```python
from orionis.introspection import Reflection


class Worker:
    category = "demo"

    def run(self, value: int) -> int:
        return value + 1

    async def stop(self) -> None:
        return None


reflected = Reflection.concrete(Worker)
assert reflected.getClassName() == "Worker"
assert "run" in reflected.getPublicSyncMethods()
assert "stop" in reflected.getPublicAsyncMethods()
assert reflected.getAttribute("category") == "demo"
print(reflected.getMethodSignature("run"))
```

### Reflejar un módulo importable

```python
from orionis.introspection import Reflection

module = Reflection.module("orionis.introspection.reflection")
assert module.hasClass("Reflection")
assert module.getClass("Reflection") is Reflection
assert module.getFile().endswith("reflection.py")
print(sorted(module.getPublicClasses()))
```

## Fuentes y siguientes pasos

[reflection.py](../../reflection.py) · [reflection.py](../../concretes/reflection.py) · [reflection.py](../../instances/reflection.py) · [reflection.py](../../callables/reflection.py)

[Volver al índice del módulo](README.md).
