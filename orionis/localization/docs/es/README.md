# Localización

Organiza los recursos por idioma, decide un fallback y pasa el idioma explícitamente cuando depende de una solicitud. Las traducciones, el fallback y los plurales son operaciones síncronas con una caché por proceso.

## Recorrido

1. [Publicar y traducir contenido por idioma](translating-content.md): requisitos, uso progresivo, configuración, integración, errores y referencia pública.

Los ejemplos aislados usan objetos de aplicación mínimos; las facades requieren una aplicación Orionis inicializada y sus providers. El código fuente y los contratos determinan las capacidades descritas.

Relacionados: [view](../../../view/docs/es/README.md) · [foundation](../../../foundation/docs/es/README.md)

## Ejecución acotada y rendimiento

`TranslationRepository(loader, max_locales=256, negative_ttl=30)` limita tanto los mapas encontrados como los locales ausentes. El LRU expulsa el mapa usado hace más tiempo; los mapas vacíos se vuelven a cargar después de 30 segundos por defecto. Los aciertos actualizan la recencia. `forget`, `flush` y la recarga existente siguen invalidando explícitamente. Los mapas positivos no vigilan archivos; precarga los locales necesarios durante el arranque porque la carga sigue siendo síncrona.
