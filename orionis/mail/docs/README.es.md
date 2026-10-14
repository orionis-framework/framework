# Mail: ejemplos de compatibilidad

La documentación oficial está en [el índice español](es/README.md). Esta ruta conserva el catálogo de ejemplos exigido por `tests/mail/test_docs.py` y enlaces existentes. Los ejemplos que inspeccionan atributos privados son pruebas aisladas de compatibilidad; utiliza las APIs públicas enseñadas en los capítulos oficiales. No implica que las facades puedan ejecutarse antes del boot.

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


### Enviar mailable con inyección

```python
from orionis.support.facades import Mail


async def send_welcome() -> None:
    result = await Mail.to("ana@example.com").send(WelcomeMail("Ana"))
    assert result.status in {"accepted", "partial", "stored"}
```
