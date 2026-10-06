# orionis.mail

> `orionis.mail` compone declaraciones inmutables, renderiza vistas, resuelve adjuntos de storage y entrega por SMTP, archivo o transportes personalizados.

## Descripción general

El pipeline separa declaración de efectos. `Envelope`, `Content` y `Attachment` validan intención inmutable; `Mailable` empaqueta intención reutilizable; `PendingMail` crea ramas fluidas independientes; `MailComposer` renderiza y serializa MIME completo; `MailManager` resuelve el transporte solo al esperar `send`, `raw` o `html`.

Los drivers incluidos son `smtp` y `file`. SMTP informa aceptación del servidor, no entrega final. File publica atómicamente archivos `.eml` privados y sirve para desarrollo, pruebas o archivo.

## Requisitos

- Python 3.14 o posterior.
- Una aplicación Orionis iniciada para facade `Mail`, inyección, vistas y discos configurados.
- Servidor SMTP accesible, o filesystem local con hard links para file.
- Remitente y destinatarios válidos; al menos un cuerpo y un destinatario por envío.

## Inicio rápido

```python
from orionis.mail import Address, Content, Envelope

sender = Address("notifications@example.com", "Example App")
envelope = Envelope(
    subject="Welcome",
    from_address=sender,
    to=("ana@example.com", "ops@example.com"),
    reply_to="support@example.com",
)
content = Content(text="Welcome to Orionis.", html="<p>Welcome to Orionis.</p>")
assert envelope.recipients() == ("ana@example.com", "ops@example.com")
assert content.text == "Welcome to Orionis."
print(sender.asHeader())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; declarar no realiza I/O.

## Conceptos principales

### Declaraciones inmutables

Direcciones, envelopes, contenido, adjuntos, preparados y resultados son snapshots inmutables. `Content.data` congela recursivamente contenedores propios. Los métodos `Mailable` son síncronos y declarativos, por lo que una instancia puede reutilizarse concurrentemente.

### Operaciones fluidas

Cada método de `PendingMail` devuelve una cadena nueva. `mailer`, `fromAddress`, `to`, `cc`, `bcc`, `replyTo`, `subject` y `attach` no renderizan, leen ni resuelven transporte. Los terminales son asíncronos. Un callback recibe un `Message` local, se ejecuta una vez y puede ser sync o async.

### Límite de composición

`MailComposer` renderiza vistas HTML/texto, lee adjuntos con `IStorageManager`, valida, construye MIME estándar y excluye Bcc de headers visibles mientras lo conserva en el envelope de transporte. La preparación termina antes de crear transporte, así que errores previos no abren SMTP ni publican parciales.

### Resultados

`MailStatus.ACCEPTED` significa que SMTP aceptó todos, `PARTIAL` algunos y `STORED` que se publicó un `.eml` completo. Ninguno demuestra entrega al buzón ni lectura.

## Estructura del módulo

| Ruta | Responsabilidad |
|---|---|
| `entities/` | Direcciones, envelopes, contenido, adjuntos, opciones, MIME, settings y resultados. |
| `mailable.py` | Abstracción declarativa reutilizable. |
| `message.py` | Configurador local del callback. |
| `pending.py` | Cadenas inmutables y terminales async. |
| `composer.py` | Vistas, storage, MIME y separación Bcc. |
| `manager.py` | Configuración, registro de drivers, remitente global y entrega. |
| `transports/smtp.py` | Frontera SMTP bloqueante fuera del event loop. |
| `transports/file.py` | Publicación atómica de `.eml` únicos. |
| `contracts/` | Interfaces de manager y transporte. |
| `provider.py`, `exceptions.py`, `enums/`, `types.py` | Wiring y tipos auxiliares. |

## API pública

La raíz exporta `Address`, `Attachment`, `Content`, `Envelope`, `MailResult`, `MailStatus`, `Mailable`, `Message` y `PendingMail`.

### Objetos de valor

- `Address(address, name=None)` acepta un addr-spec y normaliza su dominio IDNA.
- `Envelope(...)` valida headers, normaliza/deduplica destinatarios e impide que uno sea visible y Bcc.
- `Content(...)` requiere un cuerpo e impide conflictos view/literal por alternativa.
- `Attachment.fromStorage(...)` declara I/O diferido con rutas/metadatos seguros.
- `MailResult` devuelve ID, mailer/driver, destinatarios, estado y ruta opcional.

### `Mailable`

Implemente `envelope()` y `content()`; opcionalmente `attachments()`. Pase instancia a `Mail.send()` o la clase para construcción por contenedor en cada envío.

### Manager/facade fluida

`IMailManager` y `Mail` ofrecen `mailer`, `fromAddress`, `to`, `cc`, `bcc`, `replyTo`, `subject`, `attach`, `send`, `raw`, `html` y `extend`. El mailer es una entrada de configuración; `driver` elige implementación.

### Sobrecargas terminales

- `await Mail.send(mailable_or_class)`
- `await Mail.send("emails.welcome", data, callback)`
- `await Mail.send(Content(...), callback=callback)`
- `await Mail.raw(text, callback=None)`
- `await Mail.html(html, callback=None)`

## Flujos de trabajo comunes

### Crear correo reutilizable

Ponga destinatarios, asunto, cuerpo y adjuntos en `Mailable`. Mantenga sus métodos deterministas y sin I/O. Agregue destinatarios por envío o seleccione mailer derivando una cadena antes de `send`.

### Enviar vista o literal

Pase vista y datos a `send`, o use `raw`/`html`. Configure headers mediante callback o cadena previa. El callback debe devolver `None` o el mismo `Message`; sus excepciones son fallos de composición.

### Adjuntar archivos de storage

Declare una ruta lógica. El composer resuelve el disco durante envío, lee asíncronamente, elige media type explícito/storage/inferido y usa nombre override o basename.

### Agregar driver

Implemente `IMailTransport`, cree factory sync o async `(app, normalized_config)`, llame `manager.extend()` en startup y configure un mailer con ese driver. Duplicados se rechazan.

## Ejemplos

### Declarar un mailable reutilizable

```python
from orionis.mail import Content, Envelope, Mailable


