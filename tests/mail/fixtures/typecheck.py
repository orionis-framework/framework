from typing import TYPE_CHECKING, assert_type
from orionis.mail import Address, Content, MailResult, Message, PendingMail
from orionis.support.facades.mail import Mail

if TYPE_CHECKING:
    from orionis.mail import Mailable
    from orionis.mail.contracts.manager import IMailManager


def configure(message: Message) -> Message:
    """Provide a typed fluent callback accepted by all direct-send entry points."""
    return message.fromAddress("a@example.com").to("b@example.com").subject("Typed")


async def check_public_types(mail: IMailManager, mailable: Mailable) -> None:
    """Check positive consumer signatures without sending anything at import time."""
    pending = assert_type(Mail.to(Address("b@example.com")), PendingMail)
    assert_type(pending.fromAddress("a@example.com"), PendingMail)
    assert_type(mail.subject("Typed"), PendingMail)
    assert_type(await Mail.send(mailable), MailResult)
    assert_type(
        await Mail.send("emails.welcome", {"name": "Ana"}, configure), MailResult,
    )
    assert_type(await Mail.send(Content(text=""), callback=configure), MailResult)
    assert_type(await Mail.raw("text", configure), MailResult)
    assert_type(await Mail.html("<p>html</p>", configure), MailResult)
    assert_type(await mail.send(mailable), MailResult)
    assert_type(
        await mail.send("emails.welcome", {"name": "Ana"}, configure), MailResult,
    )
    assert_type(await mail.send(Content(text=""), callback=configure), MailResult)
    assert_type(await pending.send(mailable), MailResult)
    assert_type(await pending.raw("text", configure), MailResult)
    assert_type(await pending.html("<p>html</p>", configure), MailResult)
