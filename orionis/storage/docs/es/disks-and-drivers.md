# Configurar discos, publicación y drivers

Storage permite guardar contenido y trabajar con archivos mediante el mismo contrato async en discos locales, efímeros o cloud.

## Configurar discos y credenciales

La configuración incluida admite nombres `local`, `public`, `s3`, `azure` y `gcs`. Un nombre de disco selecciona una entrada; su atributo `driver` selecciona la implementación. `local` y `public` usan el mismo driver local con distintas raíces. También puedes asignar el driver `memory` a una entrada existente para un entorno aislado.

`Filesystems` y `Disks` validan los campos conocidos: añadir arbitrariamente `private` o `archive` a un dict no crea automáticamente un disco. El manager puede leer atributos de un objeto de configuración extendido, pero si necesitas nuevos nombres debes diseñar entidades/configuración compatibles y su validación. Para una integración pequeña es más sencillo cambiar el driver de una entrada existente.

| Proveedor | Extra de Orionis | Datos consumidos / predeterminados |
|---|---|---|
| Local | ninguno | `LOCAL_PATH=storage/app/private`; public usa `PUBLIC_PATH=storage/app/public`, `PUBLIC_URL=/static`. |
| S3 | `s3` (`boto3>=1.43.99`) | `S3_KEY`, `S3_SECRET`, `S3_REGION=us-east-1`, `S3_BUCKET`, URL/endpoint opcionales, path style desactivado. |
| Azure Blob | `azure` (`azure-storage-blob>=12.30.2`) | connection string o cuenta/clave; `AZURE_CONTAINER`; URL opcional. |
| GCS | `gcs` (`google-cloud-storage>=3.14.1`) | proyecto, bucket, archivo de clave opcional o credenciales por defecto del SDK. |

El extra agregado `storage` instala los tres SDK. La construcción del driver es lazy y no valida una conexión de red; el primer I/O puede lanzar `MissingStorageDependencyException` con indicación de instalación o una excepción del SDK. Las credenciales y permisos siguen las políticas del proveedor. No existe failover ni política de reintentos común en `StorageManager`.

### Visibilidad y publicación

`url()` construye una ubicación: no concede permisos ni crea una ruta estática del servidor. En local/memory requiere `base_url`; en cloud se puede derivar del proveedor o de la URL configurada. Mantén el disco privado como fuente de archivos confidenciales y autoriza cada descarga.

`temporaryUrl(expires_in=3600)` admite firmas en S3, Azure y GCS, según credenciales. Local y memory lanzan `UnsupportedStorageOperationException`. Azure requiere la clave de cuenta para SAS y no implementa ACL por blob: el parámetro visibility se ignora al escribir, y `setVisibility()` falla explícitamente; configura el contenedor. S3/GCS dependen de que las políticas del bucket permitan las ACL solicitadas. Una URL válida no demuestra existencia, autorización del usuario de tu aplicación ni alcance público.

### Registrar un driver

Implementa `IStorageDriver` y registra una factory síncrona `factory(config)` durante boot antes del primer acceso. `extend()` acepta también reemplazar nombres integrados y limpia la caché de discos; las referencias antiguas que ya guardaste siguen usando el driver anterior. No cambies el registro mientras hay solicitudes concurrentes. La factory no recibe la aplicación ni se espera como corrutina: captura dependencias explícitamente si las necesitas.

Este ejemplo registra un driver de memoria con nombre propio sobre la entrada `local`, sin crear archivos:

```python
import asyncio
from pathlib import Path
from orionis.storage import MemoryStorageDriver, StorageManager


class App:
    basePath = Path.cwd()

    def config(self, name: str) -> dict:
        return {
            "default": "local",
            "disks": {"local": {"driver": "scratch", "path": "unused"}},
        }


async def main() -> None:
    manager = StorageManager(App())
    manager.extend("scratch", lambda config: MemoryStorageDriver())
    file = await manager.disk().put("check.txt", "ok")
    assert await file.read() == b"ok"


asyncio.run(main())
```

## Configuración

`config/filesystems.py` selecciona `FILESYSTEM_DISK` (`local`) y define:

