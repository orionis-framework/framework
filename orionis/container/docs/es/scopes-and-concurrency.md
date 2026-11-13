# Scopes, aislamiento y concurrencia

Un servicio `scoped` pertenece a una unidad de trabajo delimitada por `async with`. Guarda aquí estado de solicitud o comando. Un singleton que retiene una referencia a ese estado prolonga su vida fuera del scope y rompe el aislamiento: inyecta los servicios de solicitud en el consumidor que vive dentro del scope.

## Errores y casos límite

- Registro duplicado lanza `ValueError` salvo override.
- Relaciones incorrectas lanzan `TypeError`.
- Scoped sin scope, scope cerrado o reentrada lanzan `RuntimeError`.
- Los ciclos lanzan `CircularDependencyException`; el stack es local a la tarea y distingue instancias de contenedor. Construir la misma clase en otro contenedor independiente no produce un falso ciclo.
- Parámetros sin anotación/default requieren argumento explícito.
- Clase se autoconstruye; alias ausente no.
- Fachada antes de boot o scoped fuera de scope lanza `RuntimeError`.
- No cambies bindings globales concurrentemente durante requests.

## Rendimiento y concurrencia

Container es singleton por subclase. La publicación y la inicialización usan locks de hilo con doble comprobación para que constructores concurrentes no reinicien los bindings de una instancia inicializada. Los planes se almacenan. La primera construcción singleton, scoped o de provider usa `asyncio.Lock` por clave para compartir resultado dentro de un loop.

Locks se reemplazan entre loops: serialización es por loop, no global cross-loop. Registro no está bloqueado. `ContextVar` aísla tareas aunque hijas heredan scope.

Fachadas fijadas evitan resolución repetida; scoped la evitan para preservar aislamiento.

Los dispatchers de facades sin fijar usan una caché LRU compartida de hasta 1024 pares de clase y atributo. El acceso repetido conserva la identidad del dispatcher mientras el par permanece en caché; su expulsión libera la referencia almacenada. Los métodos especiales de Python ausentes lanzan `AttributeError` en lugar de crear un dispatcher de servicio.

`scope.get()` comparte una corrutina almacenada como tarea y guarda su resultado. Al terminar, no sobrescribe un valor reemplazado mediante `set()` ni repone una entrada eliminada por `clear()`; el llamador que ya esperaba sigue recibiendo el resultado de su tarea original. Terminar después de salir del scope lanza `RuntimeError`. Cancelar un llamador que espera propaga la cancelación a la tarea compartida.

## Configuración

El contenedor no consume configuración ni variables. Bindings proceden de providers core/aplicación y registro runtime. Listas/metadata de providers pertenecen al bootstrap, no a sección `container`.

## Ejemplos

### Reutilizar servicio dentro de un scope

```python
import asyncio

from orionis.container.container import Container


class RequestState:
    pass


class ScopeContainer(Container):
    pass


async def main() -> None:
    container = ScopeContainer()
    container.scoped(None, RequestState)
    async with container.beginScope():
        first = await container.make(RequestState)
        second = await container.make(RequestState)
        print(first is second)  # True
    async with container.beginScope():
        third = await container.make(RequestState)
        print(first is third)  # False


asyncio.run(main())
```

## Cerrar recursos y tareas

La salida del scope limpia sus referencias e invalida el contexto. No llama automáticamente `close()` ni `aclose()` sobre cualquier servicio y no espera tareas arbitrarias que hayas creado. El propietario del recurso debe cerrarlo mediante su context manager o un bloque `finally`. Si una tarea hija necesita usar un servicio scoped, espera su finalización dentro del scope; no la dejes ejecutándose después de salir. Tampoco se aplica un mecanismo de captura de dependencias que impida guardar un objeto scoped en un singleton: controla esa relación en el diseño de tus servicios.

Al almacenar una corrutina nativa sin iniciar, el scope asume su custodia hasta que se solicite. Reemplazar ese valor, limpiar el scope o salir de él cierra esa corrutina sin iniciar. Reasignar el mismo objeto lo conserva. Esta limpieza no cancela tareas prestadas ni cierra corrutinas ya ejecutándose o suspendidas en otro lugar.

## Fuentes y siguientes pasos

[manager.py](../../context/manager.py) · [scope.py](../../context/scope.py) · [container.py](../../container.py)

[Volver al índice del módulo](README.md).
