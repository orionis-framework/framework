# Storage

Storage permite guardar contenido y trabajar con archivos mediante el mismo contrato async en discos locales, efímeros o cloud.

## Recorrido

1. [Archivos y directorios](files-and-directories.md): lectura, escritura, rutas, metadata y borrado.
2. [Streams y uploads](streaming-and-uploads.md): memoria, handles, publicación y cargas HTTP.
3. [Discos y drivers](disks-and-drivers.md): configuración local/cloud, visibilidad y extensiones.

Los ejemplos memory y temporales no requieren credenciales. Los ejemplos de facade requieren la aplicación y `StorageProvider`; las operaciones cloud necesitan el SDK y sus permisos.
