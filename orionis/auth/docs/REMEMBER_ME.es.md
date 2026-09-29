# Recordarme

Se conserva `users.remember_token`: ahora respalda el acceso persistente. Antes,
la casilla solo guardaba el correo en `usrname` y ningún componente validaba la
columna. El formulario ofrece «Mantener mi sesión en este dispositivo» y deja
el autocompletado al navegador. Un inicio de sesión correcto elimina la antigua
cookie `usrname`.

## Uso y configuración

```python
await Auth.attempt({"email": email, "password": password}, remember=True)
await Auth.logout()
```

La casilla del controlador integrado activa esa opción. Sin marcarla, se inicia
la sesión normal y se revoca el acceso persistente previo de la cuenta.
`auth.remember` en `config/auth.py` configura:

- `cookie`: `orionis_remember`, distinto al nombre de la cookie de sesión.
- `lifetime`: 43200 minutos (30 días), mediante `AUTH_REMEMBER_LIFETIME`.
- `secure`: `True`, mediante `AUTH_REMEMBER_SECURE`. Para desarrollo local con
  HTTP se puede configurar `False`; en producción se requiere HTTPS. Si el
  servidor recibe HTTP mientras esta opción es verdadera, rechaza la emisión
  de credenciales persistentes. Configura correctamente el esquema HTTPS en
  el despliegue con proxy.

La cookie siempre es `HttpOnly`, `SameSite=Lax`, con `Path=/`, sin `Domain` y con
caducidad. Las opciones de la sesión normal continúan en `config/session.py`.
No se utiliza la cookie persistente en las rutas API.

## Validación y revocación

La cookie incluye identificador, vencimiento y un secreto aleatorio de 256 bits.
`remember_token` guarda `v1:<vencimiento>:<digest SHA-256>`, que cabe en los 100
caracteres existentes. El digest vincula el secreto con el identificador,
vencimiento y hash de la contraseña; la base de datos no guarda el secreto.

Cuando falta una sesión válida, el guard consulta la cuenta, exige que siga
activa, verifica la caducidad y compara el digest en tiempo constante. Una
actualización condicional comprueba también la contraseña y el estado actuales,
y rota el token antes de crear una sesión y un CSRF nuevos. Dos peticiones que
presentan la misma cookie tienen un único ganador; las demás no borran la cookie
de reemplazo y permanecen anónimas hasta la siguiente petición del navegador.
La navegación nunca prolonga la fecha original de caducidad.

Cerrar sesión revoca el token en la base de datos y borra la cookie. El cambio de
contraseña desde el perfil y la recuperación dejan la columna en `NULL`; incluso
un cambio realizado por otro flujo invalida la cookie porque el digest está
vinculado a la contraseña anterior. Las cuentas eliminadas o desactivadas no
pueden restaurar el acceso.

Una columna admite **un único acceso persistente vigente por cuenta**. Recordar
otro dispositivo reemplaza al anterior y cerrar sesión revoca ese acceso. Las
sesiones normales de otros dispositivos conservan su duración habitual, salvo
cuando cambia la contraseña. Soportar gestión independiente de varios
dispositivos requeriría una tabla de credenciales por dispositivo.

## Compatibilidad

No se requiere otra migración: la columna existente es suficiente. Los valores
antiguos sin el formato y digest válidos se rechazan. Los modelos personalizados
deben incluir `remember_token`, `active` y el concern `Authenticatable` para usar
el proveedor ORM. Proveedores propios pueden implementar
`IIdentityProvider.updateRememberToken()` con comparación y reemplazo atómicos;
la implementación predeterminada no emite credenciales persistentes.

`SessionGuard.logout()` ahora es asíncrono por la revocación en base de datos:
los consumidores directos deben usar `await`. `Auth.logout()` ya era asíncrono.
Los guards de sesión personalizados deben admitir el argumento `remember` de
`attempt()` y el cierre de sesión asíncrono.

Pruebas: `python -X utf8 reactor test --start-dir tests/auth --file-pattern test_remember.py`.

Referencia: [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).
