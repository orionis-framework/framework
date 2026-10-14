# Fundamentos de Orionis

## Descripción general

`Application` extiende el `Container` de inyección y es el objeto exportado desde `orionis`. Coordina bootstrap, sirve como entrada ASGI/RSGI, despacha CLI, guarda configuración y rutas, carga providers y posee el ciclo de vida.

Foundation también define entidades congeladas para cada subsistema, metadata core inmutable, el servicio de rutas `Directory`, enums y presentación de startup/shutdown. Las aplicaciones lo configuran en `bootstrap/app.py`, llaman `create()` y dejan que servidor HTTP o Reactor dirijan el runtime.

## Requisitos

- Python 3.14 o posterior; la construcción rechaza intérpretes anteriores.
- Raíz de aplicación como `str` o `pathlib.Path`.
- Módulos de configuración dataclass congelados válidos bajo `config`.
- Archivos de rutas existentes y con la fachada requerida al registrarlos.
- Un event loop por worker; el estado mutable no está diseñado para compartirse entre loops o hilos.

## Recorrido del módulo

- [Ciclo de vida y recursos de aplicación](application-lifecycle.md)
- [Configuración tipada y valores en ejecución](configuration.md)
- [Despliegue, diagnóstico y referencia de Application](deployment-and-reference.md)
- [Crear y arrancar una aplicación](getting-started.md)
- [Directorios y caché de arranque](paths-and-caching.md)

Continúa por: [environment](../../../environment/docs/es/README.md) · [container](../../../container/docs/es/README.md) · [http](../../../http/docs/es/README.md) · [console](../../../console/docs/es/README.md).

Los ejemplos que requieren bootstrap, una solicitud o servicios externos indican su contexto. Los resultados de comprobación de esta reconstrucción se distinguen de las notas históricas; no se presupone que se haya ejecutado una integración de producción.

- [Instalación y primer proyecto](installation.md)

- [Auditoría y cobertura de la documentación](documentation-audit.md)
