# Configurar SMTP, file y transportes propios

Mail separa la declaración del mensaje, la composición MIME y el transporte. Prepara remitente, contenido y política de entrega antes del primer envío.

## Seleccionar un mailer

Un nombre de mailer identifica una entrada de `mail.mailers`; `driver` identifica su implementación. `Mail.mailer("archive")` selecciona la entrada, no registra un transporte. Las entradas convencionales `smtp` y `file` pueden inferir su driver; cualquier otro nombre necesita `driver` explícito. El manager lee la selección durante cada envío y normaliza una copia de configuración para la factory.

`config/mail.py` incluye entidades para SMTP y file. La entidad superior `Mail` también admite un mapping de mailers arbitrarios; `Mailers` es el conjunto convencional de campos. Para un transporte nuevo puedes declarar un mapping como el siguiente y registrar su factory antes de enviar. Este bloque solo valida configuración, no cambia la configuración activa de la aplicación:

```python
from orionis.foundation.config.mail import Mail

config = Mail(
    default="archive",
    from_address={"address": "notifications@example.com", "name": "Reports"},
    mailers={
        "archive": {"driver": "custom_archive", "path": "storage/mail/archive"},
        "file": {"driver": "file", "path": "storage/mail"},
    },
)
assert config.default == "archive"
```

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

Un URL `smtps://` fija SSL; un URL `smtp://` conserva encryption configurado. El URL sustituye host, puerto explícito y credenciales presentes como par. Mailers llamados `smtp` y `file` infieren driver; otros requieren `driver` explícito.



## Operar SMTP

`TLS` significa STARTTLS obligatorio; `SSL` utiliza TLS implícito; `none` o cadena vacía desactiva TLS. No hay fallback silencioso de STARTTLS a plaintext. La conexión TLS verifica hostname y certificado con contexto del sistema y mínimo TLS 1.2. El backend no expone opciones para saltarse esa verificación.

Un `smtps://` URL fija SSL y puerto 465 salvo puerto explícito. Un URL `smtp://` sustituye host y puerto si lo incluye, pero conserva encryption y puerto configurados si no los sobrescribe: no fuerza plaintext. Credenciales presentes en el URL sustituyen username/password como par. Los caracteres reservados deben codificarse en el URL. Se rechazan path, query y fragment; el host debe ser válido y el puerto entero entre 1 y 65535.

Username y password deben estar ambos presentes o ambos vacíos. `timeout` acepta entero positivo o `None`; configura un tiempo acotado para operación real porque `None` deja la decisión de timeout al socket. Los buzones internacionales con local part Unicode requieren SMTPUTF8 y 8BITMIME; no basta un dominio que pueda normalizarse a IDNA. Los errores no publican credenciales; aun así evita registrar objetos de configuración o URLs completos.

## Usar file para desarrollo o archivo

El transporte escribe MIME a un temporal privado, hace flush/fsync y publica con hard link de nombre aleatorio sin reemplazar un archivo existente. Solo después devuelve `STORED` y `file_path`. El filesystem necesita hard links; un montaje sin soporte falla explícitamente. La ruta relativa se ancla al base path, la absoluta se conserva y una ruta anclada pero relativa de Windows se rechaza.

Los `.eml` contienen cuerpo, adjuntos y direcciones visibles; protégelos como datos de aplicación. La publicación no envía correo ni programa un worker. Define rotación, retención y eliminación fuera del módulo: no hay limpieza automática de archivos de correo. La cancelación del consumidor no garantiza que se detenga la publicación ya iniciada en el executor.


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

## Implementar y registrar un transporte

Cumple `IMailTransport.send(prepared, *, mailer, driver) -> MailResult` como método async. Recibe `PreparedMail` con MIME completo, remitente y receptores separados: usa ese envelope de transporte para conservar Bcc y evita reanalizar los encabezados visibles para decidir a quién enviar. El pipeline valida composición antes de crear el transporte.

La factory recibe `(app, normalized_config)` y puede ser sync o async. Debe devolver una instancia de `IMailTransport`; el manager no acepta simplemente un objeto con un método de nombre parecido. `extend(name, factory)` rechaza nombres vacíos, duplicados y los drivers integrados `smtp`/`file`. El registro es compartido; complétalo durante boot. El resultado debe describir una evidencia real y no declarar aceptación SMTP antes de confirmarla.

La siguiente factory reutiliza el transporte file para un destino alternativo. El segundo bloque presupone que `archive_factory` está definido por el primero:


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

### Registrar el driver

```python
from orionis.mail.manager import MailManager


def register_archive(manager: MailManager) -> None:
    manager.extend("custom_archive", archive_factory)
```

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

## Referencia de implementación para extensiones

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

---

[Índice](README.md) · [foundation](../../../foundation/docs/es/README.md) · [container](../../../container/docs/es/README.md) · [storage](../../../storage/docs/es/README.md)
