# Recuperación de contraseña

`Route.auth()` registra `GET/POST /forgot-password` y `GET/POST /reset-password`
en el grupo web, con sesión, CSRF y acceso para invitados. Los nombres de las
rutas POST son `forgot-password` y `password.update`; el formulario de cambio
usa `password.reset`.

## Activación

1. Ejecuta `python reactor migrate` para crear `password_reset_tokens`.
2. El enlace del correo se forma con `request.baseUrl`, incluida la IP y el
   puerto que use el entorno. Si hay un proxy, confíalo en `TRUSTED_PROXIES`
   para que se detecte correctamente el esquema HTTPS.
3. Configura el transporte de correo en `config/mail.py`.

`config/auth.py` → `passwords` permite cambiar `expiration` (60 minutos),
`throttle` (60 segundos) y `table`. La tabla debe existir en la misma
conexión que el modelo configurado en `auth.identity.model`. El modelo debe
tener un correo único en `email` e implementar `Authenticatable`.

## Comportamiento

- La respuesta es idéntica para correos conocidos, desconocidos o limitados.
  La búsqueda y el envío se ejecutan después de enviar la respuesta HTTP.
- El token contiene 32 bytes aleatorios; solo se almacena su digest SHA-256.
  Un enlace nuevo reemplaza al anterior. Abrirlo no consume el token.
- La contraseña cumple la política del formulario de cambio de contraseña.
  Contraseña y confirmación nunca se rellenan ni se guardan en flash.
- La expiración se vuelve a comprobar al consumir el token. Su consumo, la
  actualización condicional de contraseña y la revocación de tokens personales
  se confirman en una transacción. Las solicitudes simultáneas tienen un único
  ganador. Un fallo revierte todos los cambios.
- El enlace deja de funcionar si cambia la contraseña, se elimina la cuenta
  o se cambia su correo. La recuperación no activa cuentas ni verifica correos.
- El guard de sesión compara una huella de la contraseña en cada petición.
  Tras el cambio se exige iniciar sesión nuevamente en todos los dispositivos.
  Las sesiones existentes anteriores a esta actualización también requieren
  un nuevo inicio de sesión, al no disponer de esa huella.
- Se envía una notificación de confirmación después del cambio. Nunca se envían
  contraseñas por correo y no se inicia sesión automáticamente.
- Las respuestas usan `Cache-Control: no-store` y `Referrer-Policy: no-referrer`.

Los correos utilizan `BackgroundTask`, el mecanismo existente que se ejecuta
tras responder; no es una cola durable. Si el proceso termina antes del envío,
se puede solicitar otro enlace después de la espera. Los fallos se registran
sin excepciones, cuerpos de correo, tokens ni credenciales.

El proxy/servidor debe omitir los query strings de `/reset-password` en los
logs de acceso y puede añadir límites por IP al límite por cuenta del broker.
No es necesario borrar los registros para hacer efectiva la expiración; se
reutiliza una fila por correo. Para mantenimiento se pueden eliminar registros
con `created_at` anterior a ambos límites (expiración y espera entre envíos).

Pruebas: `python -X utf8 reactor test --start-dir tests/auth --file-pattern test_password_reset.py`.

Referencia: [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
