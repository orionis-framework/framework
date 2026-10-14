# Escribir y enviar jobs

## Declarar una clase importable

Los workers descubren jobs en la ruta `app_jobs`, normalmente `app/jobs`. Mantén la clase a nivel de módulo: la identidad persistida es `module:qualname`, que debe seguir disponible cuando otro proceso consuma el mensaje.

```python
from orionis.queues import BaseJob


class GenerateReport(BaseJob):
    __slots__ = ("report_id",)
    report_id: str
    tries = 3
    timeout = 30.0
    backoff = (1.0, 5.0)

    def __init__(self, report_id: str) -> None:
        self.report_id = report_id

    async def handle(self) -> None:
        print(f"Generate report {self.report_id}")


job = GenerateReport("report-42")
assert job.report_id == "report-42"
```

Este programa solo construye un job. En una aplicación real reemplaza la salida por el servicio de generación. `handle` puede solicitar servicios mediante parámetros tipados: el worker abre un scope, registra `JobContext` e invoca el método mediante el contenedor. Pasa identidades primitivas en el constructor y resuelve servicios/modelos al ejecutar; no serialices un cliente HTTP, conexión, request ni modelo activo.

## Estado persistido y seguridad

El serializer recoge slots públicos y anotaciones que no sean `ClassVar` a lo largo de la jerarquía. `tries`, `timeout` y `backoff` son política de clase, no estado. Se admiten strings, bytes, enteros, floats finitos, booleanos, `None` y listas/tuplas/diccionarios anidados con claves string. Objetos arbitrarios, atributos privados o estado de instancia no declarado son rechazados.

La carga tiene límite de 1 MiB y profundidad de estado de 32. Guarda documentos grandes en almacenamiento y envía una clave. El estado utiliza MessagePack y preserva tuplas mediante una extensión; no carga pickle ni importa clases a partir de una identidad no confiable. Solo decodifica clases registradas. El envelope exterior se codifica como JSON, tiene versión 1 y contiene identidad, routing y política de ejecución.

Puedes verificar el round trip sin ejecutar trabajo:

```python
from orionis.queues.serializer import JobSerializer

serializer = JobSerializer()
serializer.register(GenerateReport)
identity, payload = serializer.encode(job)
restored = serializer.decode(identity, payload)
assert isinstance(restored, GenerateReport)
assert restored.report_id == "report-42"
```

El provider descubre clases durante boot; el manager también registra el tipo al enviar. Esa inscripción en el productor no reemplaza el descubrimiento del consumidor. Renombrar/mover una clase puede dejar mensajes pendientes con identidad desconocida; conserva compatibilidad o drena/migra esos mensajes durante el despliegue.

## Enviar y seleccionar destino

En una aplicación inicializada con el job instalado en su módulo:

```python
from orionis.support.facades import Queue


async def enqueue_report() -> str:
    return await (
        Queue.dispatch(GenerateReport("report-42"))
        .onConnection("database")
        .onQueue("reports")
        .delay(5.0)
    )
```

La conexión selecciona backend/almacén; la cola es un canal lógico dentro de esa conexión; el delay está en segundos. Sin selección se usan defaults. Un delay cero significa disponible inmediatamente, no ejecución inline salvo en `sync`. Ese driver rechaza delay no cero.

`PendingDispatch` no tiene destructor que envíe al perder referencia: descartarlo sin `await` no hace nada. Se puede esperar varias veces y el resultado se comparte, enviando una sola vez; opciones solo se modifican antes del primer await. No reutilices el mismo objeto como un segundo mensaje y no modifiques el job mientras otro consumidor espera su envío.

Este ejemplo verifica el protocolo sin backend:

```python
import asyncio
from orionis.queues import PendingDispatch


async def prove_dispatch() -> None:
    calls = []

    async def submit(job, connection, queue, delay):
        calls.append((connection, queue, delay))
        return "job-1"

    pending = PendingDispatch(submit, GenerateReport("report-42"))
    pending.onQueue("reports").delay(2.0)
    assert calls == []
    assert await pending == "job-1"
    assert await pending == "job-1"
    assert len(calls) == 1


asyncio.run(prove_dispatch())
```

`QueueConfigurationError` identifica política/routing inválidos; `QueuePayloadError`, estado no serializable; `UnknownJobError`, identidad no registrada; `QueueDispatchError`, cambios inválidos del envío o limitaciones del driver sync. Captura el error alrededor del `await`: construir el pending no valida todavía todo el payload.
