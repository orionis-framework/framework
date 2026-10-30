# Storage

Storage permite guardar contenido y trabajar con archivos mediante el mismo contrato async en discos locales, efímeros o cloud.

## Recorrido

1. [Archivos y directorios](files-and-directories.md): lectura, escritura, rutas, metadata y borrado.
2. [Streams y uploads](streaming-and-uploads.md): memoria, handles, publicación y cargas HTTP.
3. [Discos y drivers](disks-and-drivers.md): configuración local/cloud, visibilidad y extensiones.

Los ejemplos memory y temporales no requieren credenciales. Los ejemplos de facade requieren la aplicación y `StorageProvider`; las operaciones cloud necesitan el SDK y sus permisos.

## Ejecución acotada y rendimiento

`readStream` local, S3 y GCS conserva el tamaño lógico solicitado: lee primero un chunk y después agrupa lecturas nativas dentro de un presupuesto de 1 MiB, como mínimo un chunk solicitado. Azure agrupa como máximo 16 chunks del SDK y se detiene al alcanzar 1 MiB; un chunk del SDK puede superar ese presupuesto. No hay productor leyendo mientras el consumidor está pausado. La cancelación espera la lectura nativa en curso antes de cerrar su handle.

`async with file.open("rb") as stream: ...` admite también `async for chunk in stream.chunks(65536, buffer_size=1048576): ...`. No mezcles esa iteración con seek/write/otras lecturas. El contexto asíncrono envolvente se encarga del cierre. Para salida anticipada de streams del driver usa `contextlib.aclosing`; configura timeouts de red finitos en los SDK porque cancelar Python no detiene forzosamente el I/O nativo.