class WelcomeMail(Mailable):
    def __init__(self, name: str) -> None:
        self.name = name

    def envelope(self) -> Envelope:
        return Envelope(subject="Welcome", to="ana@example.com")

    def content(self) -> Content:
        return Content(
            view="emails.welcome",
            text=f"Welcome, {self.name}.",
            data={"name": self.name},
        )


mail = WelcomeMail("Ana")
assert mail.envelope().subject == "Welcome"
assert mail.attachments() == ()
print(mail.content().text)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Configurar un mensaje

```python
from orionis.mail import Attachment, Message

message = (
    Message()
    .fromAddress("billing@example.com", "Billing")
    .to("ana@example.com", "Ana")
    .cc(["audit@example.com", "audit@example.com"])
    .subject("Invoice 42")
    .attach(Attachment.fromStorage("invoices/42.pdf"))
)
snapshot = message._snapshot()
assert snapshot.envelope().recipients() == ("ana@example.com", "audit@example.com")
assert snapshot.attachments[0].path == "invoices/42.pdf"
print(snapshot.subject)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; `_snapshot()` solo inspecciona la declaración.

### Declarar adjunto nombrado

```python
from orionis.mail import Attachment

attachment = Attachment.fromStorage(
    "reports/annual.pdf",
    disk="private",
    name="Annual Report.pdf",
    mime_type="application/pdf",
)
assert attachment.path == "reports/annual.pdf"
assert attachment.disk == "private"
assert attachment.name == "Annual Report.pdf"
print(attachment.mime_type)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; no hubo acceso a storage.

### Construir ramas independientes

```python
from orionis.mail import PendingMail


async def deliver(*args, **kwargs):
    raise AssertionError("declarations must not deliver")


base = PendingMail(deliver)
first = base.to("first@example.com")
second = base.to("second@example.com")
assert first is not base and second is not base and first is not second
assert base._options.to == ()
assert first._options.to[0].address == "first@example.com"
assert second._options.to[0].address == "second@example.com"
print("branches are isolated")
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; se inspecciona estado protegido solo para demostrar aislamiento.

### Publicar un preparado con file

```python
import asyncio
from tempfile import TemporaryDirectory
from pathlib import Path
from orionis.mail.entities.prepared import PreparedMail
from orionis.mail.transports.file import FileTransport


async def main() -> None:
    prepared = PreparedMail(
        message_id="<example@example.com>",
        sender="a@example.com",
        recipients=("b@example.com",),
        mime=b"Subject: Example\r\n\r\nHello\r\n",
        smtp_utf8=False,
    )
    with TemporaryDirectory() as root:
        result = await FileTransport(Path(root)).send(prepared, mailer="file", driver="file")
        assert result.file_path is not None
        assert result.file_path.read_bytes() == prepared.mime
        print(result.status)


asyncio.run(main())
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; `.eml` solo temporal.

### Validar SMTP sin conectar

```python
from orionis.mail.entities.smtp_settings import SmtpSettings
from orionis.mail.enums.encryption import MailEncryption

settings = SmtpSettings.fromConfig({
    "url": "smtps://user:secret@mail.example.com",
    "host": "ignored.example.com",
    "port": 587,
    "encryption": "TLS",
    "username": "",
    "password": "",
    "timeout": 10,
})
assert settings.host == "mail.example.com"
assert settings.port == 465
assert settings.encryption is MailEncryption.SSL
assert "secret" not in repr(settings)
print(settings.host)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6; no abrió red.

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Configurar callback directo

```python
from orionis.mail import Message


def configure_invoice(message: Message) -> None:
    message.fromAddress("billing@example.com", "Billing")
    message.to("ana@example.com", "Ana")
    message.subject("Your invoice")


probe = Message()
assert configure_invoice(probe) is None
assert probe._snapshot().envelope().subject == "Your invoice"
print(probe._snapshot().to[0].address)
```

Validación: **Ejecutado correctamente** en CPython 3.14.6.

### Implementar factory asíncrona

```python
from collections.abc import Mapping
from pathlib import Path
from orionis.foundation.contracts.application import IApplication
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.transports.file import FileTransport


