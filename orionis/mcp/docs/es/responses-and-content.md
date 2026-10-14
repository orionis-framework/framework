# Contenido, serialización y metadata

`McpResponse` es un valor inmutable independiente del transporte. Sus builders crean texto, imágenes, audio, recursos embebidos, enlaces, datos estructurados, errores de herramienta o actualizaciones de progreso. Los métodos `withMeta`, `withContentMeta`, `withAnnotations`, `asUser` y `asAssistant` devuelven copias, no modifican una respuesta compartida.

## Devolver datos estructurados

```python
from orionis.mcp import ContentAnnotations, McpResponse

result = (
    McpResponse.structured({"status": "ok", "count": 2})
    .withMeta({"example.org/trace": "docs"})
    .withContentMeta({"example.org/source": "catalog"})
    .withAnnotations(ContentAnnotations(audience=("assistant",), priority=0.8))
)
assert result.structured_content == {"status": "ok", "count": 2}
assert result.content[0].meta["example.org/source"] == "catalog"
```

`structured(value)` mantiene `structuredContent` JSON y contenido textual correspondiente. Normaliza `Schema`, `msgspec.Struct`, dataclasses, enums, fechas, UUID y Decimal mediante msgspec respetando aliases, tags y defaults omitidos. No muta el valor original. Valores no finitos, claves JSON no string, objetos no soportados y buffers binarios anidados no son JSON válido; usa representación binaria explícita para esos datos.

## Recursos JSON o MessagePack

```python
import base64
import msgspec
from orionis.mcp import McpResponse

value = {"ready": True, "count": 2}
json_result = McpResponse.resource("demo://status", value, "application/json")
packed = McpResponse.resource("demo://status", value, "application/msgpack")
assert msgspec.json.decode(json_result.content[0].resource.text) == value
assert msgspec.msgpack.decode(base64.b64decode(packed.content[0].resource.blob)) == value
```

JSON y subtipos `+json` se entregan como texto UTF-8. MessagePack (`application/msgpack`, `application/x-msgpack`, `application/vnd.msgpack` y subtipos `+msgpack`) se entrega en blob Base64. El MIME describe contenido: los envelopes HTTP/STDIO continúan siendo JSON-RPC JSON. Para otros MIME proporciona texto o bytes ya codificados; el builder rechaza datos estructurados arbitrarios.

Sin MIME, datos estructurados usan JSON. Texto JSON previamente codificado y buffers binarios apropiados se conservan sin doble codificación; un string con MIME MessagePack es dato a codificar como MessagePack. La selección ignora mayúsculas/parámetros sin alterar el MIME declarado.

Al leer un `Resource`, su `mime_type` se aplica a resultados `structured()` y `text()`. Un recurso MessagePack convierte el valor original en binario, no en bytes de un string JSON serializado. Los recursos explícitamente embebidos conservan contenido y MIME propios.

## Imágenes, enlaces y fallos

`image(bytes, mime_type)` y `audio(bytes, mime_type)` representan binarios. `resourceLink(uri, name, title=..., description=..., mime_type=...)` publica referencia sin leer automáticamente su destino. `error(message)` señala fallo esperado de herramienta; no devuelvas secretos. Errores JSON-RPC, parámetros inválidos y acceso denegado pertenecen al dispatcher y sus excepciones.

## Hints y metadata segura

`CacheHint(ttl_ms=..., scope="private"|"public")` informa caché del cliente y no almacena resultados en servidor. TTL debe ser entero no negativo. La política pública debe ser coherente con identidad/visibilidad; el dispatcher conserva límites de privacidad. `Icon` acepta HTTPS o data URI y el servidor no descarga el icono. `ContentAnnotations.priority` se limita a 0–1.

La metadata se valida y queda acotada por `MCP_MAX_METADATA_SIZE`. No puedes sobrescribir claves reservadas del protocolo mediante metadata de aplicación o schema hooks. Usa claves propias con namespace y evita incluir contexto sensible por comodidad de diagnóstico.

Evidencia: [builders](../../responses.py), [normalización](../../normalization.py), [metadata](../../protocol/metadata.py), [validación](../../protocol/validation.py). Pruebas: [respuestas](../../../../tests/mcp/test_responses.py), [codecs](../../../../tests/mcp/protocol/test_codecs.py), [auditoría de límites](../../../../tests/mcp/test_audit_edges.py). Consulta [transportes](transports-and-configuration.md).
