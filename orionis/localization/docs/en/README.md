# Localization

Organize resources by locale, choose a fallback, and pass a locale explicitly when it depends on a request. Lookup, fallback, and plural selection are synchronous operations with a process-local cache.

## Learning path

1. [Publishing and translating localized content](translating-content.md): prerequisites, progressive usage, configuration, integration, failures, and public reference.

The file examples use the application's `resources/lang/en.json` and `resources/lang/es.json`; the memory examples run independently. Facades require a booted Orionis application and its providers.

Related: [view](../../../view/docs/en/README.md) · [foundation](../../../foundation/docs/en/README.md)

## Cache limits

`TranslationRepository(loader, max_locales=256, negative_ttl=30)` bounds both successful and missing locale maps. LRU eviction releases the oldest unused map; empty maps are retried after 30 seconds by default. Hits refresh recency. `forget`, `flush` and existing reload APIs still invalidate explicitly. Positive maps do not watch files; preload required locales during bootstrap because loading remains synchronous.
