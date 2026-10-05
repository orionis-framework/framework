# Orionis MCP

MCP reutiliza el contenedor, las respuestas HTTP, el cierre de streams y el contexto
de autenticacion de Orionis. `McpProvider` registra `IMcpManager`, `McpConfig` validada
y un `IMcpEventBus` acotado; boot fija las facades y carga los archivos de rutas `ai`.

## Registro

Declarar subclases de `Server` con herramientas, recursos y prompts explicitos, y
registrarlas con `Mcp.web(path, server)` o `Mcp.local(name, server)` en `routes/ai.py`.
HTTP crea rutas POST nativas con perfil API. El transporte local resuelve handles
registrados: no importa nombres de modulos enviados por clientes. El manager compila
cada servidor una vez y no cachea identidades ni instancias de handlers de peticiones.

`Tool[InputType, OutputType]` admite tambien atributos `input` y `output` explicitos.
`McpInvoker` precompila el origen confiable de cada dependencia. Las claves del
payload no se convierten en kwargs arbitrarios de constructores o handlers. El
contenedor construye las primitivas para disponibilidad, autorizacion y ejecucion.

## Runtime Y Limites

HTTP utiliza `Response` y `EventStreamResponse`. STDIO mantiene tareas independientes
acotadas y serializa la salida; shutdown espera el cleanup propio. `OwnedStream`
implementa `AsyncClosable`, incluido el cierre antes de la primera lectura. El bus
local combina cambios duplicados y limita suscriptores y buffers. No es un broker
distribuido entre workers.

Todas las opciones de `config/mcp.py` leen factories de entorno. Bytes de peticion
y concurrencia pueden compartir defaults HTTP; los origenes pueden compartir las
entradas CORS explicitas, nunca sus comodines. Los overrides del protocolo ganan.

El dispatcher prepara una vez las fuentes de listados, la identidad del servidor y
las tablas de tipos. El validador es propietario de la copia mutable del payload.
Eliminar la segunda copia reduce trabajo en mapas anidados; para listas solo evita
el diccionario raiz adicional. Los helpers sincronos de entrada/salida siguen
ejecutando reglas sincronas: no asociarles reglas de E/S bloqueante. La inyeccion
de esquemas en controladores HTTP usa el validador asincrono independiente.

## Matching De URI

La expansion usa la biblioteca RFC 6570 existente. La inversa automatica requiere
variables simples separadas por caracteres excluidos de las capturas (`/`, `?`,
`#`, `&`, `;`). Capturas adyacentes o separadores textuales ambiguos requieren
`Resource.match(uri)` como metodo estatico o de clase. El resultado debe expandirse
a la URI pedida; se rechazan variables extras y valores repetidos inconsistentes.

Las plantillas ambiguas antes aceptadas se rechazan al compilar. Una inversa
explicita permite conservarlas. Su complejidad sigue siendo responsabilidad de la
aplicacion. La validacion de nombres usa ASCII y grupos posesivos.

## Politica De Inicializacion

Los constructores capturan configuracion, metadatos y estado vacio acotado. No abren
STDIO, no crean tareas de peticion ni avanzan productores. Planes de schemas,
handlers y tablas de despacho se preparan al compilar el servidor. Instancias,
identidad, payload y cleanup pertenecen a cada invocacion. La
[auditoria global](../../docs/performance-audit.es.md) contiene pruebas, medidas y
limites de verificacion.

## Pruebas

Usar `TestCase` de `orionis.test` y crear un cliente mediante
`client = await self.mcp(ServerType)` dentro de un test async o `asyncSetUp`.
El helper reutiliza la aplicacion del runner; `app=` selecciona un contenedor
aislado y `config=` ajusta los limites. Peticiones y streams conservan codecs,
dispatcher y scopes nativos.

Ejecutar estas pruebas con `reactor test`. El cliente, las aserciones y su API
pertenecen al [paquete de pruebas](../../test/docs/README.es.md#clientes-mcp).
