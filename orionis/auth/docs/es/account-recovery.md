# Recordarme, recuperación y verificación de cuentas

La autenticación persistente y la recuperación usan credenciales distintas de tokens personales de API. Requieren identidad ORM, migraciones auth, hashing y entrega de correo. Los controladores predeterminados son una integración inicial que debes adaptar al modelo y vistas de aplicación.

## Recordar un navegador

`await Auth.attempt(credentials, remember=True)` emite una credencial persistente tras verificar contraseña. La identidad necesita columna `remember_token`. El servicio rota la credencial al restaurar sin extender su plazo original y falla de forma cerrada ante cookie inválida/expirada, usuario inactivo, contraseña cambiada o fallo de rotación.

`AUTH_REMEMBER_COOKIE` es `orionis_remember`, `AUTH_REMEMBER_LIFETIME` 43200 minutos y `AUTH_REMEMBER_SECURE` verdadero. En modo secure HTTP no restaura la credencial. El nombre debe ser diferente de la cookie de sesión. Prueba con el esquema apropiado en vez de desactivar HTTPS para un flujo productivo.

## Recuperar una contraseña

```python
from orionis.auth.passwords.broker import PasswordBroker

async def reset_password(broker: PasswordBroker, email: str, token: str, password: str) -> bool:
    identity = await broker.reset(email, token, password)
    return identity is not None
```

`issue(email)` devuelve `(identity, plain_token)` o `None`; el llamador debe entregar el secreto por un canal privado. `valid(email, token)` comprueba sin consumir y no reserva el token: otra petición podría consumirlo antes. `reset` realiza comprobación y consumo junto con cambio de contraseña en una transacción; no llames solo `valid` para después escribir el hash por separado.

El broker normaliza email, almacena hash del secreto y comprueba condicionalmente la contraseña previa para resolver carreras. Rechaza tokens consumidos, vencidos o vinculados a una contraseña anterior. El flujo limpia `remember_token` y revoca tokens personales; revisa estas garantías antes de agregar otros mecanismos propios. La contraseña nueva debe validar los requisitos de aplicación antes de llamar al servicio.

`AUTH_PASSWORD_RESET_EXPIRATION` vale 60 minutos, `AUTH_PASSWORD_RESET_THROTTLE` 60 segundos y `AUTH_PASSWORD_RESET_TABLE` `password_reset_tokens`. Devuelve un mensaje público uniforme al solicitar un enlace para no revelar existencia de cuentas.

## Páginas y email de verificación

`Route.auth()` registra login, sign-up, forgot-password, reset-password, verify-email y POST logout. Los controladores utilizan vistas y schemas del flujo de aplicación; el de registro depende explícitamente de `app.models.user.User`. Reemplaza controladores con argumentos de `Route.auth` cuando tu dominio difiera. Los enlaces reset se envían en trabajo de fondo tras devolver respuesta; no es una cola durable y una caída puede impedir entrega.

El marcador `MustVerifyEmail` hace que el registro predeterminado cree la identidad inactiva y envíe verificación. No es un servicio completo de verificaciones: el enlace cifra el identificador y no implementa un plazo dedicado de expiración. Si necesitas links de un solo uso o con vencimiento, implementa esa política explícita. La verificación no debe convertirse en login implícito.

Mantén CSRF en formularios, respuestas privadas/no-store y límites contra abuso. Revisa el manejo de excepción del registro predeterminado para producción: puede presentar el mensaje de error al formulario. No permitas divulgar secretos mediante errores de proveedor.

Evidencia: [remember](../../remember.py), [broker](../../passwords/broker.py), [rutas](../../../http/routes/auth.py), [registro](../../../http/default/controllers/register_controller.py), [recuperación](../../../http/default/controllers/forgot_password_controller.py). Pruebas: [remember](../../../../tests/auth/test_remember.py), [reset](../../../../tests/auth/test_password_reset.py), [rutas](../../../../tests/auth/test_auth_routes.py). Relacionado: [páginas HTTP](../../../http/docs/es/default-responses.md).
