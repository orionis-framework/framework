# Localización

Organiza los recursos por idioma, decide un fallback y pasa el idioma explícitamente cuando depende de una solicitud. Las traducciones, el fallback y los plurales son operaciones síncronas con una caché por proceso.

## Recorrido

1. [Publicar y traducir contenido por idioma](translating-content.md): requisitos, uso progresivo, configuración, integración, errores y referencia pública.

Los ejemplos de archivos usan `resources/lang/en.json` y `resources/lang/es.json` de la aplicación; los ejemplos en memoria funcionan de forma independiente. Las fachadas requieren una aplicación Orionis iniciada y sus providers.

Relacionados: [view](../../../view/docs/es/README.md) · [foundation](../../../foundation/docs/es/README.md)

## Límites de caché

`TranslationRepository(loader, max_locales=256, negative_ttl=30)` limita tanto los mapas encontrados como los locales ausentes. El LRU expulsa el mapa usado hace más tiempo; los mapas vacíos se vuelven a cargar después de 30 segundos por defecto. Los aciertos actualizan la recencia. `forget`, `flush` y la recarga existente siguen invalidando explícitamente. Los mapas positivos no vigilan archivos; precarga los locales necesarios durante el arranque porque la carga sigue siendo síncrona.
