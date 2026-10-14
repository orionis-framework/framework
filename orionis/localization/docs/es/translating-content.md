# Publicar y traducir contenido por idioma

Organiza los recursos por idioma, decide un fallback y pasa el idioma explícitamente cuando depende de una solicitud. Las traducciones, el fallback y los plurales son operaciones síncronas con una caché por proceso.

## Requisitos

- Python 3.14 o posterior.
- Archivos JSON UTF-8 cuyo valor raíz sea un objeto.
- Una ruta de idiomas válida para traducciones basadas en archivos.
- Una aplicación Orionis iniciada al usar `orionis.support.facades.Lang`.
## Inicio rápido

```python
from pathlib import Path
from orionis.localization import TranslationLoader, TranslationRepository, Translator

loader = TranslationLoader(Path("resources/lang"))
repository = TranslationRepository(loader)
translator = Translator(locale="en", fallback="en", loader=loader, repository=repository)
assert translator.get("Welcome") == "Welcome"
assert translator.get("Welcome", locale="es") == "Bienvenido"
assert translator.availableLocales() == ("en", "es")
print(translator.getLocale())
```

## Crear recursos que puedas mantener

Crea `resources/lang/en/cart.json` y su equivalente `resources/lang/es/cart.json` con un objeto JSON en cada archivo. Una declaración como `{"items": "{0} Empty|{1} One item|[2,*] :count items"}` se consulta con la clave `cart.items`. Las carpetas de grupo no se recorren recursivamente: el loader busca archivos `*.json` directamente bajo el directorio del idioma.

Para una clave literal de interfaz puedes usar `resources/lang/es.json`. Este archivo se carga después de los grupos y gana en una colisión; evita definir la misma clave en ambos lugares para que la procedencia resulte clara. Un idioma inexistente devuelve un mapa vacío y puede llegar al fallback. El descubrimiento informa qué recursos existen, no que cada traducción esté completa.

El código del idioma distingue mayúsculas y separadores: `es-CO`, `es_CO` y `es` son nombres distintos. No existe fallback jerárquico automático `es-CO` → `es`: solo se prueba el fallback configurado. Valida el valor solicitado contra los idiomas admitidos por tu aplicación antes de usarlo, además de la validación sintáctica que ya proporciona el translator.

### Idioma por solicitud y actualizaciones

Usa `Lang.get("cart.items", locale=requested_locale)` o `Lang.choice("cart.items", quantity, locale=requested_locale)`. No cambies `setLocale()` para una solicitud concurrente: el provider entrega un singleton mutable. En una plantilla Jinja pasa igualmente `locale=` a `trans`, `__` o `choice`; Jinja espera helpers async automáticamente.

La caché no vigila cambios de archivos. Tras publicar recursos actualizados, reinicia cada worker o invalida los idiomas en cada proceso. `reload("es")` descarta el mapa; la lectura siguiente vuelve a cargarlo. No cambia la configuración, no actualiza otros procesos y no valida el JSON inmediatamente. Los métodos de traducción son síncronos: precalentar idiomas durante boot evita I/O de archivos en la primera solicitud.

Los contratos `ITranslationLoader` y `ITranslationRepository` permiten fuentes distintas a archivos y políticas de caché propias. Inyéctalos al construir `Translator`; el manager estándar construye sus implementaciones concretas y no dispone de un registro de drivers. No hay reglas ICU/CLDR automáticas: escribe selectores explícitos cuando dos formas no basten.

## Conceptos principales

### Fuentes y claves

`{locale}.json` sirve para claves de texto fuente literal. `{locale}/{group}.json` se aplana recursivamente bajo el nombre del grupo. Los archivos agrupados se cargan ordenados; luego el archivo raíz se combina al final y gana las colisiones. Las hojas no string se convierten con `str()`.

### Resolución y fallback

`get(key, locale=None, **replace)` consulta el locale explícito o activo y después el fallback configurado si es diferente. Si ninguno contiene la clave, un handler de claves ausentes puede devolver una línea; de lo contrario se devuelve la propia clave. `has(..., fallback=False)` limita la comprobación al locale solicitado.

### Reemplazo

Los placeholders usan `:name`. El traductor también reemplaza `:Name` por valor capitalizado y `:NAME` por valor en mayúsculas. Los nombres más largos se procesan primero para impedir que un nombre corto consuma un prefijo largo.

### Selección plural

