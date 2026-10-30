# Views

View renders server-side HTML with async Jinja2 and returns an Orionis response.

## Learning path

1. [Rendering pages](rendering-templates.md): context, pending renders, responses, and forms.
2. [Layouts and helpers](template-language.md): Jinja, links, sessions, translation, and escaping.
3. [Configuration and extensions](configuration-and-extensions.md): loaders, caches, providers, and diagnostics.

Requires Python 3.14+ and the Jinja2/MarkupSafe/Markdown/msgspec dependencies declared by the project. The facade needs a booted application; isolated-engine examples are useful for tests and extensions.

## Bounded execution and performance

Top-level cold template loading/compilation and auto-reload checks run in a dedicated pool (two workers, 64 pending). With auto-reload disabled, a hot Jinja template is read directly from its bounded cache. Rendering and async globals stay on the calling loop. `await engine.warmup("page", "layouts/base", "partials/menu")` compiles known templates without evaluating globals.

Jinja's nested `include`/`extends`/import loaders remain synchronous inside its renderer. Warm the known dependency graph before serving traffic; dynamic names and auto-reload of nested templates may still perform synchronous loader I/O. Warmup does not replace Jinja's cache capacity or guarantee residency after eviction. Overload is explicit through `WorkQueueFullError`.
