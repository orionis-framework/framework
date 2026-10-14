# Enviar mensajes y manejar resultados

Mail separa la declaración del mensaje, la composición MIME y el transporte. Prepara remitente, contenido y política de entrega antes del primer envío.

## Enviar desde una aplicación inicializada

`MailProvider` registra `MailComposer` e `IMailManager` como singletons y fija la facade `Mail`. El composer necesita `IViewEngine` e `IStorageManager`, incluso si ese envío utiliza texto literal sin adjuntos. Un import no inicializa automáticamente todos esos servicios. Desde un servicio puedes recibir `IMailManager` por inyección; sus cadenas tienen el mismo comportamiento que la facade.

Las llamadas fluidas son síncronas y devuelven una cadena nueva: conserva el resultado de `Mail.to(...)` o encadénalo. La cadena anterior conserva sus destinatarios. Los terminales `send`, `raw` y `html` son async; hasta esperarlos no se renderizan vistas, leen archivos ni abre un transporte. El ejemplo necesita remitente global configurado y el mailer `file`:

```python
from orionis.mail import Content, Message
from orionis.support.facades import Mail


def address_message(message: Message) -> None:
    message.to("ana@example.com").subject("Monthly report")


async def send_report():
    return await Mail.mailer("file").send(
        Content(text="Your report is ready.", html="<p>Your report is ready.</p>"),
        callback=address_message,
    )
```

### Configurar callbacks correctamente

Un callback de envío directo recibe un `Message` mutable y exclusivo de esa operación. Puede ser sync o async, ejecutarse una sola vez y debe devolver `None` o el mismo `Message`; `False` no cancela el envío y es un error de composición. No lo guardes ni lo compartas entre envíos. El callback modifica remitente, destinatarios, subject y adjuntos, pero el cuerpo se declara por separado.

`send(mailable)` no acepta `data` ni callback adicionales: el mailable posee su contexto. `send(Content(...))` no acepta un segundo `data`, porque ya está en el objeto. Para `send("template", data, callback)` sí se admite el mapping de contexto. Cuando pasas una clase `Mailable`, el manager la construye por el contenedor; un constructor con valores de negocio simples normalmente se resuelve creando tú una instancia con esos valores.


```python
from orionis.mail import Content, Envelope, Mailable
from orionis.support.facades import Mail


class StatusMail(Mailable):
    def envelope(self) -> Envelope:
        return Envelope(subject="Status")

    def content(self) -> Content:
        return Content(text="All systems operational")


async def send_status():
    return await Mail.to("ana@example.com").send(StatusMail)
```

## Interpretar el resultado y los fallos

| Estado | Evidencia confirmada | No garantiza |
|---|---|---|
| `MailStatus.ACCEPTED` | SMTP aceptó todos los receptores previstos. | Entrega en mailbox o lectura. |
| `MailStatus.PARTIAL` | SMTP aceptó algunos y rechazó otros. | Que un reenvío completo sea seguro. |
| `MailStatus.STORED` | Se publicó un `.eml` completo en el filesystem. | Entrega a un servidor SMTP. |

El resultado incluye `message_id`, `mailer`, `driver`, `recipients`, `accepted_recipients`, `rejected_recipients` y `file_path` cuando procede. Un envío file no inventa una lista de aceptación SMTP. Registra IDs y estado de negocio sin exponer Bcc ni diagnósticos sensibles.

`MailCompositionException` y sus subclases indican declaraciones, callbacks, vistas o adjuntos inválidos antes del transporte. `MailConfigurationException` indica selección/configuración/factory inválida. `MailTransportException` representa el fallo del envío o publicación. La aplicación decide si corregir entrada, alertar o reintentar; el módulo no reintenta automáticamente.

Después de una desconexión o cancelación, el servidor podría haber aceptado el mensaje sin que el cliente haya confirmado el resultado. Cancelar el `await` no detiene de inmediato un worker síncrono SMTP/file. Un retry indiscriminado puede duplicar correo. Para `PARTIAL`, conserva aceptados y rechazados y aplica una política que no reenvíe ciegamente a todos. No se incluye clave de idempotencia ni deduplicación de transporte.

El siguiente ejemplo identifica las fronteras de error; vuelve a lanzar sin reintentar. Sustituye esos bloques por la política de tu servicio:

```python
from orionis.mail import MailStatus
from orionis.mail.exceptions import MailCompositionException, MailTransportException
from orionis.support.facades import Mail


async def publish_status():
    try:
        result = await (
            Mail.mailer("file")
            .fromAddress("status@example.com")
            .to("ana@example.com")
            .subject("Status")
            .raw("All systems operational")
        )
    except MailCompositionException:
        raise
    except MailTransportException:
        raise
    if result.status is MailStatus.PARTIAL:
        return {"status": result.status, "rejected": tuple(result.rejected_recipients)}
    return {"status": result.status, "message_id": result.message_id}
```

### Inspeccionar resultado

```python
from pathlib import Path
from orionis.mail import MailResult, MailStatus

result = MailResult(
    message_id="<stored@example.com>",
    mailer="archive",
    driver="file",
    status=MailStatus.STORED,
    recipients=("ana@example.com",),
    file_path=Path("archive/message.eml"),
)
assert result.status == "stored"
assert result.accepted_recipients == ()
assert result.file_path.name == "message.eml"
print(result.mailer)
```

## Envíos concurrentes y background

Las cadenas son independientes; el registro de factories es compartido y debe completarse durante boot. Cada envío crea un transporte; SMTP abre una conexión por operación. El código actual prepara primero texto, después HTML y luego cada adjunto secuencialmente antes de componer MIME fuera del loop. No promete preparación paralela de adjuntos ni conexiones SMTP persistentes.

Para enviar después de una respuesta puedes adjuntar una `BackgroundTask` a esa respuesta. Eso sigue siendo trabajo del proceso y no sobrevive a su terminación. Para un envío persistente usa queues con una conexión durable y una estrategia explícita de retry. No hay método `Mail.queue()` en esta API. No almacenes objetos `Message` ni conexiones SMTP en payloads de jobs; conserva identificadores o datos serializables necesarios para reconstruir la declaración.


### Manager/facade fluida

`IMailManager` y `Mail` ofrecen `mailer`, `fromAddress`, `to`, `cc`, `bcc`, `replyTo`, `subject`, `attach`, `send`, `raw`, `html` y `extend`. El mailer es una entrada de configuración; `driver` elige implementación.

### Sobrecargas terminales

- `await Mail.send(mailable_or_class)`
- `await Mail.send("emails.welcome", data, callback)`
- `await Mail.send(Content(...), callback=callback)`
- `await Mail.raw(text, callback=None)`
- `await Mail.html(html, callback=None)`

---

[Índice](README.md) · [foundation](../../../foundation/docs/es/README.md) · [background](../../../background/docs/es/README.md) · [queues](../../../queues/docs/es/README.md)
