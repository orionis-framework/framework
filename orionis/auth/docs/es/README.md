# Autenticación y autorización

Orionis resuelve la identidad actual mediante sesión de navegador o token personal y aplica permisos, roles y políticas. El contexto pertenece a la petición; los servicios compartidos no guardan un usuario global.

1. [Identidad y login de sesión](identity-and-session.md): modelo, guards, login y logout.
2. [Permisos, roles y políticas](authorization.md): proteger capacidades y recursos.
3. [Tokens personales](personal-access-tokens.md): emitir, limitar y revocar credenciales.
4. [Recordarme y recuperación de cuentas](account-recovery.md): cookies persistentes, reset y páginas predeterminadas.

Requiere Python 3.14+, modelo ORM configurado, hashing y migraciones de autenticación para persistencia. Los ejemplos de facade y repositorios necesitan una aplicación inicializada; los ejemplos de snapshots son independientes. Revisa [sesiones](../../../session/docs/es/README.md), [HTTP](../../../http/docs/es/README.md) y [ORM](../../../orm/docs/es/README.md).

## Ejecución acotada y rendimiento

El proveedor de modelos y el repositorio de tokens nativos combinan los SELECT de token e identidad cuando comparten conexión nativa, la clave es entera/textual y los scopes conservan una consulta simple. Mantienen filtros de scopes, hidratación, eventos retrieved y relaciones anticipadas. Los metadatos del token se validan antes de los eventos; el guard conserva la actualización condicional final de `last_used_at`, comprobando revocación y vencimiento después de resolver la identidad. La ruta admitida usa dos sentencias en lugar de tres y nunca cachea una decisión de autenticación.

Los proveedores/repositorios/conexiones personalizados, claves UUID, bases separadas y scopes complejos mantienen la ruta original. La conversión SQL de claves enteras almacenadas está protegida frente a valores inválidos o fuera de rango. Compilar SQL no sustituye las pruebas de integración con cada motor desplegado.