`choice(key, count, ...)` divide la línea por `|`. Admite selectores exactos como `{0}` o `{1}`, rangos inclusivos como `[2,10]` y `*` como extremo abierto. Sin selector explícito coincidente, un único segmento se usa siempre; con varios, count `1` elige el primero y los demás el segundo. `:count` se inyecta automáticamente.

## Flujos de trabajo comunes

### Traducir texto de aplicación

Use `Lang.get("Welcome")` en código de aplicación iniciado. Prefiera claves dotted estables para validación y mensajes de dominio; las claves literales son prácticas para copy de UI ya existente. Pase reemplazos como argumentos keyword.

### Elegir locale por solicitud

Pase `locale=` a `get`, `has` o `choice`. Evite `setLocale()` por solicitud porque el provider comparte un traductor en todo el proceso y las solicitudes concurrentes observarían la mutación.

### Actualizar traducciones durante desarrollo

Llame `Lang.reload("es")` después de modificar un archivo, o `Lang.reload()` / `Lang.flush()` para descartar todos los locales. El siguiente lookup carga de nuevo. Cada worker de producción tiene caché independiente y debe invalidarse o reiniciarse.

### Reportar claves ausentes

Registre `missing(lambda key, locale: ...)` para telemetría o sustitución controlada. Mantenga el handler rápido y no recursivo. Devolver `None` conserva el comportamiento de devolver la clave.

## Ejemplos

### Aplicar fallback y reemplazos

```python
from orionis.localization import TranslationRepository, Translator


class MemoryLoader:
    data = {
        "en": {"greeting": "Hello :name"},
        "es": {},
    }

    def load(self, locale: str) -> dict[str, str]:
        return dict(self.data.get(locale, {}))

    def availableLocales(self) -> tuple[str, ...]:
        return tuple(sorted(self.data))


loader = MemoryLoader()
repository = TranslationRepository(loader)
translator = Translator(locale="es", fallback="en", loader=loader, repository=repository)
assert translator.get("greeting", name="Ada") == "Hello Ada"
assert translator.has("greeting")
assert not translator.has("greeting", fallback=False)
print(translator.get("missing.key"))
```


### Seleccionar formas plurales

```python
from orionis.localization import TranslationRepository, Translator


class MemoryLoader:
    def load(self, locale: str) -> dict[str, str]:
        return {"apples": "{0} No apples|{1} One apple|[2,*] :count apples"}

    def availableLocales(self) -> tuple[str, ...]:
        return ("en",)


loader = MemoryLoader()
translator = Translator(
    locale="en",
    fallback="en",
    loader=loader,
    repository=TranslationRepository(loader),
)
assert translator.choice("apples", 0) == "No apples"
assert translator.choice("apples", 1) == "One apple"
assert translator.choice("apples", 7) == "7 apples"
print(translator.choice("apples", 2))
```


### Manejar claves ausentes

```python
from orionis.localization import TranslationRepository, Translator


class EmptyLoader:
    def load(self, locale: str) -> dict[str, str]:
        return {}

    def availableLocales(self) -> tuple[str, ...]:
        return ()


loader = EmptyLoader()
translator = Translator(
    locale="en",
    fallback="en",
    loader=loader,
    repository=TranslationRepository(loader),
)
translator.missing(lambda key, locale: f"[{locale}] {key}")
assert translator.get("unknown") == "[en] unknown"
translator.missing(None)
assert translator.get("unknown") == "unknown"
print("missing handler removed")
```


### Inspeccionar e invalidar la caché

```python
from pathlib import Path
from orionis.localization import TranslationLoader, TranslationRepository

repository = TranslationRepository(TranslationLoader(Path("resources/lang")))
assert repository.loadedLocales() == ()
assert repository.get("en")["Welcome"] == "Welcome"
assert repository.loadedLocales() == ("en",)
assert repository.forget("en")
assert repository.loadedLocales() == ()
print("cache cleared")
```


### Usar la facade de aplicación

```python
from orionis.support.facades import Lang

title = Lang.get("Welcome")
message = Lang.choice("cart.items", 3, user="Ada")
available = Lang.availableLocales()
```

## Configuración

Localización usa campos de `config/app.py`:

| Ajuste | Entorno | Predeterminado | Significado |
|---|---|---|---|
| `app.locale` | `APP_LOCALE` | `en` | Locale activo compartido. |
| `app.fallback_locale` | `APP_FALLBACK_LOCALE` | `en` | Locale secundario para claves ausentes. |
| `app.language_path` | `APP_LANGUAGE_PATH` | `resources/lang/` | Ruta absoluta o relativa a la raíz. |

