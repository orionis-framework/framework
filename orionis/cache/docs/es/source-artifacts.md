# Cachear artefactos derivados de fuentes

Usa una caché de artefactos cuando un diccionario calculado depende de archivos de código.

## Reconstruir cuando cambian fuentes

`FileBasedCache` es síncrono y guarda un diccionario completo, adecuado para metadatos compilados. En el arranque, llama a `get()`; si devuelve `None`, reconstruye el resultado, llama a `save(data)` y utiliza ese diccionario. No ofrece TTL, claves independientes ni locks distribuidos.

La huella usa ruta absoluta, `st_mtime_ns` y tamaño de los archivos. No calcula un hash del contenido completo: una modificación que conserve esos metadatos puede pasar inadvertida. Los directorios monitoreados solo añaden `*.py`; `monitored_files` permite declarar archivos concretos adicionales. La consulta de huella se memoiza 0,5 segundos; durante esa ventana un cambio aún puede no invalidar el resultado. Esa ventana es distinta a un TTL del artefacto.

`save()` acepta únicamente un `dict`, conserva versión y huella, y omite reescribir cuando todo coincide. El archivo se publica con un temporal hermano y reemplazo. Dos productores pueden calcular y guardar resultados diferentes: no hay exclusión de construcción y prevalece el último reemplazo. Coordina la compilación si esa carrera importa.

### Serializar tipos de framework

`from orionis.cache.serializer import Serializer` expone `dumps`, `loads`, `dumpToFile` y `loadFromFile`. Además de contenedores y primitivos, admite bytes, Path, fechas/horas, timedelta, Decimal, UUID, complejos, tuplas, sets, frozensets, enums, tipos y el sentinel `MISSING`. Usa marcadores `__type__` y `__value__`; evita utilizar esos nombres en mapas de negocio que deban volver intactos.

Este formato es para artefactos locales de confianza. La reconstrucción de enums y tipos puede importar módulos por nombre: no deserialices payloads aportados por clientes ni archivos modificables por usuarios no confiables. No incluye firma ni cifrado. Un archivo ausente, vacío o ilegible devuelve `None` en `loadFromFile`; JSON corrupto o un marcador desconocido puede propagar un error. Trata el caché como regenerable y define si tu arranque lo descarta o falla.


### Invalidar un artefacto cuando cambia una fuente

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from orionis.cache import FileBasedCache


with TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "feature.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")

    cache = FileBasedCache(root, "compiled.cache", monitored_files=[source])
    cache.save({"routes": ["/"]})
    print(cache.get())  # {'routes': ['/']}

    source.write_text("VALUE = 2\n", encoding="utf-8")
    time.sleep(0.6)  # FileBasedCache refreshes its source hash every 0.5 s.
    print(cache.get())  # None
```

### `FileBasedCache`

```text
FileBasedCache(
    path: Path,
    filename: str,
    monitored_dirs: list[Path] | None = None,
    monitored_files: list[Path] | None = None,
)
```

`save(data)` escribe un payload versionado y devuelve `(CACHE_VERSION, sources_hash)`; datos y hash idénticos omiten reescritura. `get()` devuelve el diccionario solo si versión y hash coinciden, o `None`. `clear()` indica si existía el archivo. Solo participan archivos Python de directorios monitorizados y se excluye el propio archivo de caché.

---

[Índice](README.md) · [foundation](../../../foundation/docs/es/README.md)
