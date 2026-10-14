# Dependencias, descubrimiento y referencia

## API pública

### `Reflection`

- `instance(value)`, `abstract(cls)`, `concrete(cls)`, `module(name)` y `callable(fn)` construyen wrappers.
- `isAbstract`, `isConcreteClass`, `isInstance`, `isGeneric`, `isProtocol` e `isTypingConstruct` aplican clasificaciones de Orionis.
- `isAsyncGen`, `isAsyncGenFunction`, `isAwaitable`, `isBuiltIn`, `isClass`, `isCode`, `isCoroutine`, `isCoroutineFunction`, `isDataDescriptor`, `isFrame`, `isFunction`, `isGenerator`, `isGeneratorFunction`, `isGetSetDescriptor`, `isMemberDescriptor`, `isMethod`, `isMethodDescriptor`, `isModule`, `isRoutine` e `isTraceback` exponen predicados de runtime.

### `ReflectionCallable`

Proporciona `getCallable`, `getName`, `getModuleName`, `getModuleWithCallableName`, `getDocstring`, `getSourceCode`, `getFile`, `getSignature`, `getDependencies` y `clearCache`. Su protocolo de items es una pequeña caché en memoria accesible al usuario.

### Wrappers de clase e instancia

Ambas familias exponen identidad, módulo, docstring, bases, fuente, archivo, anotaciones, atributos, métodos, propiedades, firmas inspect, firmas de dependencias y limpieza de caché. Los numerosos métodos `getPublic*`, `getProtected*` y `getPrivate*` seleccionan visibilidad; `Sync` y `Async` refinan el tipo de método. Los wrappers concretos y de instancia también permiten mutación controlada de atributos/métodos.

`ReflectionAbstract` ofrece la misma superficie orientada a lectura para clases abstractas y conserva la semántica de miembros abstractos.

### `ReflectionModule`

Importa un módulo dotted y expone clases, constantes, funciones, imports, fuente y archivo. Los getters dividen clases y constantes por visibilidad; los de funciones separan además sync de async. Su protocolo mapping lee o muta atributos del módulo.

### `ReflectDependencies` y `Signature`

`constructorSignature()`, `methodSignature(name)` y `callableSignature()` devuelven un `Signature`. La entidad ofrece predicados y selectores: `hasParameters`, `noArgumentsRequired`, `hasUnresolvedArguments`, `getResolved`, `getUnresolved`, `getAllOrdered`, `getPositionalOnly`, `getKeywordOnly`, conversiones y `arguments()`.

### `ModuleInspector`

- `discoverModules(base_path, target_path)` devuelve módulos dotted bajo una base segura.
- `loadClass(module_path, class_name)` o `loadClass(metadata=...)` importa una clase.
- `fileImportsAny(path, targets, allow_empty=False)` analiza imports sin ejecutar el archivo.
- `discoverFrozenDataclasses(modules)` importa módulos y devuelve dataclasses frozen declaradas allí.

## Flujos de trabajo comunes

### Construir argumentos del contenedor

Refleje el constructor o handler seleccionado. Resuelva valores de `Signature.resolved` desde el contenedor o decodificador de schema y exija al llamador los builtins sin resolver o parámetros sin anotación. Conserve `ordered` e `is_keyword_only` al invocar el objetivo.

### Descubrir componentes de aplicación

Use `discoverModules()` bajo una raíz conocida, filtre opcionalmente archivos con `fileImportsAny()` y cargue una clase declarada con `loadClass()`. Orionis aplica este patrón a comandos, migraciones, seeders, entidades de configuración y jobs en cola.

### Inspeccionar código sin mutarlo

Elija el wrapper más específico y use sus getters clasificados. Recuperar fuente/archivo puede fallar para objetos dinámicos o builtin; aun así pueden estar disponibles metadatos y firmas inspect. Trate diccionarios/listas mutables devueltos como resultados de reflexión, no como registros vivos autoritativos.

### Modificar miembros reflejados

`setAttribute`, `removeAttribute`, `setMethod`, la asignación de items de módulo y su borrado afectan la clase, instancia o módulo real. Limpie la caché tras mutación externa; los métodos de mutación del wrapper invalidan los datos afectados. Restrinja esta capacidad a bootstrap, pruebas y metaprogramación controlada.

## Configuración

Este módulo no tiene archivo de configuración de aplicación, variables de entorno, service provider, facade ni ajustes de I/O externo. Sus constantes operativas relevantes son límites de implementación: las firmas usan cachés LRU de 1.024 entradas, el descubrimiento excluye `__pycache__` y `site-packages`, y se omiten nombres reconocidos de entornos virtuales cuando contienen `pyvenv.cfg`.

## Integración con Orionis

El contenedor usa firmas de dependencias para resolver constructores e invocaciones sin inspeccionarlos repetidamente. Foundation descubre dataclasses frozen de configuración. Console descubre módulos de comandos; database descubre migraciones y seeders; queues carga clases de jobs; realtime lee metadatos de handlers. Estos consumidores importan utilidades concretas directamente en vez de resolver un servicio del contenedor.