Los códigos deben contener grupos alfanuméricos separados solo por `-` o `_`, por ejemplo `en`, `es-CO` o `pt_BR`. Se conservan exactamente; normalizar mayúsculas y separadores corresponde a la aplicación.

## Integración con Orionis

`LocalizationProvider` enlaza `ILocalizationManager` a `LocalizationManager` como singleton. Al iniciar, materializa el traductor, enlaza `ITranslator` y fija la facade `Lang`. Las plantillas reciben helpers/globales de localización y las respuestas predeterminadas usan traducciones para páginas visibles.

La construcción directa es útil para bibliotecas y pruebas. El código de aplicación debería inyectar `ITranslator` o usar `Lang`; ambos apuntan al mismo singleton configurado.

## Errores y casos límite

- Códigos malformados o similares a rutas producen `InvalidLocaleException` antes de tocar el filesystem.
- UTF-8 inválido, JSON malformado o raíz no objeto produce `TranslationSyntaxException`.
- Un archivo eliminado entre descubrimiento y lectura produce `TranslationFileNotFoundException`.
- Directorios/locales ausentes no son errores: descubrimiento devuelve `()` y carga `{}`.
- Las claves ausentes se devuelven a sí mismas salvo que un handler entregue un string.
- El reemplazo es sustitución literal, no parsing MessageFormat; placeholders no usados permanecen.
- Los rangos plurales son numéricos e inclusivos. Condiciones malformadas no coinciden; cantidades no numéricas pueden propagar `TypeError` de comparación.
- Los archivos raíz prevalecen sobre claves agrupadas en colisión. Los grupos se combinan determinísticamente por nombre.
- `reload()` invalida mapas; no lee ni valida proactivamente archivos cambiados.

## Rendimiento y concurrencia

JSON se decodifica con `msgspec`; los diccionarios anidados se aplanan una vez al primer acceso al locale. Los lookups posteriores son O(1). Descubrimiento y carga son síncronos; precargue locales requeridos durante bootstrap si importa la latencia inicial.

El provider comparte un traductor mutable sin lock. Las lecturas concurrentes son apropiadas después de calentar cachés, pero `setLocale`, `missing`, `reload`, `forget` y `flush` son mutaciones globales y pueden competir. Prefiera `locale=` explícito por solicitud y coordine operacionalmente la invalidación.

## API pública

El paquete exporta `TranslationLoader`, `TranslationRepository`, `Translator`, `LocalizationManager`, `TranslationException`, `InvalidLocaleException`, `TranslationFileNotFoundException` y `TranslationSyntaxException`.

### `TranslationLoader(path)`

`load(locale)` devuelve un `dict[str, str]` plano; un locale desconocido produce un diccionario vacío. `availableLocales()` devuelve una tupla ordenada tomada de archivos `.json` raíz y directorios con archivos de grupo. El loader no mantiene caché deliberadamente.

### `TranslationRepository(loader)`

`get(locale)` carga una vez y devuelve el mapa en caché. `has(locale)`, `forget(locale)`, `flush()` y `loadedLocales()` inspeccionan o invalidan esa caché local al proceso. El orden de locales cargados sigue el de inserción.

### `Translator`

- `get`, `has` y `choice` realizan traducciones por llamada.
- `setLocale` y `getLocale` controlan el locale activo compartido.
- `availableLocales` delega descubrimiento al loader.
- `reload(locale=None)`, `forget(locale)` y `flush()` invalidan entradas.
- `missing(handler)` instala o retira un callback de claves ausentes en ese traductor.

### `LocalizationManager(app)`

`translator()` crea perezosamente un traductor con `app.locale`, `app.fallback_locale` y `app.language_path`. Las rutas relativas se resuelven contra `app.basePath`.

## Referencia de implementación para extensiones

| Ruta | Responsabilidad |
|---|---|
| `loader.py` | Descubrir, decodificar, combinar y aplanar recursos JSON. |
| `repository.py` | Caché lazy en memoria por locale. |
| `translator.py` | Lookup, fallback, interpolación, pluralización, locale y caché. |
| `manager.py` | Construir y conservar un traductor desde configuración. |
| `provider.py` | Registrar servicios y fijar `Lang`. |
| `types.py` | Aliases de mapas, caché y handler de ausencias. |
| `exceptions.py` | Jerarquía de errores de localización. |
| `contracts/` | Interfaces de loader, repositorio, traductor y manager. |

---

[Índice](README.md) · [view](../../../view/docs/es/README.md) · [foundation](../../../foundation/docs/es/README.md)
