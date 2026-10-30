# Correo

Mail separa la declaración del mensaje, la composición MIME y el transporte. Prepara remitente, contenido y política de entrega antes del primer envío.

## Recorrido

1. [Declarar mensajes](composing-mail.md): mailable, cuerpos, destinatarios y adjuntos.
2. [Enviar y manejar resultados](sending-and-results.md): facade, callbacks, concurrencia y errores.
3. [Transportes y extensiones](transports-and-extensions.md): SMTP, seguridad, archivo y factories propias.

## Ejecución acotada y rendimiento

En la capa de transporte de mensajes preparados, `await smtp.sendMany(messages, mailer="notifications", driver="smtp")` admite hasta 100 objetos `PreparedMail`. Abre la conexión, negocia TLS y autentica una vez; luego envía cada sobre en orden y cierra. Un ejecutor dedicado admite cuatro lotes activos y 16 pendientes. La API habitual de mensaje único conserva su comportamiento; no se comparte la conexión entre lotes ni credenciales.

`MailBatchException.completed` conserva resultados confirmados y `failed_index` identifica la primera transacción incierta; después del fallo no se intentan los mensajes restantes. No hay reintentos automáticos. Cancelar un lote activo espera su ejecución nativa y cierre; no demuestra que no hubo entrega y puede permitir que el lote aceptado termine. Configura un timeout de socket finito. La API recibe mensajes ya compuestos y no materializa un generador ilimitado.
