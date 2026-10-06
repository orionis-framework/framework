# orionis.localization

> `orionis.localization` carga recursos JSON, guarda traducciones aplanadas, aplica fallback y reemplazos, y selecciona formas plurales.

## Descripción general

El pipeline de localización tiene cuatro capas pequeñas: `TranslationLoader` lee recursos, `TranslationRepository` mantiene la caché por locale, `Translator` resuelve traducciones y plurales, y `LocalizationManager` las conecta desde la configuración. `LocalizationProvider` expone el traductor compartido mediante el contenedor y la facade `Lang`.

Los recursos pueden ser archivos raíz como `resources/lang/es.json`, donde las claves son textos fuente literales, o archivos agrupados como `resources/lang/es/validation.json`, aplanados a claves como `validation.required`.

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

Validación: **Ejecutado correctamente** desde la raíz del repositorio en CPython 3.14.6.

## Conceptos principales

### Fuentes y claves

`{locale}.json` sirve para claves de texto fuente literal. `{locale}/{group}.json` se aplana recursivamente bajo el nombre del grupo. Los archivos agrupados se cargan ordenados; luego el archivo raíz se combina al final y gana las colisiones. Las hojas no string se convierten con `str()`.

### Resolución y fallback

`get(key, locale=None, **replace)` consulta el locale explícito o activo y después el fallback configurado si es diferente. Si ninguno contiene la clave, un handler de claves ausentes puede devolver una línea; de lo contrario se devuelve la propia clave. `has(..., fallback=False)` limita la comprobación al locale solicitado.

### Reemplazo

Los placeholders usan `:name`. El traductor también reemplaza `:Name` por valor capitalizado y `:NAME` por valor en mayúsculas. Los nombres más largos se procesan primero para impedir que un nombre corto consuma un prefijo largo.

### Selección plural

`choice(key, count, ...)` divide la línea por `|`. Admite selectores exactos como `{0}` o `{1}`, rangos inclusivos como `[2,10]` y `*` como extremo abierto. Sin selector explícito coincidente, un único segmento se usa siempre; con varios, count `1` elige el primero y los demás el segundo. `:count` se inyecta automáticamente.

## Estructura del módulo

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

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

Validación: **Ejecutado correctamente** en CPython 3.14.6.

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

Validación: **Ejecutado correctamente** desde la raíz del repositorio en CPython 3.14.6.

### Usar la facade de aplicación

```python
from orionis.support.facades import Lang

title = Lang.get("Welcome")
message = Lang.choice("cart.items", 3, user="Ada")
available = Lang.availableLocales()
```

Validación: **Solo importación** en CPython 3.14.6; las llamadas requieren una aplicación iniciada y la facade fijada.

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

## Compatibilidad

Orionis declara Python 3.14+ y usa JSON UTF-8. La sintaxis de traducción es propia de Orionis, no ICU MessageFormat. Los identificadores son códigos opacos seguros, no se validan automáticamente contra CLDR ni el sistema operativo. `pathlib` mantiene lookup consistente en Windows y POSIX.

## Notas de verificación

La validación usó CPython 3.14.6. Se inspeccionaron exports, contratos, precedencia/aplanado del loader, caché, fallback/reemplazos/plurales, manager, provider, facade, configuración, integración de plantillas y todas las pruebas de `tests/localization`. Los **148** métodos de prueba pasaron con el runner de Orionis. Cuatro programas directos se ejecutaron correctamente; el ejemplo de facade se validó solo por importación.
