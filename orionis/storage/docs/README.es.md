# Orionis Storage (`orionis.storage`)

> Almacenamiento de archivos asíncrono e independiente del medio: una sola API para discos locales, discos en memoria, Amazon S3, Azure Blob Storage y Google Cloud Storage.

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
  - [Dónde encaja en el framework](#dónde-encaja-en-el-framework)
  - [Flujo entre componentes](#flujo-entre-componentes)
  - [Mapa de archivos](#mapa-de-archivos)
  - [Decisiones de diseño](#decisiones-de-diseño)
- [Referencia de API](#referencia-de-api)
  - [`StorageManager`](#storagemanager)
  - [`Disk`](#disk)
  - [`File`](#file)
  - [`Directory`](#directory)
  - [`UploadedFile`](#uploadedfile)
  - [`AsyncStream`](#asyncstream)
  - [`IStorageDriver`](#istoragedriver)
  - [`LocalStorageDriver`](#localstoragedriver)
  - [`MemoryStorageDriver`](#memorystoragedriver)
  - [`S3StorageDriver`](#s3storagedriver)
  - [`AzureStorageDriver`](#azurestoragedriver)
  - [`GoogleStorageDriver`](#googlestoragedriver)
  - [Funciones auxiliares de los drivers](#funciones-auxiliares-de-los-drivers)
  - [`FileInfo`](#fileinfo)
  - [`Visibility`](#visibility)
  - [Normalización de rutas](#normalización-de-rutas)
  - [Excepciones](#excepciones)
  - [`StorageProvider` y la facade `Storage`](#storageprovider-y-la-facade-storage)
  - [Claves de configuración](#claves-de-configuración)
- [Ejemplos de uso](#ejemplos-de-uso)
  - [Resolver un disco con la facade](#resolver-un-disco-con-la-facade)
  - [Manejo de errores](#manejo-de-errores)
  - [Streaming de archivos grandes](#streaming-de-archivos-grandes)
  - [Guardar un archivo subido por HTTP](#guardar-un-archivo-subido-por-http)
  - [Ejecución autónoma con el driver en memoria](#ejecución-autónoma-con-el-driver-en-memoria)
  - [Registrar un driver personalizado](#registrar-un-driver-personalizado)
- [Consideraciones de rendimiento y concurrencia](#consideraciones-de-rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)

## Requisitos

Los drivers `local` y `memory` no requieren nada más allá de `pip install orionis`: solo
usan la biblioteca estándar (`asyncio`, `hashlib`, `mimetypes`, `shutil`, `pathlib`,
`secrets`, `io`, `urllib.parse`).

Los drivers de nube usan el SDK oficial de cada plataforma, declarado como **dependencia
opcional** en `pyproject.toml`:

| Driver | Paquete PyPI | Versión mínima | Instalación |
| --- | --- | --- | --- |
| `S3StorageDriver` | `boto3` | `>=1.35` | `pip install orionis[s3]` |
| `AzureStorageDriver` | `azure-storage-blob` | `>=12.24` | `pip install orionis[azure]` |
| `GoogleStorageDriver` | `google-cloud-storage` | `>=2.18` | `pip install orionis[gcs]` |
| Los tres a la vez | — | — | `pip install orionis[storage]` |

El SDK nunca se importa al construir el driver: cada uno arranca su cliente en la primera
operación mediante `importDriverDependency()`, de modo que un paquete ausente lanza
`MissingStorageDependencyException` con el comando exacto de instalación en lugar de un
`ImportError` durante el arranque.

## Descripción funcional

### Dónde encaja en el framework

`orionis.storage` da acceso uniforme y totalmente asíncrono al almacenamiento de archivos,
sin importar el medio físico que haya detrás. El código de la aplicación siempre habla con
los mismos objetos (`Disk`, `File`, `Directory`); cambiar un disco local por un bucket de
S3 es un cambio de configuración, no de código.

Relaciones directas con otros módulos:

- `orionis.foundation.config.filesystems` — aporta las entidades de configuración
  `Filesystems` / `Disks` que `StorageManager` lee vía `app.config("filesystems")`.
- `orionis.foundation` (`core_providers.py`) — registra `StorageProvider`.
- `orionis.container` — resuelve `IStorageManager` y sostiene la facade `Storage`.
- `orionis.http.payload` — produce el payload multipart que `UploadedFile` adapta. El
  contrato HTTP se importa solo bajo `TYPE_CHECKING`, así que el módulo de storage nunca
  depende de la capa HTTP en tiempo de ejecución.

### Flujo entre componentes

```text
Storage (facade)  ->  IStorageManager
                        |
                        |  disk(name) / default()          cacheado por nombre
                        v
                      Disk  ------------------------------ IStorageDriver
                        |                                   (local | memory |
                        |  file(path) / directory(path)      s3 | azure | gcs |
                        v                                    custom vía extend)
              File            Directory
                |                 |
                |  open()         |  files() / directories()
                v                 v
           AsyncStream        list[File] / list[Directory]

UploadedFile  ->  manager.disk(disk).file(target).writeStream(chunks)
```

Toda operación de `Disk`, `File` y `Directory` se delega al driver, y el driver solo habla
en rutas canónicas relativas a la raíz producidas por `normalizePath()` /
`normalizeFilePath()`.

### Mapa de archivos

| Archivo | Contenido |
| --- | --- |
| `manager.py` | `StorageManager`: lee la configuración, construye y cachea discos, registra drivers personalizados y adapta cargas HTTP. |
| `disk.py` | `Disk`: fábrica de objetos `File` / `Directory` más métodos de conveniencia que siempre delegan en ellos. |
| `file.py` | `File`: todas las operaciones sobre un archivo (contenido, metadatos, reubicación, URLs). |
| `directory.py` | `Directory`: creación, borrado, existencia y listados que devuelven objetos, nunca cadenas. |
| `uploaded_file.py` | `UploadedFile`: adapta un payload multipart HTTP para persistirlo en cualquier disco. |
| `stream.py` | `AsyncStream`: envoltorio asíncrono sobre un handle binario abierto de forma perezosa. |
| `paths.py` | `normalizePath()` / `normalizeFilePath()`: forma canónica y protección ante traversal. |
| `exceptions.py` | Jerarquía de excepciones con raíz en `StorageException`. |
| `provider.py` | `StorageProvider`: vincula `IStorageManager` y fija la facade `Storage`. |
| `contracts/` | ABCs: `IStorageManager`, `IDisk`, `IFile`, `IDirectory`, `IUploadedFile`, `IStorageStream`, `IStorageDriver`. |
| `drivers/local.py` | `LocalStorageDriver` (sistema de archivos, escrituras atómicas, permisos POSIX). |
| `drivers/memory.py` | `MemoryStorageDriver` (diccionarios en proceso, para tests/uso efímero). |
| `drivers/s3.py` | `S3StorageDriver` (Amazon S3 y servicios compatibles). |
| `drivers/azure.py` | `AzureStorageDriver` (Azure Blob Storage). |
| `drivers/gcs.py` | `GoogleStorageDriver` (Google Cloud Storage). |
| `drivers/functions.py` | Helpers compartidos por los drivers: import perezoso, validación de modos, destino de descarga, filtrado de claves. |
| `entities/file_info.py` | `FileInfo`: instantánea inmutable de metadatos. |
| `enums/visibility.py` | `Visibility`: `PUBLIC` / `PRIVATE`. |

### Decisiones de diseño

- **Patrón driver** — `IStorageDriver` aísla el medio; `File` / `Directory` / `Disk` nunca
  saben sobre qué backend corren, así que el mismo código sirve para todos los discos.
- **Sin lógica duplicada** — `Disk.put/exists/delete/copy/move` delegan en `File`, y
  `Directory.files()` construye objetos `File`; hay una sola implementación por comportamiento.
- **`__slots__` en todas las clases concretas** (`StorageManager`, `Disk`, `File`,
  `Directory`, `UploadedFile`, `AsyncStream`, todos los drivers) **y `__slots__ = ()` en
  todos los contratos** — las instancias no llevan diccionario de atributos, lo que acota
  la memoria por objeto.
- **Metadatos inmutables** — `FileInfo` es un `@dataclass(frozen=True, kw_only=True, slots=True)`,
  así que la instantánea se puede pasar de un lado a otro sin riesgo de mutación.
- **Import perezoso del SDK** — los constructores de los drivers de nube no hacen E/S ni
  importaciones, lo que permite construirlos (y probarlos) sin el SDK instalado.
- **Normalización de rutas en el borde** — `File` y `Directory` normalizan en `__init__`,
  de modo que los drivers pueden asumir que la ruta ya es segura.
- **Provider diferible** — `StorageProvider` implementa `DeferrableProvider`, así que nada
  del stack de storage se construye hasta que se resuelve `IStorageManager` por primera vez.

## Referencia de API

### `StorageManager`

`orionis.storage.manager.StorageManager` — implementa
`orionis.storage.contracts.manager.IStorageManager`.

`__slots__ = ("_app", "_base_path", "_config", "_custom", "_default", "_disks")`

```python
def __init__(self, app: IApplication) -> None
```

Lee `app.config("filesystems")` y, cuando es un `dict`, lo convierte en la entidad
validada `Filesystems`. Guarda `app.basePath` como ancla de las raíces locales relativas y
el nombre del disco `default` configurado.

| Método | Firma | Descripción |
| --- | --- | --- |
| `disk` | `disk(name: str \| None = None) -> IDisk` | Resuelve el disco declarado con ese nombre (o el default). Se construye en el primer acceso y se cachea en `_disks`. Lanza `DiskNotFoundException` si el disco no está declarado y `DriverNotSupportedException` si su `driver` no tiene implementación. |
| `default` | `default() -> IDisk` | Atajo de `disk()`. |
| `extend` | `extend(driver: str, factory: Callable[[object], IStorageDriver]) -> None` | Registra una fábrica para un nombre de driver. La fábrica recibe la entidad de configuración del disco y debe devolver un driver listo. **Efecto secundario:** limpia la caché de discos para que las resoluciones siguientes la tomen en cuenta. |
| `uploaded` | `uploaded(source: IHttpUploadedFile) -> IUploadedFile` | Envuelve un payload multipart HTTP en un `UploadedFile` ligado a este manager. |

Orden de resolución del driver dentro del privado `__buildDriver()`:

1. Fábrica registrada con `extend()` para el valor `driver` del disco (siempre gana).
2. `"local"` → `LocalStorageDriver`, con raíz en `config.path`; las rutas relativas se
   anclan a `app.basePath` y `config.url` pasa a ser la URL pública base.
3. `"memory"` → `MemoryStorageDriver(base_url=config.url)`.
4. `"aws"` o `"s3"` → `S3StorageDriver(config)`.
5. `"azure"` → `AzureStorageDriver(config)`.
6. `"gcs"` o `"google"` → `GoogleStorageDriver(config)`.
7. Cualquier otro valor → `DriverNotSupportedException`.

### `Disk`

`orionis.storage.disk.Disk` — implementa `orionis.storage.contracts.disk.IDisk`.

`__slots__ = ("_driver", "_name")`

```python
def __init__(self, name: str, driver: IStorageDriver) -> None
```

| Método | Firma | Descripción |
| --- | --- | --- |
| `name` | `name() -> str` | Nombre de configuración del disco. |
| `file` | `file(path: str) -> IFile` | Construye un `File` ligado a este driver. Lanza `StoragePathException` si la ruta es inválida o resuelve a la raíz. |
| `directory` | `directory(path: str = "") -> IDirectory` | Construye un `Directory`; la cadena vacía es la raíz del disco. Lanza `StoragePathException` ante intentos de escape. |
| `put` | `async put(path: str, contents: bytes \| str, visibility: str \| None = None) -> IFile` | `self.file(path).write(contents, visibility)`. |
| `exists` | `async exists(path: str) -> bool` | `self.file(path).exists()`. |
| `delete` | `async delete(path: str) -> bool` | `self.file(path).delete()`. |
| `copy` | `async copy(source: str, target: str) -> IFile` | `self.file(source).copyTo(target)`. |
| `move` | `async move(source: str, target: str) -> IFile` | `self.file(source).moveTo(target)`. |

### `File`

`orionis.storage.file.File` — implementa `orionis.storage.contracts.file.IFile`.

`__slots__ = ("_driver", "_path")`

```python
def __init__(self, driver: IStorageDriver, path: str) -> None
```

La ruta se normaliza con `normalizeFilePath()` al construir el objeto, así que una ruta
inválida falla de inmediato con `StoragePathException` y nunca llega al driver.

| Método | Firma | Notas |
| --- | --- | --- |
| `path` | `path() -> str` | Ruta canónica relativa a la raíz. |
| `read` | `async read() -> bytes` | Lanza `StorageFileNotFoundException`. |
| `readStream` | `readStream(chunk_size: int = 65536) -> AsyncIterator[bytes]` | No es corrutina: devuelve el iterador asíncrono del driver, se consume con `async for`. |
| `write` | `async write(contents: bytes \| str, visibility: str \| None = None) -> IFile` | Las cadenas se codifican en UTF-8. Devuelve `self` (encadenable). |
| `writeStream` | `async writeStream(stream: AsyncIterable[bytes], visibility: str \| None = None) -> IFile` | Devuelve `self`. |
| `open` | `open(mode: str = "rb") -> IStorageStream` | Llamada síncrona que devuelve un stream perezoso. Modos aceptados: `rb`, `wb`, `ab`, `rb+`, `wb+`, `ab+`; cualquier otro lanza `UnsupportedStorageOperationException`. |
| `delete` | `async delete() -> bool` | `True` si el archivo existía. |
| `exists` | `async exists() -> bool` | — |
| `copyTo` | `async copyTo(target: str) -> IFile` | Devuelve un `File` **nuevo** que apunta a la copia. |
| `moveTo` | `async moveTo(target: str) -> IFile` | Devuelve un `File` nuevo; el objeto actual sigue apuntando a la ruta antigua. |
| `rename` | `async rename(name: str) -> IFile` | Renombra dentro del mismo directorio. Lanza `StoragePathException` si `name` está vacío o contiene `/` o `\`. |
| `size` | `async size() -> int` | Bytes. |
| `mimeType` | `async mimeType() -> str \| None` | — |
| `lastModified` | `async lastModified() -> datetime` | Con zona horaria (UTC). |
| `url` | `async url() -> str` | Lanza `UnsupportedStorageOperationException` si el disco no expone URLs públicas. |
| `temporaryUrl` | `async temporaryUrl(expires_in: int = 3600) -> str` | URL firmada; no soportada por `local` ni `memory`. |
| `visibility` | `async visibility() -> str` | `'public'` o `'private'`. |
| `setVisibility` | `async setVisibility(visibility: str) -> IFile` | Devuelve `self`. |
| `download` | `async download(destination: str \| Path) -> Path` | Copia al sistema de archivos local; si `destination` es un directorio existente conserva el nombre original. Devuelve la ruta absoluta. |
| `hash` | `async hash(algorithm: str = "sha256") -> str` | Cualquier algoritmo aceptado por `hashlib.new`. |
| `info` | `async info() -> FileInfo` | Instantánea de metadatos. |

### `Directory`

`orionis.storage.directory.Directory` — implementa
`orionis.storage.contracts.directory.IDirectory`.

`__slots__ = ("_driver", "_path")`

```python
def __init__(self, driver: IStorageDriver, path: str = "") -> None
```

La ruta se normaliza con `normalizePath()`; la cadena vacía denota la raíz del disco.

| Método | Firma | Notas |
| --- | --- | --- |
| `path` | `path() -> str` | La cadena vacía significa la raíz del disco. |
| `create` | `async create() -> IDirectory` | Crea los padres que falten. Devuelve `self`. |
| `delete` | `async delete() -> bool` | Recursivo. `True` si existía. |
| `exists` | `async exists() -> bool` | — |
| `files` | `async files() -> list[IFile]` | Solo hijos directos, ordenados por ruta. |
| `allFiles` | `async allFiles() -> list[IFile]` | Todo el subárbol. |
| `directories` | `async directories() -> list[IDirectory]` | Solo hijos directos. |
| `allDirectories` | `async allDirectories() -> list[IDirectory]` | Todo el subárbol. |

Los métodos de listado devuelven objetos `File` / `Directory`, nunca cadenas: el driver
devuelve rutas y `Directory` las envuelve.

### `UploadedFile`

`orionis.storage.uploaded_file.UploadedFile` — implementa
`orionis.storage.contracts.uploaded_file.IUploadedFile`.

`__slots__ = ("_hash_name", "_manager", "_source")`

```python
def __init__(self, source: IHttpUploadedFile, manager: IStorageManager) -> None
```

| Método | Firma | Notas |
| --- | --- | --- |
| `originalName` | `originalName() -> str` | `source.filename` (ya saneado por la capa HTTP). |
| `extension` | `extension() -> str` | En minúsculas y con punto; cadena vacía si no hay extensión. |
| `size` | `size() -> int` | Bytes del payload. |
| `mimeType` | `mimeType() -> str \| None` | Tipo MIME declarado por el cliente. |
| `hashName` | `hashName() -> str` | `secrets.token_hex(20)` más la extensión original. Se genera una vez y se cachea por instancia. |
| `read` | `async read() -> bytes` | Lee todo el payload en un hilo de trabajo. |
| `store` | `async store(directory: str = "", disk: str \| None = None, visibility: str \| None = None) -> IFile` | Persiste con el nombre hash generado. |
| `storeAs` | `async storeAs(directory: str, name: str, disk: str \| None = None, visibility: str \| None = None) -> IFile` | Nombre explícito. Lanza `StoragePathException` si `name` está vacío o contiene separador. |
| `move` | `async move(directory: str, name: str \| None = None, disk: str \| None = None) -> IFile` | Persiste y después cierra el búfer de la carga. |
| `copy` | `async copy(directory: str, name: str \| None = None, disk: str \| None = None) -> IFile` | Persiste y deja el búfer utilizable. |

La persistencia siempre pasa por `manager.disk(disk).file(target).writeStream(...)`, y el
payload se transmite trozo a trozo (el iterador bloqueante se avanza con
`asyncio.to_thread`), así que una carga volcada a un archivo temporal nunca se carga
entera en memoria.

### `AsyncStream`

`orionis.storage.stream.AsyncStream` — implementa
`orionis.storage.contracts.stream.IStorageStream`.

`__slots__ = ("_handle", "_on_close", "_opener")`

```python
def __init__(
    self,
    opener: Callable[[], BinaryIO],
    on_close: Callable[[BinaryIO], None] | None = None,
) -> None
```

El handle lo crea `opener` en el primer uso (o en `__aenter__`) y toda operación
bloqueante corre en un hilo de trabajo.

| Método | Firma | Notas |
| --- | --- | --- |
| `read` | `async read(size: int = -1) -> bytes` | `-1` lee hasta EOF. |
| `write` | `async write(data: bytes) -> int` | Bytes escritos. |
| `seek` | `async seek(offset: int, whence: int = 0) -> int` | Nueva posición absoluta. |
| `close` | `async close() -> None` | Invoca `on_close` con el handle abierto y luego lo cierra. Desliga el handle primero, así que un segundo cierre no hace nada. |
| `__aenter__` | `async __aenter__() -> IStorageStream` | Abre el handle y devuelve el stream. |
| `__aexit__` | `async __aexit__(exc_type, exc, traceback) -> None` | Siempre cierra. |

El callback `on_close` es lo que permite al driver de memoria volcar el búfer de vuelta a
su almacén cuando se cierra un stream de escritura.

### `IStorageDriver`

`orionis.storage.contracts.driver.IStorageDriver` — ABC con 24 métodos abstractos. El
código de aplicación nunca toca un driver directamente.

| Grupo | Métodos |
| --- | --- |
| Contenido | `read`, `readStream`, `write`, `writeStream`, `delete`, `exists`, `open` |
| Reubicación | `copy`, `move`, `download` |
| Metadatos | `size`, `mimeType`, `lastModified`, `visibility`, `setVisibility`, `hash`, `info` |
| Directorios | `createDirectory`, `deleteDirectory`, `directoryExists`, `files`, `directories` |
| URLs | `url`, `temporaryUrl` |

`readStream` y `open` son los únicos miembros que no son `async def`: `readStream` se
implementa como generador asíncrono (se llama y se itera con `async for`) y `open`
devuelve el objeto stream de forma síncrona.

`files()` y `directories()` reciben `recursive` como argumento solo por palabra clave
(`files(path="", *, recursive=False)`).

Matriz de capacidades de los cinco drivers incorporados:

| Capacidad | `local` | `memory` | `s3` | `azure` | `gcs` |
| --- | --- | --- | --- | --- | --- |
| `url()` | Requiere `url` configurada; si no, `UnsupportedStorageOperationException` | Igual que local | `url` configurada, `endpoint` propio o dirección virtual-host | `url` configurada o el endpoint de blobs de Azure | `url` configurada o `storage.googleapis.com` |
| `temporaryUrl()` | Siempre lanza `UnsupportedStorageOperationException` | Siempre lanza `UnsupportedStorageOperationException` | `generate_presigned_url` | Token SAS; requiere la clave de cuenta | URL firmada V4; requiere una clave de firma |
| `visibility()` | Derivada de los bits de permiso (`st_mode & 0o044`) | Valor guardado con la entrada | Concesiones ACL del objeto para `AllUsers` | Política de acceso del contenedor | Entrada `allUsers` en el ACL del blob |
| `setVisibility()` | `chmod` `0o644` / `0o600` | Actualiza el valor guardado | `put_object_acl` | Siempre lanza `UnsupportedStorageOperationException` | ACL predefinido |
| Directorios | Directorios reales del sistema de archivos | Conjunto explícito más prefijos implícitos de las claves | Marcadores `path/` de cero bytes más prefijos implícitos | Igual que S3 | Igual que S3 |

### `LocalStorageDriver`

`orionis.storage.drivers.local.LocalStorageDriver`

`__slots__ = ("_base_url", "_root")`

```python
def __init__(self, root: Path, base_url: str | None = None) -> None
```

- `root` se resuelve con `Path.resolve()` y se crea con `mkdir(parents=True, exist_ok=True)`
  en el constructor.
- A `base_url` se le quita la `/` final; cuando es `None`, `url()` lanza excepción y
  `FileInfo.url` queda en `None`.
- **Escrituras atómicas:** `write()` y `writeStream()` escriben en un archivo hermano
  `<nombre>.<aleatorio>.tmp` y luego hacen `Path.replace()` sobre el destino. El infijo
  aleatorio da a cada llamada su propio archivo de preparación, así que dos escrituras
  que compiten por la misma ruta nunca mezclan contenidos; una escritura fallida elimina
  solo su propio temporal y deja el destino intacto.
- Por eso mismo, `files()` omite las entradas cuyo nombre termina en `.tmp`.
- La visibilidad se traduce a bits POSIX: archivos `0o644` (pública) / `0o600` (privada),
  directorios `0o755` / `0o700`. Un nivel desconocido lanza
  `UnsupportedStorageOperationException`.
- `info()` lee el archivo una sola vez y calcula MD5 (`etag`) y SHA-256 (`checksum`) en la
  misma pasada; `createdAt` usa `st_birthtime` cuando la plataforma lo ofrece y, si no, `None`.
- `mimeType()` se deduce de la extensión con `mimetypes.guess_type()` y no toca el disco.
- Toda llamada bloqueante pasa por `asyncio.to_thread`.

### `MemoryStorageDriver`

`orionis.storage.drivers.memory.MemoryStorageDriver`

`__slots__ = ("_base_url", "_directories", "_files")`

```python
def __init__(self, base_url: str | None = None) -> None
```

Mantiene todos los objetos en memoria del proceso: `_files` mapea rutas a `_MemoryEntry`
(`content`, `visibility`, `created_at`, `modified_at`) y `_directories` guarda los
directorios creados explícitamente. Pensado para tests y cargas efímeras.

- Una entrada nueva queda con `Visibility.PRIVATE` cuando `write()` recibe `visibility=None`;
  al sobrescribir se conserva la visibilidad previa y también `created_at`.
- `open()` trabaja sobre `io.BytesIO`: los modos de lectura exigen que el archivo exista,
  los de anexado se posicionan al final y todo modo de escritura vuelca al almacén al cerrar.
- `download()` sí toca el sistema de archivos: escribe el contenido en memoria en el destino
  local.
- Concurrencia: el almacén es un diccionario mutado sin locks. Toda operación termina sin
  esperar a mitad de camino, así que varias tareas del mismo bucle de eventos nunca ven una
  mutación parcial; no hay garantía cuando la misma ruta se muta desde varios hilos a la
  vez, que es lo que hacen los streams abiertos con `open()` al volcar su búfer en un hilo
  de trabajo.

### `S3StorageDriver`

`orionis.storage.drivers.s3.S3StorageDriver`

`__slots__ = ("_base_url", "_bucket", "_client", "_client_error", "_endpoint", "_key", "_region", "_secret", "_use_path_style")`

```python
def __init__(self, config: object) -> None
```

Lee `bucket`, `region`, `key`, `secret`, `url`, `endpoint` y `use_path_style_endpoint` de
la entidad de configuración. El constructor no importa nada ni hace llamadas de red.

- El cliente de `boto3` se construye en el primer uso: las credenciales explícitas ganan y,
  si faltan, boto3 recurre a su propia cadena de credenciales. `use_path_style_endpoint=True`
  cambia el estilo de direccionamiento a `path`.
- Los códigos de error `404`, `NoSuchKey` y `NotFound` se traducen a
  `StorageFileNotFoundException`; cualquier otro error del SDK se propaga tal cual.
- La visibilidad se traduce a ACLs prefabricados `public-read` / `private`; `visibility()`
  inspecciona las concesiones del objeto buscando permiso de lectura para el grupo de
  usuarios anónimos.
- `deleteDirectory()` borra por lotes de hasta 1000 claves.
- Los streams se almacenan en un archivo temporal con búfer que se vuelca a disco a partir
  de 8 MiB.

### `AzureStorageDriver`

`orionis.storage.drivers.azure.AzureStorageDriver`

`__slots__ = ("_account_key", "_account_name", "_base_url", "_connection_string", "_container", "_container_name", "_http_error", "_not_found", "_sdk")`

```python
def __init__(self, config: object) -> None
```

Lee `connection_string`, `account_name`, `account_key`, `container` y `url`. Cuando se
entrega una cadena de conexión, `AccountName` y `AccountKey` se extraen de ella para poder
producir URLs y tokens SAS.

- Azure no tiene visibilidad por blob: `visibility()` refleja la política de acceso del
  contenedor y `setVisibility()` **siempre** lanza `UnsupportedStorageOperationException`.
- `temporaryUrl()` genera una URL SAS de solo lectura y necesita la clave de cuenta; sin
  ella, la llamada lanza `UnsupportedStorageOperationException`.
- `info()` rellena `checksum` con el `Content-MD5` que Azure guarda (en hexadecimal) cuando
  está disponible, y `etag` con el ETag del blob sin comillas.
- `directoryExists("")` devuelve `True` (la raíz siempre existe).

### `GoogleStorageDriver`

`orionis.storage.drivers.gcs.GoogleStorageDriver`

`__slots__ = ("_base_url", "_bucket", "_bucket_name", "_cloud_error", "_key_file", "_not_found", "_project")`

```python
def __init__(self, config: object) -> None
```

Lee `project_id`, `key_file`, `bucket` y `url`. La autenticación usa el archivo de clave de
la cuenta de servicio cuando está configurado y, si no, las Application Default Credentials.

- `temporaryUrl()` construye una URL firmada V4; firmar requiere credenciales con clave
  privada (un archivo de clave), que las ADC simples no aportan.
- `visibility()` devuelve `'private'` cuando no se pueden inspeccionar los ACL — por
  ejemplo, con acceso uniforme a nivel de bucket.
- La visibilidad se traduce a ACLs predefinidos de GCS; un nivel desconocido lanza
  `UnsupportedStorageOperationException`.

### Funciones auxiliares de los drivers

`orionis.storage.drivers.functions` — funciones a nivel de módulo compartidas por los
drivers de nube.

| Función | Firma | Descripción |
| --- | --- | --- |
| `importDriverDependency` | `importDriverDependency(module: str, package: str, extra: str) -> ModuleType` | Importa un módulo SDK opcional y convierte `ImportError` en `MissingStorageDependencyException` con el comando de instalación. |
| `assertBinaryMode` | `assertBinaryMode(mode: str) -> None` | Valida un modo de stream contra `rb`, `wb`, `ab`, `rb+`, `wb+`, `ab+`. |
| `resolveDownloadTarget` | `resolveDownloadTarget(normalized: str, destination: str \| Path) -> Path` | Resuelve el destino local de una descarga, conservando el nombre original si el destino es un directorio existente y creando los padres que falten. |
| `filterFiles` | `filterFiles(keys: Iterable[str], base: str, *, recursive: bool) -> list[str]` | Selecciona las claves que son archivos bajo `base`; las claves terminadas en `/` son marcadores de directorio y siempre se excluyen. Devuelve una lista ordenada. |
| `deriveDirectories` | `deriveDirectories(keys: Iterable[str], base: str, *, recursive: bool) -> list[str]` | Deduce rutas de directorio a partir de claves de objeto (los object stores no tienen directorios físicos). Devuelve una lista ordenada. |

### `FileInfo`

`orionis.storage.entities.file_info.FileInfo` —
`@dataclass(frozen=True, kw_only=True, slots=True)`. Lo devuelve `await file.info()`.

| Campo | Tipo | Valor por defecto | Descripción |
| --- | --- | --- | --- |
| `path` | `str` | — | Ruta canónica relativa a la raíz. |
| `size` | `int` | — | Tamaño en bytes. |
| `lastModified` | `datetime` | — | Marca de modificación con zona horaria. |
| `visibility` | `str` | — | `'public'` o `'private'`. |
| `mimeType` | `str \| None` | `None` | Tipo MIME deducido. |
| `createdAt` | `datetime \| None` | `None` | Marca de creación cuando el driver puede aportarla. |
| `etag` | `str \| None` | `None` | Entity tag (digest MD5 hexadecimal en los drivers incorporados). |
| `checksum` | `str \| None` | `None` | Digest SHA-256 hexadecimal cuando está disponible. |
| `url` | `str \| None` | `None` | URL pública cuando el disco expone una. |

Los nombres de campo están en camelCase a propósito, para coincidir con la convención de
nombres de la API pública del framework.

### `Visibility`

`orionis.storage.enums.visibility.Visibility` — `StrEnum` con `PUBLIC = "public"` y
`PRIVATE = "private"`. Como los miembros heredan de `str`, se pueden pasar en cualquier
lugar donde se acepte una cadena de visibilidad.

### Normalización de rutas

`orionis.storage.paths` — dos funciones a nivel de módulo aplicadas en cada borde.

```python
def normalizePath(path: str) -> str
def normalizeFilePath(path: str) -> str
```

`normalizePath()` convierte `\` en `/`, descarta segmentos vacíos y `.`, resuelve `..` de
forma lógica (sin tocar el sistema de archivos) y devuelve una ruta sin barra inicial ni
final. La cadena vacía representa la raíz del disco. Lanza `StoragePathException` cuando la
ruta contiene un byte nulo, cuando un segmento contiene `:` (bloqueando letras de unidad y
separadores de flujo) o cuando un `..` escapa de la raíz.

`normalizeFilePath()` aplica las mismas reglas y además rechaza el resultado vacío, porque
la raíz del disco nunca puede tratarse como un archivo.

### Excepciones

`orionis.storage.exceptions` — todas heredan de `StorageException`, que hereda de
`Exception`.

| Excepción | Se lanza cuando |
| --- | --- |
| `StorageException` | Clase base del módulo. |
| `DiskNotFoundException` | El disco no está declarado en la configuración `filesystems`. |
| `DriverNotSupportedException` | El disco referencia un driver sin implementación. |
| `MissingStorageDependencyException` | Un driver necesita un paquete opcional que no está instalado. |
| `StoragePathException` | La ruta está mal formada o escapa de la raíz del disco. |
| `StorageFileNotFoundException` | El archivo no existe en el disco de destino. |
| `UnsupportedStorageOperationException` | El driver no puede realizar la operación pedida (URL temporal, visibilidad, modo de stream, algoritmo de hash). |

### `StorageProvider` y la facade `Storage`

`orionis.storage.provider.StorageProvider` extiende `ServiceProvider` y
`DeferrableProvider`, y está listado en `orionis/foundation/core_providers.py`.

| Miembro | Comportamiento |
| --- | --- |
| `provides()` | `[IStorageManager]` |
| `register()` | `self.app.singleton(IStorageManager, StorageManager)` |
| `boot()` | `await Storage.pin()` (asíncrono) |

`orionis.support.facades.storage.Storage` solo sobrescribe `getFacadeAccessor()`, que
devuelve `IStorageManager`. El archivo hermano `storage.pyi` existe únicamente para el
autocompletado del editor y nunca se ejecuta.

Como el provider es **diferible**, `register` y `boot` solo corren la primera vez que se
resuelve `IStorageManager` a través del contenedor. Eso tiene una consecuencia concreta
para la facade:

- Antes de esa primera resolución, `Storage.disk("public")` devuelve un dispatcher diferido
  que hay que esperar: `disk = await Storage.disk("public")`. Esa llamada resuelve el
  servicio, arranca el provider y fija (pin) la facade.
- Una vez fijada, el acceso a atributos es directo: `Storage.disk("public")` devuelve el
  `Disk` de forma síncrona, y esperarlo con `await` fallaría porque un `Disk` no es
  awaitable.

Inyectar `IStorageManager` (por constructor o como parámetro de un método de controlador)
evita del todo esa distinción: el contenedor resuelve el provider diferido y entrega el
manager real.

### Claves de configuración

`StorageManager` lee `app.config("filesystems")`, respaldado por las entidades de
`orionis.foundation.config.filesystems` y, en la aplicación, por `config/filesystems.py`.

| Clave | Tipo | Descripción |
| --- | --- | --- |
| `default` | `DiskName \| str` | Disco que usan `Storage.default()` / `disk(None)`. Se valida contra `DiskName` (`local`, `public`, `s3`, `azure`, `gcs`). |
| `disks.local` | `Local` | `driver` (por defecto `"local"`), `path` (por defecto `"storage/app/private"`). |
| `disks.public` | `Public` | `driver` (por defecto `"local"`), `path`, `url`. |
| `disks.s3` | `S3` | `driver` (por defecto `"aws"`), `key`, `secret`, `region`, `bucket`, `url`, `endpoint`, `use_path_style_endpoint`. |
| `disks.azure` | `Azure` | `driver` (por defecto `"azure"`), `connection_string`, `account_name`, `account_key`, `container`, `url`. |
| `disks.gcs` | `GCS` | `driver` (por defecto `"gcs"`), `project_id`, `key_file`, `bucket`, `url`. |

`Disks` es un dataclass congelado con exactamente esos cinco campos, así que los **nombres**
de disco son fijos; lo configurable por disco es el `driver` al que apunta, que además es la
clave que usa `StorageManager.extend()`.

## Ejemplos de uso

### Resolver un disco con la facade

```python
from orionis.storage.contracts.file import IFile
from orionis.support.facades.storage import Storage


async def store_report(payload: bytes) -> IFile:
    """Persistir un reporte en el disco público y devolver el archivo."""
    # Primer acceso a la facade: esperarlo arranca el provider diferido y fija
    # la facade, de modo que los accesos posteriores se usan directamente.
    disk = await Storage.disk("public")

    report = await disk.put("reports/2026-q1.pdf", payload, "public")
    print(report.path(), await report.size(), await report.url())

    for entry in await disk.directory("reports").files():
        print(entry.path())

    return report
```

### Manejo de errores

```python
import asyncio

from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.exceptions import (
    StorageFileNotFoundException,
    StoragePathException,
    UnsupportedStorageOperationException,
)


async def main() -> None:
    disk = Disk(name="memory", driver=MemoryStorageDriver())

    try:
        await disk.file("missing.txt").read()
    except StorageFileNotFoundException as exc:
        print("no encontrado:", exc)

    try:
        disk.file("../../etc/passwd")
    except StoragePathException as exc:
        print("ruta rechazada:", exc)

    await disk.put("notes.txt", "hello")
    try:
        await disk.file("notes.txt").temporaryUrl(60)
    except UnsupportedStorageOperationException as exc:
        print("no soportado:", exc)


asyncio.run(main())
```

### Streaming de archivos grandes

```python
import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from orionis.storage.disk import Disk
from orionis.storage.drivers.local import LocalStorageDriver


async def rows() -> AsyncIterator[bytes]:
    """Producir el contenido de la exportación trozo a trozo."""
    for index in range(3):
        yield f"row-{index}\n".encode()


async def main() -> None:
    driver = LocalStorageDriver(root=Path("storage/app/private"))
    disk = Disk(name="local", driver=driver)

    # Nada se materializa por completo en memoria, ni al escribir ni al leer.
    export = await disk.file("exports/report.csv").writeStream(rows())

    async for chunk in export.readStream(chunk_size=8):
        print(chunk)

    async with export.open("rb") as stream:
        print(await stream.read(5))

    await export.delete()


asyncio.run(main())
```

### Guardar un archivo subido por HTTP

```python
from orionis.http import HttpResponse, response
from orionis.http.base import BaseController
from orionis.http.request import Request
from orionis.storage.contracts.manager import IStorageManager


class AvatarController(BaseController):

    async def store(
        self,
        request: Request,
        storage: IStorageManager,
    ) -> HttpResponse:
        """
        Persistir el avatar subido en el disco público.

        Parameters
        ----------
        request : Request
            Petición HTTP entrante que transporta el formulario multipart.
        storage : IStorageManager
            Gestor de almacenamiento inyectado por el contenedor.

        Returns
        -------
        HttpResponse
            Payload JSON con la ruta almacenada y su URL pública.
        """
        form = await request.form()
        upload = storage.uploaded(form.files["avatar"][0])

        # store() usa un nombre hash aleatorio; storeAs() recibe uno explícito.
        stored = await upload.store("avatars", disk="public", visibility="public")

        return response.json({
            "path": stored.path(),
            "url": await stored.url(),
        })
```

### Ejecución autónoma con el driver en memoria

```python
import asyncio

from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver


async def main() -> None:
    disk = Disk(name="fake", driver=MemoryStorageDriver(base_url="https://cdn.test"))

    await disk.put("invoices/2026/001.txt", "total: 120", "public")
    await disk.put("invoices/2026/002.txt", "total: 340")

    invoices = disk.directory("invoices")
    print([entry.path() for entry in await invoices.allFiles()])
    print([entry.path() for entry in await invoices.directories()])

    first = disk.file("invoices/2026/001.txt")
    print(await first.visibility())
    print(await first.url())
    print(await first.hash("md5"))
    print(await first.info())


asyncio.run(main())
```

### Registrar un driver personalizado

```python
from orionis.storage.contracts.driver import IStorageDriver
from orionis.storage.contracts.manager import IStorageManager
from orionis.storage.drivers.memory import MemoryStorageDriver


def register_fake_driver(manager: IStorageManager) -> None:
    """Vincular el nombre de driver 'fake' con una implementación en memoria."""

    def factory(config: object) -> IStorageDriver:
        # config es la entidad del disco declarada en config/filesystems.py.
        return MemoryStorageDriver(base_url=getattr(config, "url", None))

    # Cualquier disco cuyo campo `driver` sea "fake" resuelve ahora con esta
    # fábrica, que además tiene prioridad sobre los drivers incorporados.
    manager.extend("fake", factory)
```

## Consideraciones de rendimiento y concurrencia

- **E/S sin bloqueo:** toda operación bloqueante (acceso al sistema de archivos, llamadas
  al SDK, búferes de carga volcados a disco) pasa por `asyncio.to_thread`, así que el bucle
  de eventos sigue respondiendo. No interviene ningún cliente nativo verdaderamente
  asíncrono; el modelo es "hilos de trabajo detrás de una API async".
- **Memoria acotada:** `readStream`, `writeStream`, `hash` e `info` procesan trozos de
  64 KiB; los drivers de nube vuelcan los streams entrantes a un archivo temporal que pasa a
  disco a partir de 8 MiB. `read()` es la única operación que materializa el archivo entero.
- **Caché de discos:** `StorageManager` construye cada `Disk` una vez y lo cachea en
  `_disks`; `extend()` limpia la caché. Los clientes de nube también se construyen una vez
  por instancia de driver y se reutilizan.
- **Escrituras locales atómicas:** la secuencia de archivo temporal más `Path.replace()`
  implica que un lector nunca ve un archivo a medio escribir, y una transferencia fallida no
  deja destino parcial. Cada llamada prepara su contenido en un temporal con nombre
  aleatorio propio, así que varios escritores sobre la misma ruta publican un contenido
  completo o nada.
- **`__slots__` en todas partes** en las clases concretas y `__slots__` vacío en los
  contratos, lo que elimina el diccionario de atributos de las muchas instancias efímeras
  de `File` / `Directory` que crea un listado.
- **Objetos baratos:** `Disk.file()`, `Disk.directory()` y `File.open()` no hacen E/S; solo
  construyen objetos. El coste llega al esperarlos o al entrar en ellos.
- **Estado independiente:** `File` y `Directory` solo guardan una referencia al driver y una
  cadena, así que se pueden crear y usar libremente desde varias tareas. `AsyncStream`, en
  cambio, envuelve un único handle con posición mutable, por lo que un stream debe usarse
  desde una sola tarea a la vez.

## Notas de compatibilidad

- **Python `>= 3.14`** (`requires-python` en `pyproject.toml`). El módulo usa `Path.walk()`
  (3.12+), `datetime.UTC` (3.11+), `StrEnum` (3.11+),
  `hashlib.new(..., usedforsecurity=False)` (3.9+) y la sintaxis de tipos `X | Y`.
- **Windows:** la visibilidad se apoya en bits de permiso POSIX. Windows no implementa el
  modelo POSIX completo, así que `chmod` degrada de forma benigna y `visibility()` puede
  informar `'public'` para archivos creados con el modo por defecto.
- **`createdAt`** depende de `st_birthtime`, que no todas las plataformas/sistemas de
  archivos exponen; queda en `None` cuando no está disponible.
- **`Path.replace()`** no puede cruzar dispositivos; el driver local recurre a
  `shutil.move()` para movimientos entre dispositivos. En Windows además puede lanzar
  `PermissionError` si otro escritor está reemplazando ese mismo destino en ese preciso
  instante, una restricción del sistema operativo que POSIX no tiene.
- **SDKs opcionales:** los drivers de nube se pueden instanciar sin su SDK instalado; el
  fallo aflora en la primera operación como `MissingStorageDependencyException`.
- **El módulo `storage` nunca importa la capa HTTP en tiempo de ejecución**: el contrato del
  payload multipart se importa solo bajo `TYPE_CHECKING` y se consume por duck-typing
  (`filename`, `extension`, `size`, `content_type`, `read()`, `chunks()`, `close()`).