async def archive_factory(
    app: IApplication,
    config: Mapping[str, object],
) -> IMailTransport:
    path = Path(str(config.get("path", "storage/mail/archive")))
    if not path.is_absolute():
        path = app.basePath / path
    return FileTransport(path)
```

Validación: **Ejecutado por la prueba documental de mail** con `Application` real y ruta temporal.

### Registrar el driver

```python
from orionis.mail.manager import MailManager


def register_archive(manager: MailManager) -> None:
    manager.extend("custom_archive", archive_factory)
```

Validación: **Importación y sintaxis verificadas**; el manager se resuelve en startup.

### Enviar mediante facade

```python
import asyncio
from orionis.mail import Message
from orionis.support.facades import Mail


def configure(message: Message) -> None:
    message.to("ana@example.com").subject("Status")


async def send_status():
    return await Mail.mailer("file").raw("All systems operational", configure)


# asyncio.run(send_status())  # Run only after the Orionis application boots.
```

Validación: **Importación y sintaxis verificadas**; requiere aplicación iniciada.

### Enviar mailable con inyección

```python
from orionis.support.facades import Mail


async def send_welcome() -> None:
    result = await Mail.to("ana@example.com").send(WelcomeMail("Ana"))
    assert result.status in {"accepted", "partial", "stored"}
```

Validación: **Importación y sintaxis verificadas**; requiere vistas, remitente y transporte.

## Configuración

`config/mail.py` define:

| Ajuste | Entorno | Predeterminado |
|---|---|---|
| Mailer predeterminado | `MAIL_MAILER` | `smtp` |
| Remitente | `MAIL_FROM_ADDRESS` | vacío |
| Nombre remitente | `MAIL_FROM_NAME` | `APP_NAME`, luego `Orionis` |
| URL SMTP | `MAIL_URL` | vacío |
| Endpoint | `MAIL_HOST`, `MAIL_PORT` | host vacío, 587 |
| Seguridad | `MAIL_ENCRYPTION` | `TLS` |
| Credenciales | `MAIL_USERNAME`, `MAIL_PASSWORD` | par vacío |
| Timeout | `MAIL_TIMEOUT` | `None` |
| Salida file | `MAIL_FILE_PATH` | `storage/mail` |

Una URL `smtp://` o `smtps://` prevalece sobre endpoint/seguridad y reemplaza credenciales como par. Mailers llamados `smtp` y `file` infieren driver; otros requieren `driver` explícito.

## Integración con Orionis

`MailProvider` enlaza `MailComposer` e `IMailManager` como singletons y fija `Mail` sin conectar. El composer inyecta `IViewEngine` e `IStorageManager`; clases Mailable se construyen por contenedor. Autenticación usa mail para verificación y reset.

Use `IMailManager` inyectado para dependencias explícitas y `Mail` en entry points concisos. Ambos apuntan al mismo singleton; cada operación fluida queda aislada.

## Errores y casos límite

- Controles en headers, direcciones ambiguas, dominios inválidos, vistas vacías, conflictos de cuerpo, adjuntos inseguros y solape Bcc generan errores de composición.
- Enviar sin remitente o destinatarios falla al componer. Asunto/cuerpo literal vacío sí es válido.
- Fallos de adjunto son `MailAttachmentException`; archivos ausentes no se detectan al declarar.
- Mailers/drivers desconocidos, extensiones duplicadas, SMTP mal configurado y factories inválidas generan `MailConfigurationException`.
- Fallos SMTP se vuelven `MailTransportException` con diagnóstico acotado, una línea y credenciales redactadas.
- STARTTLS obligatorio falla si no se anuncia. Local parts internacionales requieren SMTPUTF8.
- File nunca sobrescribe y falla si no hay hard links atómicos.
- Bcc está en el envelope de transporte, nunca en MIME.
- Un resultado parcial exige política de retry/idempotencia; reenviar ciegamente puede duplicar aceptados.

## Rendimiento y concurrencia

Render y lecturas se ejecutan concurrentemente cuando es seguro; storage/file y SMTP síncronos salen del event loop mediante el executor. MIME se construye completo en memoria, así que adjuntos grandes elevan memoria pico. Imponga límites antes de declarar.

Opciones fluidas y Mailable son inmutables y reutilizables. Factories corren por envío y deben ser stateless o sincronizadas. Registre drivers en startup. File usa nombres únicos/links atómicos; SMTP crea conexión por operación. Use colas y concurrencia acotada para volumen.

## Compatibilidad

Orionis declara Python 3.14+. MIME usa políticas `email`, dominios IDNA, nombres Unicode y SMTPUTF8 solo si el addr-spec lo exige. SMTP soporta STARTTLS obligatorio, SSL implícito y plaintext explícito. File requiere filesystem local con hard links atómicos, como NTFS o POSIX regular.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, entidades, sobrecargas, composición, vistas, storage, transportes, factories, configuración, provider/facade e integraciones. Los **193** métodos de prueba pasaron, incluido el contrato documental. Nueve ejemplos directos se ejecutaron, la factory personalizada corrió con aplicación real y tres ejemplos dependientes del contenedor se validaron por compilación/importación.
