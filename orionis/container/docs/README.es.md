# orionis.container

> Resuelve servicios y dependencias de callables, administra scopes y providers diferidos, y expone facades globales o locales al scope.

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Descripción funcional](#descripción-funcional)
- [Estructura del módulo](#estructura-del-módulo)
- [Referencia de API](#referencia-de-api)
- [Ejemplos de uso](#ejemplos-de-uso)
- [Características de diseño](#características-de-diseño)
- [Rendimiento y concurrencia](#rendimiento-y-concurrencia)
- [Notas de compatibilidad](#notas-de-compatibilidad)
- [Verificación y limitaciones](#verificación-y-limitaciones)

## Requisitos

El proyecto declara Python **>=3.14** en [pyproject.toml](../../../pyproject.toml).
Registro, construcción, invocación y scopes de un `Container` independiente no
requieren bootstrap de aplicación. No hay un extra de instalación del módulo.
Reflexión e inyección de schemas usan `msgspec`, dependencia core del framework.

La preparación adicional depende de la API utilizada:

| Operación | Preparación necesaria y evidencia |
| --- | --- |
| `Facade.resolve` / `pin` globales o despacho sin pin | Una `Application` cacheada u obtenida de forma diferida con `isBooted` verdadero y un accessor resoluble. Véase [facade.py](../facades/facade.py). `Application.create()` establece el flag tras el registro; `await Application.boot()` también completa boot de providers eager. El flag no implica que todos los servicios hayan completado boot. |
| `ScopedFacade` | Un `ScopeManager` actualmente activo que almacene un servicio no-None bajo la clave exacta del accessor. No se ejecuta boot de aplicación ni pin global. |
| Parámetro schema implícito | Un `Request` concreto resoluble cuyo `data()` suministre el payload; el contenedor espera `Schema.validateAsync`. Un valor explícito evita esa ruta. |
| Provider diferido | El registro de Application prepara los metadatos. Declare providers mediante la API real [Application.withProviders](../../foundation/application.py) y `DeferrableProvider.provides`; un Container independiente empieza con el registro vacío. |

Bases de datos, cachés y servicios de red externos son requisitos de los
servicios inyectados, no requisitos añadidos por este módulo. Este manual no
autoriza iniciarlos ni ejecutar el bootstrap del checkout para verificarlo.

## Descripción funcional

`orionis.container` asocia clases de contrato y alias string con instancias o
clases concretas, aplica lifetimes transient/singleton/scoped e inyecta
dependencias en construcción y ejecución de callables. También coordina
providers diferidos y ofrece proxies globales y locales al scope.

### Integraciones directas

La implementación que controla el comportamiento es [Container](../container.py).
[Application](../../foundation/application.py) lo hereda y prepara los metadatos
de providers. [InvocationPlan](../entities/invocation.py) obtiene parámetros
mediante [introspection](../../introspection/dependencies/reflection.py); los
schemas leen [Request](../../http/request.py) y usan el
[validador](../../schemas/validator.py) asíncrono. [Binding](../entities/binding.py)
hereda [BaseEntity](../../support/entities/base.py).

[KernelHTTP](../../http/kernel.py) precalienta planes de funciones y controllers
sin construir estos últimos. La [facade Session](../../support/facades/session.py)
real hereda `ScopedFacade`. Son límites de integración, no catálogos adicionales
de API de esos módulos.

### Límites de scope y ejecución

Las instancias de Container son singleton **por subclase**; el singleton de
aplicación y los de servicios usan cachés diferentes. Una nueva llamada a
`Container()` no crea un registro vacío. `make`, `build`, `invoke` y `call` son
asíncronos, pero constructores y handlers síncronos corren directamente en el
hilo que los ejecuta.

Scopes y stacks de resolución usan `ContextVar`. Las tareas hijas heredan por
referencia el objeto scope, con su registro mutable y flag de actividad. El
binding de scope es local al contexto; el objeto no se copia por tarea o
contenedor. Los stacks inmutables de resolución/providers se restauran mediante
tokens, no se vacían globalmente. Cerrar el scope no cancela, espera ni cierra
los recursos almacenados.

## Estructura del módulo

Se inspeccionaron los 23 archivos Python, incluidos los inicializadores. No
hay recursos de runtime no Python en el módulo fuera de su documentación.

| Archivos | Responsabilidad implementada y superficie pública |
| --- | --- |
| [container.py](../container.py) | `Container`: registros, resolución de lifetimes, coordinación diferida, inyección y despacho. |
| [context/manager.py](../context/manager.py), [context/scope.py](../context/scope.py), [context/__init__.py](../context/__init__.py) | `ScopeManager`, `ScopedContext`, `get_current_scope`, `set_current_scope`, `reset_scope`; inicializador vacío. |
| [contracts/container.py](../contracts/container.py), [contracts/facade.py](../contracts/facade.py), [contracts/service_provider.py](../contracts/service_provider.py), [contracts/deferrable_provider.py](../contracts/deferrable_provider.py), [contracts/__init__.py](../contracts/__init__.py) | `IContainer`, `IFacade`, `IServiceProvider`, `IDeferrableProvider`; solo se reexporta IFacade aquí. |
| [entities/binding.py](../entities/binding.py), [entities/invocation.py](../entities/invocation.py), [entities/__init__.py](../entities/__init__.py) | `Binding`, `InvocationPlan`, `callable_plan`, `constructor_plan`, `warm_controller_plan`; el paquete solo exporta Binding. |
| [enums/lifetimes.py](../enums/lifetimes.py), [enums/__init__.py](../enums/__init__.py) | `Lifetime`, reexportado por el paquete de enums. |
| [exceptions/container.py](../exceptions/container.py), [exceptions/__init__.py](../exceptions/__init__.py) | `CircularDependencyException`, reexportada por el paquete de excepciones. |
| [facades/facade.py](../facades/facade.py), [facades/meta.py](../facades/meta.py), [facades/__init__.py](../facades/__init__.py) | `Facade`, `ScopedFacade`, `FacadeMeta`, `ScopedFacadeMeta`, `_FacadeDispatch` privado; el paquete solo exporta Facade. |
| [providers/service_provider.py](../providers/service_provider.py), [providers/deferrable_provider.py](../providers/deferrable_provider.py), [providers/__init__.py](../providers/__init__.py) | `ServiceProvider` y `DeferrableProvider`, ambos reexportados. |
| [__init__.py](../__init__.py) | Inicializador raíz vacío: no reexporta Container, Facade ni contratos. |

## Referencia de API

Los grupos siguientes describen comportamiento y restricciones. Las
[declaraciones literales](#declaraciones-literales) conservan headers,
decoradores, anotaciones, expresiones predeterminadas, campos, alias y exports
del código. No tienen cuerpo: son **fragmentos de referencia, no scripts**.
Las operaciones generadas o heredadas se identifican aparte a continuación.

### Imports y exports

Use `orionis.container.container.Container`, no un supuesto export raíz.
`ScopeManager` y `ScopedContext` se importan desde sus módulos de contexto.
Los cuatro contratos se importan desde sus archivos; solo `IFacade` está
disponible desde `orionis.container.contracts`. `ScopedFacade` y ambas
metaclases también requieren sus módulos de definición. Consulte cada
inicializador en la [tabla de estructura](#estructura-del-módulo) y su
`__all__` literal.

`InvocationPlan` y sus tres funciones públicas son auxiliares de integración,
no exports de `orionis.container.entities`. Imports de bibliotecas y el helper
typing `T` de context/manager.py no son API independiente del contenedor.
Stores, stacks, `_callable_plan` y `_FacadeDispatch` privados se explican solo
cuando resultan necesarios para entender el comportamiento público.

### Identidad y registro de Container

Fuente/import: [orionis.container.container.Container](../container.py), que
implementa `IContainer`. `__new__(cls, *args: object, **kwargs: object)` usa un
diccionario de clase `_instances`, indexado por clase, y `threading.RLock` con
doble comprobación. `__init__` inicializa los diccionarios una vez, comprobando
`_Container__initialized` en el diccionario de la instancia. No existe API
pública de reset, unbind o disposición del contenedor.

| Método | Parámetros, resultado, mutación y errores explícitos |
| --- | --- |
| `instance` | `abstract` es una clase de contrato o None para usar `type(instance)`; `instance` debe ser un objeto inicializado, no una clase. Valida `isinstance` contra el contrato indicado. Retorna True. Fuera de scope almacena Binding SINGLETON y el objeto en el caché global. Dentro de scope publica bajo la clave de contrato sin modificar bindings globales; allí se prohíbe un alias no-None. |
| `transient` | Registra `abstract` -> `concrete` con lifetime TRANSIENT; None abstract usa la clase concreta. Retorna True. |
| `singleton` | El mismo registro con SINGLETON; la primera construcción se cachea bajo el contrato. Retorna True. |
| `scoped` | El mismo registro con SCOPED; el registro es global incluso dentro de un scope activo. Retorna True. |
| `bound` | Recibe tipo o alias y retorna si el contrato está en el scope actual, bindings o caché singleton. Un alias desconocido retorna False; no carga providers diferidos ni considera bound una clase autoconstruible no registrada. |

En registros de clases, las clases suministradas deben ser tipos y la concreta
debe cumplir `issubclass(concrete, abstract)`; en caso contrario, TypeError.
El registro no instancia la clase ni demuestra que pueda construirse por
reflexión. `instance` usa `isinstance`. Una clave no hashable propaga TypeError
del diccionario. Las operaciones de clases/metaclases personalizadas también
pueden fallar; la lista de excepciones no es exhaustiva.

En los cuatro registros, `alias` es opcional, debe ser string si se suministra
y se normaliza con strip; vacío lanza ValueError, no-string lanza TypeError.
Las claves de lookup no se normalizan con strip. `override=False` rechaza con
ValueError contrato/alias global duplicado o instancia scoped duplicada;
`override=True` permite reemplazar. Se evalúa su truthiness, sin exigir bool
literal. Reemplazar un binding de clase elimina su instancia global cacheada.
No limpia entradas scoped existentes, alias antiguos, pins ni objetos que ya
recibieron los consumidores. Reutilizar un alias puede apuntarlo a otro
contrato. No se dispone del servicio anterior al reemplazarlo.

El lookup del caché singleton global precede al scope en `make`: publicar una
instancia scoped no sustituye un singleton global cacheado no-None. Un hit
singleton o scoped también ignora argumentos de construcción nuevos.
Binding.instance queda None en los registros creados por estos métodos; las
instancias reales permanecen en los cachés del contenedor o scope.

### Resolución e invocación de Container

Fuente: [container.py](../container.py), con planes en
[entities/invocation.py](../entities/invocation.py).

| Método | Operación implementada y resultado |
| --- | --- |
| `make(key, *args, **kwargs)` | Espera trabajo pending del provider que corresponda, consulta singleton por tipo, resuelve alias/metadatos diferidos, consulta singleton otra vez, luego scope y finalmente binding. Autoconstruye clases no vinculadas. Alias desconocido o clave no construible lanza ValueError. Retorna el objeto resuelto, no su contrato declarado. |
| `build(type_, *args, **kwargs)` | Exige una clase real antes de consultar cachés/bindings (TypeError en otro caso), coordina providers aplicables y construye la clase suministrada. No retorna el caché singleton ni sustituye la clase por su implementación vinculada. Se respetan lifetimes de dependencias; el propio `__new__` de la clase puede reutilizar un objeto. |
| `invoke(fn, *args, **kwargs)` | Exige un callable que no sea clase (TypeError), selecciona el plan, inyecta parámetros y lo llama. Solo espera el resultado si el plan lo identifica como función de corutina asíncrona. Retorna el resultado. |
| `call(instance, method_name, *args, **kwargs)` | Usa `getattr(instance, method_name, None)` y el mismo despacho. Atributo ausente/None lanza AttributeError; no-callable lanza TypeError. Propaga errores de descriptores/accessors. No valida por separado que el primer argumento sea necesariamente una instancia ni el nombre del método. |

TRANSIENT construye cada vez, salvo que un hit previo del scope suministre la
clave. SINGLETON serializa la primera construcción y cachea resultados no-None
bajo el contrato; None cuenta como miss. SCOPED exige scope actual no-None o
lanza RuntimeError, reutiliza su entrada y publica una instancia bajo un lock
de creación propio de ese scope. Un scope heredado cerrado rechaza nueva
construcción/publicación; `getCurrentScope` todavía puede retornarlo.

`CircularDependencyException` se lanza cuando una construcción con argumentos
vuelve a visitar su tipo concreto en el stack actual. La comprobación previa
al lock evita reentrarlo desde ese stack. El token se restaura en finally.
Es una comprobación local, no un grafo global de esperas entre tareas ni timeout.

Al guard permisivo de callable le sigue ReflectionCallable: admite funciones
Python, métodos, lambdas u objetos callable con los metadatos necesarios de
función. No implica soporte para todo built-in, functools.partial u objeto
con solo `__call__`. Un target no hashable puede lanzar TypeError antes de
reflexión. Se propagan errores de validación e inspección de firmas.

Un callable `async def` se espera una vez. Una función síncrona que devuelve
corutina, Future, generador u otro awaitable no se espera solo por el tipo de
su resultado; ese objeto se entrega al consumidor. Boot de providers y
despacho de facades tienen reglas diferentes, explicadas en sus secciones.
Constructores/callbacks pueden lanzar excepciones arbitrarias, incluida
cancelación; las operaciones públicas no las traducen ni ocultan.

### Parámetros inyectados y schemas

El código de control es `Container.__resolveSignature` / `__resolveArgument`
en [container.py](../container.py), alimentado por la
[reflexión de dependencias](../../introspection/dependencies/reflection.py).
Se conservan las anotaciones públicas literales de *args/**kwargs en el apéndice;
son declaraciones, no coerción ni validación runtime de tipos.

La firma se procesa en orden de declaración. Reflexión elimina el receptor
bound, nombres self/cls y parámetros variádicos; **los parámetros ordinarios
llamados args o kwargs siguen siendo inyectables**. Los posicionales exclusivos
y los posicionales-o-keyword siguen la misma rama no-keyword-only.

Para un parámetro no-keyword-only:

1. Consume el siguiente valor posicional explícito, si existe.
2. Si no, consume el valor keyword que coincida, incluido None.
3. Resuelve el provider diferido anunciado para el path completo del tipo, si aplica.
4. Para un schema, lee Request y valida su payload de forma asíncrona.
5. Resuelve el tipo registrado mediante `make`, salvo una referencia forward
   no resuelta representada como typing/str.
6. Usa resolución automática: built-in/typing no resueltos lanzan TypeError;
   un default declarado gana en el fallback; una clase resuelta sin default
   se suministra a `make`.

Los keyword-only usan el mismo orden sin consumir posicionales. Los restantes
posicionales se añaden y los keywords sin consumir se reenvían. Python sigue
aplicando aridad y puede rechazar duplicados o argumentos inesperados. No se
convierten ni validan por anotación los valores proporcionados. **Los valores
explícitos evitan el provider diferido y la validación del request.**

Reflexión describe un parámetro con default usando el tipo del default, no
su anotación. Un default None hace que no sea schema; un tipo de default
registrado puede inyectarse antes de recurrir a dicho default. Los built-ins
sin default son utilizables si se proporcionan o registran. Los constructos
typing no soportados no se interpretan automáticamente como factories
union/optional. Hints string desconocidos lanzan TypeError con un mensaje de
forward-reference aunque exista un servicio string registrado.

Schemas implícitos son subclases de `msgspec.Struct`, no solo Orionis Schema.
El contenedor resuelve [Request](../../http/request.py) concreto, espera
`data()` y [Schema.validateAsync](../../schemas/validator.py); no produce una
respuesta HTTP. Pueden propagarse dependencias de Request ausentes, errores
de parsing, [ValidationException](../../schemas/exceptions/validation.py),
reglas personalizadas y cancelación. Varios parámetros reutilizan lo que
cachee Request, pero cada uno se valida. Los explícitos no necesitan request.

### InvocationPlan y funciones de planes

Fuente/import: [orionis.container.entities.invocation](../entities/invocation.py).
`InvocationPlan` es `@dataclass(frozen=True, slots=True)` con campos obligatorios
`arguments: tuple[Argument, ...]` e `is_async: bool`. Constructor compatible
con posicionales, igualdad, representación y hash son generados por el decorador,
no métodos literales. Las anotaciones no validan en runtime ni congelan
profundamente metadatos/defaults referenciados. No hereda BaseEntity ni toDict.

| Función | Parámetros, resultado y límites |
| --- | --- |
| `callable_plan(target)` | Para MethodType bound usa la función subyacente con bound=True, excluyendo receptor. En otro caso usa el target directamente. Valida con ReflectionCallable; retorna InvocationPlan reutilizable y clasificación de corutina de inspect.iscoroutinefunction. |
| `constructor_plan(target, constructor)` | Valida clase concreta con ReflectionConcrete; incluye el descriptor actual del constructor en la clave LRU. Retorna argumentos e is_async=False. Restaura hints string locales a clase usando globals del módulo del constructor, atributos de clase y su propio nombre; acepta solo tipos clase resueltos. |
| `warm_controller_plan(target, method_name)` | Usa inspect.getattr_static para no ejecutar getters de descriptores custom. Precalienta constructores ordinarios soportados y acciones instance/static/class; omite descriptores custom o acciones ausentes. Retorna None sin construir controller ni resolver servicios. Los descriptores inspeccionados aún pueden causar errores de reflexión. |

`constructor_plan` lleva lru_cache(maxsize=1024). El `_callable_plan` privado
tiene LRU(1024) propio, indexado por callable subyacente y modo de receptor.
Un hit reutiliza el plan; la API de caché del wrapper del constructor proviene
de functools, no de métodos declarados aquí. La invocación lee bindings y
argumentos actuales. Reemplazar función/constructor cambia la clave; modificar
anotaciones/defaults del mismo callable no garantiza invalidación. Precalentar
no garantiza retención permanente, sino que está sujeto a capacidad.

La [reflexión inferior](../../introspection/dependencies/reflection.py) también
restaura hints string disponibles en globals del módulo, independientemente si
otro es desconocido, y conserva defaults. La reparación del constructor añade
namespaces locales a clase. Los errores de evaluación capturados conservan
metadatos sin resolver que la inyección puede rechazar después. El código
soporta los casos de future annotations comprobados, a diferencia de la
prohibición general antigua; no garantiza resolver cualquier string o tipo ausente.

### ScopeManager y ScopedContext

Fuente/import: [ScopeManager](../context/manager.py) y
[ScopedContext](../context/scope.py).
`Container.beginScope()` retorna un nuevo manager; `getCurrentScope()` hace
cast del valor raw sin validarlo ni consultar isActive.

ScopeManager usa slots y es de un solo uso. Antes de entrar está inactivo,
pero admite almacenamiento y creationLock mientras no se haya cerrado.
`__aenter__` rechaza manager activo/cerrado con RuntimeError, guarda un token
ContextVar, lo activa y retorna self. `__aexit__` lo marca inactivo/cerrado,
vacía instancias y mapa de locks, restaura el token anterior, retorna None y
no suprime la excepción del bloque. El token debe resetearse en su contexto;
salir antes de entrar o reutilizar/resetear un token puede lanzar errores
subyacentes después de limpiar estado.

| Operación | Resultado, mutación y casos límite |
| --- | --- |
| `manager[key]` | Retorna valor almacenado o None. Sin espera, conversión ni error por estado cerrado. |
| `manager[key] = value` / `set(key, value)` | Almacena bajo clave hashable. Tras cerrar lanza RuntimeError; admite valores ordinarios, corutinas y Tasks. |
| `key in manager` | Comprueba presencia: una clave con None sigue presente. |
| `clear()` | Vacía solo instancias, sin valor de retorno, disposición de recursos, cancelación de tareas ni reinicio de actividad/locks. Puede llamarse tras cerrar. |
| `creationLock(key)` | Retiene de forma diferida un asyncio.Lock por clave **en ese manager**. Cerrado lanza RuntimeError. No reemplaza locks al cambiar de loop. |
| `isActive` | Property de solo lectura, False antes de entrar/tras salir, también en hijos que retienen el mismo manager. |
| `await get(key)` | Ausente/None -> None. Convierte una corutina almacenada en Task y la publica antes de esperar; espera una Task, luego guarda el resultado mediante el guard de escritura cerrada. Otros valores, incluidos Future no-Task/awaitables, se retornan sin tocar. |
| `await resolve(key)` | Usa get, pero lanza KeyError si el resultado es None, aunque hubiera clave. |

Llamadas get concurrentes comparten la Task publicada dentro de un loop. La
cancelación de un waiter puede propagarse a esa Task: no se usa shield. Una
Task fallida permanece almacenada y puede volver a fallar. Si termina tras
el cierre, no puede republicar su resultado. La conversión corutina->Task
asigna directamente al diccionario interno; almacenar una corutina sin
esperarla y después limpiar no la cierra. El consumidor administra ese lifecycle.

`ScopedContext.getCurrentScope()` retorna objeto raw o None.
`setCurrentScope(scope)` lo almacena y retorna Token; `reset(token)` restaura
el binding anterior. No valida tipo, actividad ni pertenencia. Los alias
`get_current_scope`, `set_current_scope` y `reset_scope` son métodos bound
get/set/reset del ContextVar, no wrappers adicionales; sus declaraciones
son asignaciones, con semántica estándar de tokens contextvars. Todos los
Containers consultan el mismo ContextVar. Scopes anidados restauran el externo.
Copiar/heredar contexto no copia los servicios almacenados.

### Binding y Lifetime

Fuente/import: [Binding](../entities/binding.py), reexportado por entities,
y [Lifetime](../enums/lifetimes.py), reexportado por enums.

Binding es dataclass frozen keyword-only que extiende BaseEntity, **sin
slots=True**. El constructor generado recibe `contract`, `concrete`,
`instance`, `lifetime`, `alias`; el apéndice conserva campos/metadatos exactos.
Todos valen None por defecto excepto lifetime=Lifetime.TRANSIENT.
`__post_init__` solo exige lifetime de tipo Lifetime y lanza TypeError en
otro caso. El record no valida contract/concrete/instance/alias. Los guards
generados de asignación frozen no congelan profundamente la instancia
referenciada; el hash generado puede fallar con campos no hashables.

[BaseEntity.toDict / getFields](../../support/entities/base.py), heredados,
proporcionan diccionarios copiados recursivamente y descripciones normalizadas
de campos. toDict serializa enums por su valor; getFields puede ejecutar
defaults callable y normalizar metadatos. Pueden propagarse errores de copia
o metadatos. Sus firmas pertenecen a BaseEntity, no son declaraciones de Binding.

Lifetime es Enum con TRANSIENT, SINGLETON y SCOPED declarados usando auto().
Sus valores runtime son 1, 2 y 3, en ese orden. El contenedor compara esos
miembros por identidad; el entero 2 no es lifetime válido en Binding.
Construcción/lookup estándar de Enum son heredados. No hay conversión custom
ni jerarquía adicional pública de excepciones declarada aquí.

### ServiceProvider y lifecycle diferido

Fuente/import: [ServiceProvider](../providers/service_provider.py) y
[DeferrableProvider](../providers/deferrable_provider.py), reexportados por
providers. ServiceProvider implementa IServiceProvider y guarda directamente
`app: IApplication`, sin comprobar su tipo. `register()` y async `boot()` solo
tienen docstring y retornan None. **La implementación no lanza** el
NotImplementedError anunciado en la docstring de register. DeferrableProvider
implementa IDeferrableProvider de forma independiente; no hereda ServiceProvider.
Su classmethod provides() lanza NotImplementedError hasta sobrescribirlo.
Declarar provides no prepara el registro de un Container independiente.

El [registro de providers](../../foundation/application.py) de Application
guarda metadatos module/class bajo alias o path del tipo y distingue eager de
DeferrableProvider. Una implementación que necesita estado de aplicación puede
heredar ambas bases, como en el ejemplo 7.

La coordinación diferida de [container.py](../container.py) se indexa por
**(module, class)**, no solo por cada servicio solicitado:

1. Localiza metadatos por alias o module/name de tipo; sin metadatos no hace nada.
2. Omite providers completos y permite que contextos bootstrap recursivos/heredados
   usen sus propios servicios publicados mediante un stack local al contexto.
3. Serializa la identidad del provider con un creation lock del contenedor.
4. Importa/carga/construye la clase, llama register síncrono, retiene la instancia
   y marca pending todas las claves anunciadas.
5. Espera boot solo si inspect.iscoroutinefunction(boot); en otro caso lo llama
   síncronamente. Un boot síncrono que retorna awaitable no se espera.
6. Solo tras boot correcto marca la identidad lista y elimina el estado pending.

Fuera de ese contexto bootstrap, make/build para claves pending coincidentes
esperan boot. También participan las correspondencias alias->contrato y
tipo->alias de binding; no extienda esa garantía a un build concreto arbitrario
no anunciado. Si boot falla o se cancela tras registro correcto, el reintento
reutiliza la misma instancia sin registrar otra vez. Fallar durante register
no garantiza rollback: sus efectos pueden persistir y otro intento registrar
de nuevo. Errores de import/getattr/build/register/boot se propagan. No hay
validación de metadatos como schema público separado; el registro protegido
no es un método público genérico de registro.

### Facade y FacadeMeta

Fuente/import: [Facade](../facades/facade.py), reexportada por facades, y
[FacadeMeta](../facades/meta.py), en su módulo de definición. Facade usa la
metaclase, pero **no hereda IFacade en runtime**. Puede declararse una subclase
sin accessor; getFacadeAccessor() base lanza NotImplementedError al invocarlo.
Los accessors son tipos o claves string admitidos por el contenedor de aplicación.

| Método u operación | Comportamiento implementado |
| --- | --- |
| `await resolve(*args, **kwargs)` | Obtiene/cachea Application de forma diferida si `_application` es None. Exige isBooted o lanza RuntimeError, y espera make(accessor, *args, **kwargs). No consulta un pin ni lo establece automáticamente. |
| `await pin()` | Resuelve una vez y guarda `_pinned_instance` en cls; retorna None. Los atributos dinámicos siguientes son acceso directo al servicio, incluso con binding transient. |
| `unpin()` | Establece ese atributo de clase en None; retorna None. No limpia cachés de aplicación o dispatchers. |
| Atributo de clase ausente | FacadeMeta.__getattr__ usa getattr(pinned_service, name) con pin. Sin pin retiene y retorna una función dispatcher por (clase de facade, name). Leer/llamar esa función no resuelve un servicio todavía. |

Sin pin, `Facade.method(...)` retorna `_FacadeDispatch` privado, no el
resultado del servicio. `await` resuelve el servicio de nuevo, lee el atributo,
lo llama si es callable y espera una vez un resultado awaitable. Para un
atributo no-callable use `await Facade.attribute()`; en ese caso se ignoran
argumentos del dispatcher. Leer un atributo sin pin no comprueba existencia:
incluso un nombre desconocido obtiene dispatcher; getattr puede fallar después.

`async with Facade.method(...)` resuelve el resultado del atributo y espera
directamente __aenter__/__aexit__. A diferencia de await, no espera primero
una corutina retornada por el método. Para esa operación use método síncrono
que retorne context manager asíncrono. Se delega el resultado de salida,
incluida supresión de excepciones. Debe entrarse antes de salir. Los dispatch
no memoizan resultados al esperarlos y mantienen un único slot de contexto
mutable; no se garantiza coordinación en reutilización/reentrada. No son
proxies genéricos para encadenar atributos.

Con pin se usa getattr normal: valores síncronos siguen síncronos, métodos de
corutina requieren await y errores de descriptor/atributo ausente son inmediatos.
Atributos y classmethods reales evitan __getattr__. Pins/aplicaciones son
estado de clase y siguen herencia hasta que la subclase asigna un valor propio.
No hay aislamiento por request ni invalidación automática al cambiar bindings.
Boot de un provider puede pinear como efecto independiente; esperar el dispatcher
no lo hace intrínsecamente.

### ScopedFacade y ScopedFacadeMeta

Fuente/import: [ScopedFacade](../facades/facade.py),
[ScopedFacadeMeta](../facades/meta.py). ScopedFacade hereda Facade, sobrescribe
sus métodos de lifecycle y usa ScopedFacadeMeta para atributos ausentes.

`scopedInstance()` exige contexto raw de tipo ScopeManager con isActive=True
y valor no-None bajo **la clave exacta del accessor**; si no, RuntimeError.
No traduce alias globales, espera Tasks almacenadas, llama container.make,
autoconstruye servicios ni consulta pins globales.

Async `resolve(*_args, **_kwargs)` ignora argumentos y retorna scopedInstance.
Async `pin()` solo comprueba disponibilidad y retorna None; unpin() es no-op
que retorna None. ScopedFacadeMeta.__getattr__ delega inmediatamente a
getattr(scopedInstance(), name): métodos/properties síncronos ya son directos
y los asíncronos siguen asíncronos. Atributos de servicio ausentes lanzan
AttributeError; scope inválido/inactivo lanza RuntimeError. Las tareas hijas
con un scope heredado cerrado no acceden al servicio mediante esta facade.

### Contratos y excepciones

Los cuatro contratos son clases abstractas ABC; sus métodos declaran contratos
con cuerpos de solo docstring y no resuelven servicios por sí mismos. No
declaran __slots__ ni validan anotaciones en runtime.

| Contrato | Operaciones declaradas y relación |
| --- | --- |
| [IContainer](../contracts/container.py) | Once métodos abstractos: instance, transient, singleton, scoped, bound, beginScope, getCurrentScope, make, build, invoke, call. Implementado por Container. |
| [IServiceProvider](../contracts/service_provider.py) | register síncrono y boot asíncrono abstractos; implementado por ServiceProvider. |
| [IDeferrableProvider](../contracts/deferrable_provider.py) | Classmethod provides abstracto; implementado por el placeholder que lanza en DeferrableProvider. |
| [IFacade](../contracts/facade.py) | Classmethods getFacadeAccessor, resolve, pin, unpin abstractos; contrato de typing, no base runtime de Facade. |

[CircularDependencyException](../exceptions/container.py) hereda Exception
directamente, sin constructor custom ni excepción base de módulo. Se heredan
args y semántica estándar de mensaje/traceback/chaining. Consulte la condición
real en [resolución](#resolución-e-invocación-de-container). TypeError,
ValueError, RuntimeError, AttributeError, KeyError, errores de validación y
fallos arbitrarios invocados permanecen distintos; no se envuelven todos
en esta excepción.

### Declaraciones literales

Cada owner se enlaza al código inspeccionado. Los campos describen
constructores generados y constantes; los headers de clase no reproducen
firmas generadas. Los fragmentos sin cuerpo conservan literalmente código,
incluidos comentarios de firmas, y no son ejemplos ejecutables separados.

#### __init__.py

Fuente: [orionis/container/__init__.py](../__init__.py).

Sin API pública declarada directamente; inicializador de paquete vacío.

#### container.py

Fuente: [orionis/container/container.py](../container.py).

`Container`

```python
class Container(IContainer):
```

`Container.__new__`

```python
def __new__(cls, *args: object, **kwargs: object) -> Self:
```

`Container.__init__`

```python
def __init__(self) -> None:
```

`Container.instance`

```python
def instance(
    self,
    abstract: type[Any] | None,
    instance: object,
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`Container.transient`

```python
def transient(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`Container.singleton`

```python
def singleton(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`Container.scoped`

```python
def scoped(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`Container.bound`

```python
def bound(
    self,
    key: type[Any] | str,
) -> bool:
```

`Container.beginScope`

```python
def beginScope(self) -> ScopeManager:
```

`Container.getCurrentScope`

```python
def getCurrentScope(self) -> ScopeManager | None:
```

`Container.make`

```python
async def make(
    self,
    key: type[Any] | str,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`Container.build`

```python
async def build(
    self,
    type_: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`Container.invoke`

```python
async def invoke(
    self,
    fn: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`Container.call`

```python
async def call(
    self,
    instance: object,
    method_name: str,
    *args: object,
    **kwargs: object,
) -> Any:
```

#### context/__init__.py

Fuente: [orionis/container/context/__init__.py](../context/__init__.py).

Sin API pública declarada directamente; inicializador de paquete vacío.

#### context/manager.py

Fuente: [orionis/container/context/manager.py](../context/manager.py).

`ScopeManager`

```python
class ScopeManager:

    # ruff: noqa: ANN401
```

`ScopeManager fields`

```python
__slots__ = ("__active", "__closed", "__creation_locks", "_instances", "_token")
```

`ScopeManager.__init__`

```python
def __init__(self) -> None:
```

`ScopeManager.creationLock`

```python
def creationLock(self, key: object) -> asyncio.Lock:
```

`ScopeManager.isActive`

```python
@property
def isActive(self) -> bool:
```

`ScopeManager.__getitem__`

```python
def __getitem__(self, key: object) -> object | None:
```

`ScopeManager.__setitem__`

```python
def __setitem__(self, key: object, value: object) -> None:
```

`ScopeManager.__contains__`

```python
def __contains__(self, key: object) -> bool:
```

`ScopeManager.clear`

```python
def clear(self) -> None:
```

`ScopeManager.__aenter__`

```python
async def __aenter__(self) -> Self:
```

`ScopeManager.__aexit__`

```python
async def __aexit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: types.TracebackType | None,
) -> None:
```

`ScopeManager.get`

```python
async def get(self, key: object) -> Any | None:
```

`ScopeManager.set`

```python
def set(self, key: object, value: Any) -> None:
```

`ScopeManager.resolve`

```python
async def resolve(self, key: object) -> Any:
```

#### context/scope.py

Fuente: [orionis/container/context/scope.py](../context/scope.py).

`ScopedContext`

```python
class ScopedContext:

    # ruff: noqa: SLF001

    # Define a context variable to hold the active scope.
    # The default value is None, indicating no active scope.
```

`ScopedContext.getCurrentScope`

```python
@classmethod
def getCurrentScope(cls) -> object | None:
```

`ScopedContext.setCurrentScope`

```python
@classmethod
def setCurrentScope(cls, scope: object) -> contextvars.Token:
```

`ScopedContext.reset`

```python
@classmethod
def reset(cls, token: contextvars.Token) -> None:
```

`get_current_scope`

```python
get_current_scope = ScopedContext._active_scope.get
```

`set_current_scope`

```python
set_current_scope = ScopedContext._active_scope.set
```

`reset_scope`

```python
reset_scope       = ScopedContext._active_scope.reset
```

#### contracts/__init__.py

Fuente: [orionis/container/contracts/__init__.py](../contracts/__init__.py).

`__all__`

```python
__all__ = ["IFacade"]
```

#### contracts/container.py

Fuente: [orionis/container/contracts/container.py](../contracts/container.py).

`IContainer`

```python
class IContainer(ABC):

    # ruff: noqa: ANN401

    @abstractmethod
```

`IContainer.instance`

```python
@abstractmethod
def instance(
    self,
    abstract: type[Any] | None,
    instance: object,
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`IContainer.transient`

```python
@abstractmethod
def transient(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`IContainer.singleton`

```python
@abstractmethod
def singleton(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`IContainer.scoped`

```python
@abstractmethod
def scoped(
    self,
    abstract: type[Any] | None,
    concrete: type[Any],
    *,
    alias: str | None = None,
    override: bool = False,
) -> bool:
```

`IContainer.bound`

```python
@abstractmethod
def bound(
    self,
    key: type[Any] | str,
) -> bool:
```

`IContainer.beginScope`

```python
@abstractmethod
def beginScope(self) -> ScopeManager:
```

`IContainer.getCurrentScope`

```python
@abstractmethod
def getCurrentScope(self) -> ScopeManager | None:
```

`IContainer.make`

```python
@abstractmethod
async def make(
    self,
    key: type[Any] | str,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`IContainer.build`

```python
@abstractmethod
async def build(
    self,
    type_: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`IContainer.invoke`

```python
@abstractmethod
async def invoke(
    self,
    fn: Callable[..., Any],
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any],
) -> Any:
```

`IContainer.call`

```python
@abstractmethod
async def call(
    self,
    instance: object,
    method_name: str,
    *args: object,
    **kwargs: object,
) -> Any:
```

#### contracts/deferrable_provider.py

Fuente: [orionis/container/contracts/deferrable_provider.py](../contracts/deferrable_provider.py).

`IDeferrableProvider`

```python
class IDeferrableProvider(ABC):

    @classmethod
    @abstractmethod
```

`IDeferrableProvider.provides`

```python
@classmethod
@abstractmethod
def provides(cls) -> list[type | str]:
```

#### contracts/facade.py

Fuente: [orionis/container/contracts/facade.py](../contracts/facade.py).

`IFacade`

```python
class IFacade(ABC):

    @classmethod
    @abstractmethod
```

`IFacade.getFacadeAccessor`

```python
@classmethod
@abstractmethod
def getFacadeAccessor(cls) -> str | type:
```

`IFacade.resolve`

```python
@classmethod
@abstractmethod
async def resolve(cls, *args: object, **kwargs: object) -> object:
```

`IFacade.pin`

```python
@classmethod
@abstractmethod
async def pin(cls) -> None:
```

`IFacade.unpin`

```python
@classmethod
@abstractmethod
def unpin(cls) -> None:
```

#### contracts/service_provider.py

Fuente: [orionis/container/contracts/service_provider.py](../contracts/service_provider.py).

`IServiceProvider`

```python
class IServiceProvider(ABC):

    @abstractmethod
```

`IServiceProvider.register`

```python
@abstractmethod
def register(self) -> None:
```

`IServiceProvider.boot`

```python
@abstractmethod
async def boot(self) -> None:
```

#### entities/__init__.py

Fuente: [orionis/container/entities/__init__.py](../entities/__init__.py).

`__all__`

```python
__all__ = ["Binding"]
```

#### entities/binding.py

Fuente: [orionis/container/entities/binding.py](../entities/binding.py).

`Binding`

```python
@dataclass(frozen=True, kw_only=True)
class Binding(BaseEntity):
```

`Binding fields`

```python
contract: type | None = field(
        default=None,
        metadata={
            "description": "Contract of the concrete class to inject.",
            "default": None,
        },
    )
concrete: type | None = field(
        default=None,
        metadata={
            "description": "Concrete class implementing the contract.",
            "default": None,
        },
    )
instance: object | None = field(
        default=None,
        metadata={
            "description": "Concrete instance of the class, if provided.",
            "default": None,
        },
    )
lifetime: Lifetime = field(
        default=Lifetime.TRANSIENT,
        metadata={
            "description": "Lifetime of the instance.",
            "default": Lifetime.TRANSIENT,
        },
    )
alias: str | None = field(
        default=None,
        metadata={
            "description": "Alias for resolving the dependency from the container.",
            "default": None,
        },
    )
```

`Binding.__post_init__`

```python
def __post_init__(self) -> None:
```

#### entities/invocation.py

Fuente: [orionis/container/entities/invocation.py](../entities/invocation.py).

`InvocationPlan`

```python
@dataclass(frozen=True, slots=True)
class InvocationPlan:
```

`InvocationPlan fields`

```python
arguments: tuple[Argument, ...]
is_async: bool
```

`callable_plan`

```python
def callable_plan(target: Callable) -> InvocationPlan:
```

`constructor_plan`

```python
@lru_cache(maxsize=1024)
def constructor_plan(target: type, constructor: object) -> InvocationPlan:
```

`warm_controller_plan`

```python
def warm_controller_plan(target: type, method_name: str) -> None:
```

#### enums/__init__.py

Fuente: [orionis/container/enums/__init__.py](../enums/__init__.py).

`__all__`

```python
__all__ = ["Lifetime"]
```

#### enums/lifetimes.py

Fuente: [orionis/container/enums/lifetimes.py](../enums/lifetimes.py).

`Lifetime`

```python
class Lifetime(Enum):
```

`Lifetime fields`

```python
TRANSIENT = auto()
SINGLETON = auto()
SCOPED = auto()
```

#### exceptions/__init__.py

Fuente: [orionis/container/exceptions/__init__.py](../exceptions/__init__.py).

`__all__`

```python
__all__ = ["CircularDependencyException"]
```

#### exceptions/container.py

Fuente: [orionis/container/exceptions/container.py](../exceptions/container.py).

`CircularDependencyException`

```python
class CircularDependencyException(Exception):
```

#### facades/__init__.py

Fuente: [orionis/container/facades/__init__.py](../facades/__init__.py).

`__all__`

```python
__all__ = ["Facade"]
```

#### facades/facade.py

Fuente: [orionis/container/facades/facade.py](../facades/facade.py).

`Facade`

```python
class Facade(metaclass=FacadeMeta):

    # ruff: noqa: PLC0415

    # Cached application instance shared across all facade subclasses
```

`Facade.getFacadeAccessor`

```python
@classmethod
def getFacadeAccessor(cls) -> str | type:
```

`Facade.resolve`

```python
@classmethod
async def resolve(cls, *args: object, **kwargs: object) -> object:
```

`Facade.pin`

```python
@classmethod
async def pin(cls) -> None:
```

`Facade.unpin`

```python
@classmethod
def unpin(cls) -> None:
```

`ScopedFacade`

```python
class ScopedFacade(Facade, metaclass=ScopedFacadeMeta):
```

`ScopedFacade.scopedInstance`

```python
@classmethod
def scopedInstance(cls) -> object:
```

`ScopedFacade.resolve`

```python
@classmethod
async def resolve(cls, *_args: object, **_kwargs: object) -> object:
```

`ScopedFacade.pin`

```python
@classmethod
async def pin(cls) -> None:
```

`ScopedFacade.unpin`

```python
@classmethod
def unpin(cls) -> None:
```

#### facades/meta.py

Fuente: [orionis/container/facades/meta.py](../facades/meta.py).

`FacadeMeta`

```python
class FacadeMeta(type):
```

`FacadeMeta.__getattr__`

```python
def __getattr__(cls, name: str) -> object:
```

`ScopedFacadeMeta`

```python
class ScopedFacadeMeta(FacadeMeta):
```

`ScopedFacadeMeta.__getattr__`

```python
def __getattr__(cls, name: str) -> object:
```

#### providers/__init__.py

Fuente: [orionis/container/providers/__init__.py](../providers/__init__.py).

`__all__`

```python
__all__ = ["DeferrableProvider", "ServiceProvider"]
```

#### providers/deferrable_provider.py

Fuente: [orionis/container/providers/deferrable_provider.py](../providers/deferrable_provider.py).

`DeferrableProvider`

```python
class DeferrableProvider(IDeferrableProvider):
```

`DeferrableProvider.provides`

```python
@classmethod
def provides(cls) -> list[type | str]:
```

#### providers/service_provider.py

Fuente: [orionis/container/providers/service_provider.py](../providers/service_provider.py).

`ServiceProvider`

```python
class ServiceProvider(IServiceProvider):

    # ruff: noqa: TC001
```

`ServiceProvider.__init__`

```python
def __init__(
    self,
    app: IApplication,
) -> None:
```

`ServiceProvider.register`

```python
def register(self) -> None:
```

`ServiceProvider.boot`

```python
async def boot(self) -> None:
```

## Ejemplos de uso

Ejecute cada bloque Python como script independiente con framework y
dependencias core instalados sobre Python 3.14+. En las ejecuciones locales
verificadas, los imports apuntaron al checkout inspeccionado, se desactivó
bytecode, se separaron procesos/árboles de recursos y se bloquearon escrituras
fuera del temporal de validación. Ningún script usa bootstrap del checkout ni
un servicio externo real.

### 1. Registrar lifetimes, alias y reemplazos

Se espera identidad contrato/alias para singleton, Reports nuevos para
transient, prioridad de argumentos explícitos y reemplazo vivo de bindings.

```python
import asyncio
from orionis.container.container import Container

class Repository:
    pass

class MemoryRepository(Repository):
    pass

class ReplacementRepository(Repository):
    pass

class Report:
    def __init__(self, repository: Repository, prefix: str = "report") -> None:
        self.repository = repository
        self.prefix = prefix

async def main() -> None:
    container = Container()
    assert container.singleton(Repository, MemoryRepository, alias=" repository ")
    first = await container.make(Repository)
    assert first is await container.make("repository")
    assert container.bound("repository") and not container.bound(" repository ")
    assert await container.build(MemoryRepository) is not first
    container.transient(None, Report)
    report = await container.make(Report)
    assert report is not await container.make(Report)
    assert report.repository is first
    explicit = MemoryRepository()
    prepared = await container.build(Report, explicit, prefix="prepared")
    assert prepared.repository is explicit and prepared.prefix == "prepared"
    container.singleton(Repository, ReplacementRepository, override=True)
    replaced = await container.build(Report)
    assert isinstance(replaced.repository, ReplacementRepository)
    assert report.repository is first

asyncio.run(main())
```

### 2. Invocar callables y manejar errores reales de resolución

Se esperan valores explícitos count/keyword, TypeError para built-in no
resuelto, ValueError para alias desconocido y la excepción de dependencia
circular del módulo para el constructor autorreferenciado.

```python
import asyncio
from orionis.container.container import Container
from orionis.container.exceptions import CircularDependencyException

def multiply(count: int, *, factor: int = 2) -> int:
    return count * factor

class Cycle:
    def __init__(self, dependency: "Cycle") -> None:
        self.dependency = dependency

async def main() -> None:
    container = Container()
    assert await container.invoke(multiply, 4, factor=3) == 12
    assert await container.invoke(multiply, count=4) == 8
    failures = []
    try:
        await container.invoke(multiply)
    except TypeError:
        failures.append("builtin")
    try:
        await container.make("missing.alias")
    except ValueError:
        failures.append("alias")
    try:
        await container.build(Cycle)
    except CircularDependencyException:
        failures.append("cycle")
    assert failures == ["builtin", "alias", "cycle"]

asyncio.run(main())
```

### 3. Compartir servicios scoped y usar ScopedFacade

Se espera identidad en el scope, servicio anidado distinto, restauración del
scope externo y rechazo inmediato de la facade tras cerrar. La tarea hija
lee el mismo servicio perteneciente al scope externo.

```python
import asyncio
from orionis.container.container import Container
from orionis.container.facades.facade import ScopedFacade

class SessionValue:
    def __init__(self) -> None:
        self.label = "unset"

class LocalValue(ScopedFacade):
    @classmethod
    def getFacadeAccessor(cls) -> type:
        return SessionValue

async def main() -> None:
    container = Container()
    container.scoped(None, SessionValue)
    try:
        await container.make(SessionValue)
    except RuntimeError:
        pass
    else:
        raise AssertionError("A scoped service resolved without a scope")
    async with container.beginScope() as outer:
        first = await container.make(SessionValue)
        first.label = "outer"
        assert first is await container.make(SessionValue)
        child = asyncio.create_task(LocalValue.resolve())
        assert await child is first and LocalValue.label == "outer"
        async with container.beginScope():
            second = await container.make(SessionValue)
            second.label = "inner"
            assert second is not first and LocalValue.label == "inner"
        assert container.getCurrentScope() is outer
        assert LocalValue.label == "outer"
    assert not outer.isActive and SessionValue not in outer
    try:
        LocalValue.scopedInstance()
    except RuntimeError:
        pass
    else:
        raise AssertionError("A closed scope exposed its service")

asyncio.run(main())
```

### 4. Resolver tareas almacenadas y conservar tokens de contexto

Se espera cachear el resultado de una corutina, presencia de None con fallo
en resolve, limpieza temporal del contexto reversible y error al escribir
en manager cerrado. La limpieza no descarta corutinas sin resolver.

```python
import asyncio
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import (
    get_current_scope,
    reset_scope,
    set_current_scope,
)

async def produce() -> str:
    await asyncio.sleep(0)
    return "ready"

async def main() -> None:
    manager = ScopeManager()
    manager.set("before", "entry")
    assert not manager.isActive
    async with manager:
        assert get_current_scope() is manager
        assert manager.creationLock("job") is manager.creationLock("job")
        manager.set("job", produce())
        results = await asyncio.gather(manager.resolve("job"), manager.get("job"))
        assert results == ["ready", "ready"] and manager["job"] == "ready"
        manager["null"] = None
        assert "null" in manager and await manager.get("null") is None
        try:
            await manager.resolve("null")
        except KeyError:
            pass
        else:
            raise AssertionError("None was accepted as a resolved instance")
        token = set_current_scope(None)
        try:
            assert get_current_scope() is None
        finally:
            reset_scope(token)
        assert get_current_scope() is manager
        manager.clear()
        assert manager.isActive and "job" not in manager
    assert get_current_scope() is None and not manager.isActive
    try:
        manager.set("late", "value")
    except RuntimeError:
        pass
    else:
        raise AssertionError("A closed manager accepted a value")

asyncio.run(main())
```

### 5. Inspeccionar Binding y planes de invocación reutilizables

Se espera compartir plan de método bound sin retener el primer controller,
metadatos de constructor que describen Dependency y serialización de enum
por la API heredada de entidad. Lifetime entero es un error real de definición.

```python
import asyncio
import gc
import weakref
from orionis.container.container import Container
from orionis.container.entities.binding import Binding
from orionis.container.entities.invocation import (
    callable_plan,
    constructor_plan,
    warm_controller_plan,
)
from orionis.container.enums import Lifetime

class Dependency:
    pass

class Controller:
    def __init__(self, dependency: Dependency) -> None:
        self.dependency = dependency

    async def action(self, count: int = 2) -> int:
        return count

async def main() -> None:
    container = Container()
    container.singleton(None, Dependency)
    warm_controller_plan(Controller, "action")
    first = await container.build(Controller)
    second = await container.build(Controller)
    plan = callable_plan(first.action)
    assert plan is callable_plan(second.action) and plan.is_async
    constructor = constructor_plan(Controller, Controller.__init__)
    assert constructor.arguments[0].type is Dependency
    assert await container.call(second, "action", count=7) == 7
    reference = weakref.ref(first)
    del first
    gc.collect()
    assert reference() is None
    binding = Binding(contract=Dependency, concrete=Dependency,
                      lifetime=Lifetime.SINGLETON)
    assert binding.toDict()["lifetime"] == 2
    assert len(binding.getFields()) == 5
    try:
        Binding(lifetime=2)
    except TypeError:
        pass
    else:
        raise AssertionError("An integer was accepted as Lifetime")

asyncio.run(main())
```

### 6. Inyectar un schema desde un Request local real

Usa ASGITransportAdapter, Request y validación Schema reales, sin servidor
HTTP. Se espera quantity=3 parseado, ValidationException propagada para
quantity inválido y payload explícito utilizable sin Request actual.

```python
import asyncio
from orionis.container.container import Container
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.enums.interfaces import Interface
from orionis.http.request import Request
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.schema import Schema

class Payload(Schema):
    quantity: int

async def action(payload: Payload, *, increment: int = 2) -> int:
    return payload.quantity + increment

def make_request(body: bytes) -> Request:
    messages = [{"type": "http.request", "body": body, "more_body": False}]
    async def receive() -> dict[str, object]:
        return messages.pop(0)
    scope = {
        "type": "http", "method": "POST", "scheme": "http", "path": "/",
        "query_string": b"", "server": ("localhost", 80),
        "headers": [(b"content-type", b"application/json")],
    }
    return Request(Interface.ASGI, ASGITransportAdapter(scope),
                   receive_or_protocol=receive)

async def main() -> None:
    container = Container()
    async with container.beginScope():
        request = make_request(b'{"quantity":3}')
        container.instance(Request, request)
        assert await container.invoke(action) == 5
        assert await request.data() == {"quantity": 3}
    async with container.beginScope():
        container.instance(Request, make_request(b'{"quantity":"invalid"}'))
        try:
            await container.invoke(action)
        except ValidationException as error:
            assert "quantity" in error.errors
        else:
            raise AssertionError("An invalid body was accepted")
    assert await container.invoke(action, Payload(quantity=9)) == 11

asyncio.run(main())
```

### 7. Iniciar un provider diferido multicontrato y facade global

La Application temporal ejecuta registro y boot eager reales; los lookups
concurrentes activan una vez el provider diferido custom. Se esperan ambos
contratos listos, despacho await/context sin pin y acceso síncrono directo
tras pinear. La restauración de cwd y limpieza de logs temporales son explícitas.

```python
import asyncio
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

previous = Path.cwd()
with tempfile.TemporaryDirectory(prefix="container-provider-") as directory:
    os.chdir(directory)
    try:
        from orionis.container.facades.facade import Facade
        from orionis.container.providers import DeferrableProvider, ServiceProvider
        from orionis.foundation.application import Application

        class Catalogue:
            label = "catalogue"

            def count(self) -> int:
                return 7

            @asynccontextmanager
            async def context(self):
                yield self

        class Secondary:
            pass

        class CatalogueProvider(ServiceProvider, DeferrableProvider):
            registrations = 0
            boots = 0

            @classmethod
            def provides(cls) -> list[type | str]:
                return [Catalogue, Secondary, "docs.catalogue", "docs.secondary"]

            def register(self) -> None:
                type(self).registrations += 1
                self.app.singleton(None, Catalogue, alias="docs.catalogue")
                self.app.singleton(None, Secondary, alias="docs.secondary")

            async def boot(self) -> None:
                type(self).boots += 1
                await self.app.make(Catalogue)
                await asyncio.sleep(0)

        class CatalogueFacade(Facade):
            @classmethod
            def getFacadeAccessor(cls) -> type:
                return Catalogue

        async def main() -> None:
            app = Application(base_path=Path(directory))
            app.withProviders(CatalogueProvider)
            await app.boot()
            assert CatalogueProvider.registrations == 0
            first, second = await asyncio.gather(
                app.make(Catalogue), app.make("docs.secondary"),
            )
            assert isinstance(second, Secondary)
            assert CatalogueProvider.registrations == CatalogueProvider.boots == 1
            assert await CatalogueFacade.count() == 7
            assert await CatalogueFacade.label() == "catalogue"
            async with CatalogueFacade.context() as entered:
                assert entered is first
            await CatalogueFacade.pin()
            assert CatalogueFacade.count() == 7 and CatalogueFacade.label == "catalogue"
            CatalogueFacade.unpin()

        asyncio.run(main())
    finally:
        logging.shutdown()
        os.chdir(previous)
```

## Características de diseño

| Mecanismo observado | Consecuencia concreta |
| --- | --- |
| Registro singleton de Container e inicialización idempotente | Construirlo de nuevo conserva registros; subclases diferentes tienen identidad propia y normalmente comparten el registro indexado por clase. |
| Binding e InvocationPlan dataclasses frozen | Resisten asignación a campos generados, no mutación profunda. Binding tiene dict de instancia; InvocationPlan usa slots. Los métodos generados no son declaraciones literales. |
| Slots de ScopeManager y token ContextVar | Sin dict por manager; los contextos anidados restauran el scope previo y los hijos pueden retener el mismo objeto cerrado. |
| Contratos ABC sin __slots__ | Describen operaciones, no implementaciones sin diccionario ni validación runtime de anotaciones. Container/providers conservan dicts de instancia. |
| Plan bound indexado por función, no receptor | Controllers diferentes comparten metadatos sin retener cada receptor. Funciones/clases/defaults referenciados siguen ocupando cachés acotados. |
| Despacho de atributo ausente por metaclase | Atributos reales evitan proxies; pin cambia comportamiento en esa clase globalmente; ScopedFacade consulta el scope activo cada vez. |
| Identidad de provider y registros pending | Contratos anunciados comparten startup/reintentos; register publica servicios, pero resolución externa coincidente espera boot. |

## Rendimiento y concurrencia

### Cachés y estado retenido

Fuentes: [container.py](../container.py), [invocation.py](../entities/invocation.py),
[scope manager](../context/manager.py), [metadatos de facade](../facades/meta.py).
Diccionarios singleton/alias/binding, providers registrados/pending, registro
de creation locks y Container._instances no tienen límite/reset público.
La instancia de provider completo se elimina del registro de reintento;
su identidad queda marcada lista. Cancelar antes de publicar no cachea el
resultado singleton/scoped, pero no deshace efectos de constructor/register.

El plan materializa parámetros ordenados en tuple. Cada despacho construye
lista posicional y dict keyword, lee bindings actuales y no modifica el dict
del consumidor expandido mediante **kwargs. Reflexión tiene otros LRU
acotados en su módulo. El caché de dispatchers es **no acotado** por (clase,
name); sus funciones retienen clase/nombre y crean un objeto pending por
llamada. Pins retienen servicios. No se realizaron benchmarks ni afirmaciones
de tasa de asignación para esta tarea.

### Límites entre tareas, scopes, loops e hilos

Container.__new__ serializa creación por subclase con threading.RLock. No
serializa __init__ concurrentes, registros, callbacks ni todo uso de servicios.
La docstring limita otras garantías al trabajo one-shot en un loop.
Los servicios mutables deben gestionar su propia seguridad.

Construcción singleton/diferida usa lock por clave de contenedor asociado al
loop actual; otro loop reemplaza esa entrada, sin exclusión global cross-loop.
La construcción scoped usa locks del ScopeManager: scopes independientes
pueden construir concurrentemente, contendientes del mismo scope comparten
construcción y no hay reemplazo del lock de un loop distinto en el scope.
No suponga seguro compartir un manager entre hilos o loops.

No se configuran timeout, grafo global de esperas, teardown de recursos ni
garantía de equidad. Cancelación libera locks async-with y restaura tokens;
el reintento de boot conserva el provider registrado correctamente. Hijos
con stack heredado pueden participar en bootstrap del padre. Registrar o
reemplazar durante construcción suspendida no es una transacción; el módulo
no garantiza esa combinación.

Entradas `async def` pueden ejecutar construcción, reflexión, evaluación de
anotaciones, imports, register y handlers síncronos en el hilo del loop. No
hay offload general a executor en Container. Await de facade diferida trata
resultados awaitable; despacho ordinario no añade esa segunda regla. Vaciar
scope o gestionar pins maneja referencias, no apaga recursos automáticamente.

## Notas de compatibilidad

El mínimo declarado es Python >=3.14. El checkout usa uniones, genéricos
built-in, slots dataclass, ContextVar, locks/tasks asyncio y resolución de
anotaciones inspect/typing. Valide contra el target declarado, no contra un
mínimo de sintaxis anterior inferido. Todas las ejecuciones usaron **CPython
3.14.6 en Windows**; no se ejecutaron otros runtimes/plataformas.

| Dependencia | Rango declarado | Resolución en lockfile | Versión instalada de validación |
| --- | --- | --- | --- |
| msgspec (core, integración reflexión/schema) | >=0.21.1 | 0.22.0 | 0.22.0 |
| markdown (core; validación documental aquí) | >=3.10.3,<4.0 | 3.11 | 3.11 |
| ruff (lint de desarrollo) | >=0.16.8 | 0.16.9 | 0.16.9 |

Evidencia: [pyproject.toml](../../../pyproject.toml), [uv.lock](../../../uv.lock)
y metadatos instalados locales registrados en esta ejecución. Las versiones
de lock son resoluciones, no mínimos soportados. Dependencias de despliegue
opcionales pertenecen a componentes inyectados; no se instaló ninguna nueva.

Anotaciones string/future resolubles en globals del módulo participan ahora
en inyección de callables, con restauración local a clase en constructores.
Nombres desconocidos, typing no soportado y metadatos obsoletos del mismo
objeto siguen siendo límites distintos. Los parámetros con default conservan
metadatos derivados de este. None no equivale a no proporcionar valor. Estas
distinciones sustituyen suposiciones antiguas de docs/instrucciones; no se
modificó fuente para reconciliarlas.

## Verificación y limitaciones

### Inventario y pruebas

El inventario cubre 23 fuentes, 17 clases públicas, 61 métodos públicos o
especiales, tres funciones públicas de planes, cuatro bloques de campos,
nueve bloques alias/export y 94 bloques literales. Cada candidato público
se mapea a fuente y grupo de API; nombres importados de librerías y typing T
están explícitamente excluidos. Detalles privados se describen cuando
controlan comportamiento público, no como API de extensión independiente.

TestingEngine y TestRunner nativos usaron Application temporal real booteada
y una vista de discovery con basePath hacia las pruebas inspeccionadas y
caché de resultados desactivado. **253 descubiertas, 253 ejecutadas, 253
correctas**, sin fallos/errores crudos ni omisiones. Un audit hook bloqueó
escrituras ajenas al temporal, procesos externos y conexiones de servicios;
no hubo operaciones denegadas en el run correcto. El primer harness bloqueó
el socketpair interno de asyncio Windows antes de discovery; se permitió
únicamente esa operación stdlib y se repitió, sin modificar framework/tests.

Otra prueba aislada confirmó identidad de scope en hijo, estado cerrado
visible y rechazo de publicación tardía. Las pruebas existentes verifican
precedencia explícita, planes/release de receptor, hints future de constructor,
readiness/reintento multicontrato, construcción en scopes independientes y
reintento tras cancelar construcción. Sus escenarios no prueban seguridad
universal entre hilos o loops.

### Estado de ejemplos y documentos

| Ejemplo | Sintaxis | Imports locales | Ejecución |
| --- | --- | --- | --- |
| 1 | Correcta | Correctos | Ejecutado correctamente. |
| 2 | Correcta | Correctos | Ejecutado correctamente. |
| 3 | Correcta | Correctos | Ejecutado correctamente. |
| 4 | Correcta | Correctos | Ejecutado correctamente. |
| 5 | Correcta | Correctos | Ejecutado correctamente. |
| 6 | Correcta | Correctos | Ejecutado correctamente. |
| 7 | Correcta | Correctos | Ejecutado correctamente. |

Ambos manuales tienen 60 encabezados equivalentes y 101 bloques idénticos byte
a byte. Los 94 bloques de referencia coinciden con sus declaraciones y los
90 candidatos públicos están mapeados a su grupo de API. Los siete scripts
de cada idioma pasaron sintaxis, imports locales reales y ejecución independiente.
Se comprobaron 105 enlaces relativos/anclas por manual y 19 del skill. Su YAML
válido solo contiene name y description, con nombre derivado orionis-container.
Ruff acotado a orionis/container y tests/container pasó sin fixes ni caché;
el editor no informa errores en los tres entregables.

Scripts, resultados registrados y árboles de recursos quedan fuera del
repositorio. La instantánea inicial completa incluye ocultos, ignorados y no
versionados y todos los cambios de documentación previos. Fuentes, pruebas,
configuración y documentación de otros módulos se comparan contra ese baseline,
no contra un HEAD supuestamente limpio. La comparación final registra aparte
el cambio ajeno descrito abajo; no se eliminó contenido adicional de docs,
que contiene solo README.md, README.es.md y SKILL.md, sin subdirectorios.

### Límites restantes

Discrepancias verificadas: prioridad de parámetros explícitos, nombres ordinarios
args/kwargs, restauración de hints string, locks propios del scope, lifecycle
distinto de ScopedFacade y register no-op pese al error de su docstring.
Los errores de callbacks/dependencias no constituyen lista exhaustiva. Esta
tarea no aplicó fixes, formato automático, benchmarks, instalaciones ni cambios
del índice Git.

> ⚠️ No especificado en el código fuente: atomicidad de registro/reemplazo frente a construcción en curso, seguridad cross-loop/thread de todo el módulo o disposición automática de servicios almacenados/pineados.

> ⚠️ No ejecutado en este entorno: tráfico HTTP desplegado, servicios externos de dependencias inyectadas, ejecución Linux/macOS/free-threaded o Python distinto de 3.14.6.

La comparación completa observó contenido cambiado ajeno en PUBLISH.ps1
tras el baseline. Esta tarea lo conservó sin modificar ni revertir; comparar
solo estado Git omitiría ese archivo ignorado. Índice Git, HEAD y cambios
versionados previos se comprueban independientemente. Las ejecuciones bloquearon
escrituras ajenas al temporal y las ediciones apuntaron solo a container/docs.
No puede certificarse que todo el árbol externo permanezca intacto debido a
ese cambio concurrente; no se atribuye silenciosamente a esta tarea ni se
deshace para fabricar un resultado limpio.
