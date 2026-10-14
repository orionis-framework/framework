# Formularios y archivos subidos

Usa `await request.form()` para conservar campos repetidos y archivos de un formulario. El resultado `FormData` puede proceder de URL encoded o multipart. `get(key)` elige el último valor; `getAll(key)` conserva todos. `fields` agrupa textos y `files` agrupa objetos `UploadedFile`. `multiItems()` conserva la secuencia completa de pares.

## Inspeccionar un adjunto sin conservar temporales

```python
from orionis.http import Request, response

async def inspect_attachment(request: Request):
    form = await request.form()
    try:
        uploads = form.files.get("attachment", [])
        if len(uploads) != 1:
            return response.json({"message": "One attachment is required"}, 422)
        upload = uploads[0]
        return response.json({
            "filename": upload.filename,
            "size": upload.size,
            "extension": upload.extension,
            "labels": form.getAll("label"),
        })
    finally:
        form.close()
```

El cliente debe enviar `multipart/form-data` con un boundary válido. El ejemplo no guarda datos y es adecuado para comprobar la integración del formulario. `FormData` también implementa context manager síncrono: `with await request.form() as form:`. No uses `async with`; `close()` es síncrono.

## Guardar de forma controlada

`UploadedFile.read()` devuelve bytes, `chunks(size)` itera bloques y `save(path)` copia al destino. Estos métodos son síncronos. No escribas un archivo grande en disco lento desde el event loop sin delegar el trabajo. `replace(data)` sustituye el contenido; `size` y `extension` son propiedades. La extensión incluye el punto y se normaliza a minúsculas.

El nombre recibido se sanea para quitar separadores, controles y prefijos de puntos. Eso no comprueba el contenido ni garantiza unicidad. Genera un nombre de almacenamiento propio, valida los bytes y MIME según tu dominio y utiliza una ruta autorizada. No conviertas directamente un nombre del cliente en una ruta pública. Para almacenamiento persistente, consulta [files](../../../storage/docs/es/README.md).

Los archivos empiezan en memoria y pasan a un archivo temporal cuando superan `HTTP_UPLOAD_MEMORY_THRESHOLD`. Conserva solo el resultado persistido; un `UploadedFile` cerrado ya no es una fuente válida para una tarea en segundo plano. Si debes procesar después, guarda primero y pasa un identificador de dominio o ruta controlada.

## Presupuestos multipart

`config/http.py` declara límites de archivos (`HTTP_MAX_FILES`), campos (`HTTP_MAX_FIELDS`), parte (`HTTP_MAX_PART_SIZE`), campo (`HTTP_MAX_FIELD_SIZE`), encabezados (`HTTP_MAX_PART_HEADER_SIZE`), umbral de archivo y memoria multipart total (`HTTP_MAX_MULTIPART_MEMORY_SIZE`). Se combinan con el límite total del cuerpo. Aumentar el total no elimina el límite de parte.

Las cargas incompletas, boundaries inválidos, demasiadas partes o tamaños excesivos generan errores de parseo/límite. El parser limpia archivos temporales al fallar; el handler sigue siendo responsable de no retener referencias ni dejar copias propias abandonadas. Dimensiona almacenamiento temporal y memoria por worker multiplicando por concurrencia.


Los valores iniciales de `HTTPBodyLimits` son:

| Límite | Valor |
|---|---:|
| Archivos / campos | 32 / 128 |
| Parte individual | 10 MiB |
| Campo de texto | 1 MiB |
| Encabezado de parte | 16 KiB |
| Umbral de archivo en memoria | 256 KiB |
| Memoria multipart retenida total | 8 MiB |

Los presupuestos de memoria no incluyen todos los objetos, copias temporales ni buffers del servidor. Permitir cero archivos o campos rechaza esa clase de parte; no significa ilimitado.

Evidencia: [FormData](../../payload/form_data.py), [UploadedFile](../../payload/uploaded_file.py), [parser](../../payload/stream_parser.py), [configuración](../../../../config/http.py). Pruebas: [uploads](../../../../tests/http/payload/test_uploaded_file.py), [parser incremental](../../../../tests/http/payload/test_stream_parser.py), [límites](../../../../tests/http/payload/test_body_limits.py). Vuelve a [entrada](requests-and-validation.md) o continúa con [respuestas](responses.md).
