# Sending messages and handling results

Mail separates message declarations, MIME composition, and transport. Prepare sender, content, and delivery policy before the first send.

## Send from an initialized application

`MailProvider` registers singleton `MailComposer` and `IMailManager` services and pins the `Mail` facade. The composer needs `IViewEngine` and `IStorageManager` even when one send uses literal text without attachments. Importing the package does not initialize all these services. Services can inject `IMailManager`; its chains behave like the facade.

Fluent calls are synchronous and return a new chain: retain `Mail.to(...)`'s return value or chain it. The previous chain retains its recipients. Terminal `send`, `raw`, and `html` calls are async; views are not rendered, files are not read, and transports are not opened until they are awaited. This example needs a configured global sender and `file` mailer:

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

### Configure callbacks correctly

A direct-send callback receives a mutable `Message` exclusive to that operation. It may be sync or async, runs once, and must return `None` or the same `Message`; `False` does not cancel sending and is a composition error. Do not retain or share it across sends. A callback changes sender, recipients, subject, and attachments; bodies are declared separately.

`send(mailable)` accepts neither extra `data` nor a callback: the mailable owns its context. `send(Content(...))` accepts no second `data` argument because the object already carries it. `send("template", data, callback)` does accept a context mapping. Passing a `Mailable` class lets the manager construct it through the container; for simple business values in a constructor, normally create an instance yourself with those values.


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

## Interpret results and failures

| Status | Confirmed evidence | Does not guarantee |
|---|---|---|
| `MailStatus.ACCEPTED` | SMTP accepted every intended recipient. | Mailbox delivery or reading. |
| `MailStatus.PARTIAL` | SMTP accepted some recipients and rejected others. | Safe full-message retries. |
| `MailStatus.STORED` | A complete `.eml` was published on the filesystem. | Delivery to an SMTP server. |

Results contain `message_id`, `mailer`, `driver`, `recipients`, `accepted_recipients`, `rejected_recipients`, and `file_path` where applicable. A file send does not fabricate SMTP acceptance. Record identifiers and business status without exposing Bcc or sensitive diagnostics.

`MailCompositionException` and its subclasses represent invalid declarations, callbacks, views, or attachments before transport. `MailConfigurationException` represents invalid selection, configuration, or factories. `MailTransportException` represents send/publication failure. Application code decides whether to correct input, alert, or retry; the module does not retry automatically.

After disconnection or cancellation, the server may have accepted a message without the client confirming its outcome. Cancelling an `await` does not immediately stop a synchronous SMTP/file worker. Indiscriminate retries can duplicate mail. For `PARTIAL`, retain accepted and rejected recipients and apply a policy that does not blindly resend to everyone. Transport idempotency keys and deduplication are not supplied.

The following example identifies error boundaries and re-raises without retrying. Replace those blocks with your service policy:

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

### Inspect a transport result

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

## Concurrent sends and background work

Chains are independent; the factory registry is shared and must be completed during boot. Each send creates a transport; SMTP opens one connection per operation. Current preparation renders text first, HTML second, then reads each attachment sequentially before composing MIME off the loop. It does not promise parallel attachment preparation or persistent SMTP connections.

To send after a response, attach a `BackgroundTask` to that response. Work still belongs to the process and does not survive termination. For persistence use queues with a durable connection and an explicit retry strategy. This API has no `Mail.queue()` method. Do not store `Message` objects or SMTP connections in job payloads; retain identifiers or serializable data needed to reconstruct declarations.


### Fluent manager/facade

The `IMailManager` service and `Mail` facade provide `mailer`, `fromAddress`, `to`, `cc`, `bcc`, `replyTo`, `subject`, `attach`, `send`, `raw`, `html`, and `extend`. A selected mailer is a configuration entry name; its `driver` chooses an implementation.

### Terminal overloads

- `await Mail.send(mailable_or_class)`
- `await Mail.send("emails.welcome", data, callback)`
- `await Mail.send(Content(...), callback=callback)`
- `await Mail.raw(text, callback=None)`
- `await Mail.html(html, callback=None)`

---

[Index](README.md) · [foundation](../../../foundation/docs/en/README.md) · [background](../../../background/docs/en/README.md) · [queues](../../../queues/docs/en/README.md)