- Local: `LOCAL_PATH` (`storage/app/private`).
- Public: `PUBLIC_PATH` (`storage/app/public`) y `PUBLIC_URL` (`/static`).
- S3: `S3_KEY`, `S3_SECRET`, `S3_REGION`, `S3_BUCKET`, `S3_URL`, `S3_ENDPOINT`, `S3_USE_PATH_STYLE_ENDPOINT`.
- Azure: `AZURE_CONNECTION_STRING` o `AZURE_ACCOUNT_NAME`/`AZURE_ACCOUNT_KEY`, `AZURE_CONTAINER`, `AZURE_URL`.
- GCS: `GCS_PROJECT_ID`, `GCS_KEY_FILE`, `GCS_BUCKET`, `GCS_URL`.

Rutas relativas se anclan al base path. Credenciales vacías son placeholders; entities validan forma y SDK valida credenciales al usar.



## Integración con Orionis

`StorageProvider` deferrable enlaza singleton y fachada. HTTP bufferiza uploads; manager los adapta sin acoplar drivers. Las reglas Schema de archivo/imagen validan el contrato del payload HTTP antes de adaptarlo a storage.

Discos public suelen emparejar `PUBLIC_URL=/static` con routing estático. La configuración por sí sola no publica el directorio.



### Usar fachada

```python
from orionis.support.facades import Storage


async def publish_manifest() -> str:
    file = await Storage.disk("public").put(
        "build/manifest.json", '{"version": 1}', visibility="public",
    )
    return await file.url()
```

## Errores y casos límite

- Rutas inválidas producen `StoragePathException`; archivos requeridos ausentes, `StorageFileNotFoundException`.
- Features no soportadas producen `UnsupportedStorageOperationException`.
- Disco/driver desconocido producen `DiskNotFoundException`/`DriverNotSupportedException`.
- Overwrite sigue contrato/semántica del backend.
- MIME no valida contenido; hash/ETag varían.
- Cloud depende de consistencia, paginación, credenciales y red.
- Streams abiertos deben cerrarse; close/flush puede publicar writes.



## Concurrencia y límites

Los wrappers son ligeros; cada disco se construye y cachea en el manager. Local publica `write()` y `writeStream()` con temporales únicos y reemplazo: lectores no observan bytes mezclados, pero escritores concurrentes tienen semántica de último reemplazo. Un flujo `exists()` seguido de `write()` no garantiza crear solo si falta. Memory es efímero y no sincroniza threads ni procesos. Los drivers cloud dependen de SDK, red y consistencia del servicio.

No hay transacciones entre múltiples archivos, lock de negocio ni compare-and-swap común. Coordina operaciones sobre la misma clave desde la aplicación. Mantén límites de tamaño, disco temporal y concurrencia: spooling protege RAM a costa de I/O local y no hace el trabajo ilimitado.


## Compatibilidad

Todos implementan `IStorageDriver`, pero ACL, URL firmada, timestamps, ETag, checksum y directorios no son equivalentes. La API usa rutas POSIX relativas incluso en Windows.

`normalizePath`/`normalizeFilePath` siguen como aliases legacy; código nuevo debe usar snake_case.

## Referencia de implementación para extensiones

| Ruta | Responsabilidad |
|---|---|
| `manager.py`, `provider.py` | Config, discos lazy, drivers custom y fachada. |
| `disk.py`, `file.py`, `directory.py` | API neutral. |
| `stream.py`, `uploaded_file.py` | Handles async y uploads HTTP. |
| `paths.py` | Normalización y rechazo de traversal. |
| `drivers/local.py`, `drivers/memory.py` | Implementaciones local/efímera. |
| `drivers/s3.py`, `drivers/azure.py`, `drivers/gcs.py` | Cloud opcional. |
| `entities/file_info.py`, `enums/visibility.py` | Metadata y visibilidad. |
| `contracts/`, `exceptions.py` | Interfaces y fallos tipados. |

---

[Índice](README.md) · [http](../../../http/docs/es/README.md) · [container](../../../container/docs/es/README.md) · [mail](../../../mail/docs/es/README.md)