Como la inspección está por debajo del contenedor, el paquete no depende de una instancia de aplicación. Puede usarse en bootstrap y herramientas antes de iniciar Orionis.

## Errores y casos límite

- Cada wrapper rechaza una categoría incorrecta; por ejemplo, reflexión concreta rechaza clases abstractas, builtin, genéricas, protocolos y construcciones de typing.
- `ReflectionInstance` rechaza objetos de clase, instancias builtin/ABC e instancias cuya clase se define en `__main__`.
- `ReflectionCallable` acepta funciones Python, métodos ligados, lambdas y callables con `__code__`; otros callables pueden rechazarse.
- Buscar fuente y archivo puede producir `AttributeError`, `TypeError` o errores de inspección para objetos generados, interactivos o builtin.
- Métodos/propiedades desconocidos producen `AttributeError`; nombres de mutación inválidos y métodos no callable fallan en validación.
- Anotaciones builtin requeridas como `int` quedan sin resolver intencionalmente; un valor predeterminado resuelve el parámetro desde su tipo concreto.
- Las referencias futuras se resuelven cuando es posible. Los nombres no disponibles permanecen como metadatos conservadores sin importarlos especulativamente.
- `discoverModules` falla si el objetivo queda fuera de la base. El análisis AST devuelve `False` para archivos ausentes, inválidos o no decodificables.
- Descubrir módulos y dataclasses frozen importa código cuando así se documenta; no lo ejecute sobre paquetes no confiables.

## Rendimiento y concurrencia

Los scans de clase/miembros recorren una vez y se guardan por wrapper. Las firmas inspect y de dependencias se memoizan, y la carga de módulos/clases combina la caché de importación de Python con una caché de clases de Orionis. Reutilice wrappers en hot paths y llame `clearCache()` solo tras mutación intencional.

Las cachés son locales al proceso. Las lecturas sirven para concurrencia normal bajo las garantías del runtime, pero mutar objetos reflejados y limpiar cachés no es transaccional. No modifique una clase/módulo compartido mientras otros threads o tasks lo inspeccionan o invocan. El recorrido del filesystem es síncrono y corresponde a bootstrap/herramientas, no al hot path de solicitudes.

## Compatibilidad

Orionis declara Python 3.14+. La reflexión depende del comportamiento de inspección de CPython/Python, incluidos descriptores, `inspect.signature`, resolución de anotaciones, name mangling y metadatos de importación. Objetos de extensiones, funciones generadas dinámicamente, aplicaciones congeladas y runtimes alternativos pueden no exponer fuente o archivo aunque otros métodos funcionen.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `reflection.py` | Factory y predicados generales de clasificación. |
| `callables/` | Metadatos, código, firma inspect y dependencias de funciones/métodos. |
| `abstract/` | Reflexión y clasificación de miembros de clases abstractas. |
| `concretes/` | Reflexión, mutación y firmas de clases concretas. |
| `instances/` | Estado de instancia y reflexión de miembros/propiedades de clase. |
| `modules/reflection.py` | Clases, constantes, funciones, código y caché de módulos importados. |
| `modules/inspector.py` | Descubrimiento, análisis AST, carga de clases y dataclasses frozen. |
| `dependencies/` | Resolución de firmas y entidades `Argument` / `Signature`. |
| `*/contracts/` | Contratos abstractos para cada especialización. |

## Ejemplos

### Analizar argumentos de inyección

```python
from orionis.introspection import ReflectDependencies


class Repository:
    pass


def handler(repository: Repository, raw, *, limit=25):
    return repository, raw, limit


signature = ReflectDependencies(handler).callableSignature()
assert list(signature.getAllOrdered()) == ["repository", "raw", "limit"]
assert list(signature.getResolved()) == ["repository", "limit"]
assert list(signature.getUnresolved()) == ["raw"]
assert signature.getKeywordOnly()["limit"].default == 25
print(signature.hasUnresolvedArguments())
```

### Descubrir módulos y cargar una clase

```python
from pathlib import Path
from orionis.introspection import ModuleInspector

root = Path.cwd()
modules = ModuleInspector.discoverModules(root, root / "orionis" / "introspection")
assert "orionis.introspection" in modules
assert "orionis.introspection.reflection" in modules
loaded = ModuleInspector.loadClass("pathlib", "Path")
assert loaded is Path
print(len(modules))
```

### Detectar imports mediante AST

```python
from pathlib import Path
from orionis.introspection import ModuleInspector

source = Path("orionis/container/entities/invocation.py")
targets = {"orionis.introspection.callables.reflection"}
assert ModuleInspector.fileImportsAny(source, targets)
assert not ModuleInspector.fileImportsAny(source, {"package.that.is.not.imported"})
print(source.name)
```

## Fuentes y siguientes pasos

[reflection.py](../../dependencies/reflection.py) · [signature.py](../../dependencies/entities/signature.py) · [inspector.py](../../modules/inspector.py)

[Volver al índice del módulo](README.md).
