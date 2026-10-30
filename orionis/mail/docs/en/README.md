# Mail

Mail separates message declarations, MIME composition, and transport. Prepare sender, content, and delivery policy before the first send.

## Learning path

1. [Declaring messages](composing-mail.md): mailables, bodies, recipients, and attachments.
2. [Sending and handling results](sending-and-results.md): facade, callbacks, concurrency, and failures.
3. [Transports and extensions](transports-and-extensions.md): SMTP, security, file publication, and custom factories.

## Bounded execution and performance

At the prepared-message transport boundary, `await smtp.sendMany(messages, mailer="notifications", driver="smtp")` accepts up to 100 `PreparedMail` objects. It opens, negotiates TLS and authenticates once, then sends each envelope in order and closes the connection. A dedicated executor admits four batches and 16 pending batches. The ordinary single-message API remains compatible; no connection is pooled across batches or credentials.

`MailBatchException.completed` retains confirmed results and `failed_index` identifies the first uncertain transaction; later messages are not attempted after failure. There are no automatic retries. Cancellation of a running batch waits for its native execution and resource cleanup; it is not proof of non-delivery and may allow the accepted batch to finish. Configure a finite socket timeout. The batch API requires already composed messages and does not retain an unbounded message generator.
