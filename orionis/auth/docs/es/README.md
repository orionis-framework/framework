# Autenticación y autorización

Orionis resuelve la identidad actual mediante sesión de navegador o token personal y aplica permisos, roles y políticas. El contexto pertenece a la petición; los servicios compartidos no guardan un usuario global.

1. [Identidad y login de sesión](identity-and-session.md): modelo, guards, login y logout.
2. [Permisos, roles y políticas](authorization.md): proteger capacidades y recursos.
3. [Tokens personales](personal-access-tokens.md): emitir, limitar y revocar credenciales.
4. [Recordarme y recuperación de cuentas](account-recovery.md): cookies persistentes, reset y páginas predeterminadas.

Requiere Python 3.14+, modelo ORM configurado, hashing y migraciones de autenticación para persistencia. Los ejemplos de facade y repositorios necesitan una aplicación inicializada; los ejemplos de snapshots son independientes. Revisa [sesiones](../../../session/docs/es/README.md), [HTTP](../../../http/docs/es/README.md) y [ORM](../../../orm/docs/es/README.md).
