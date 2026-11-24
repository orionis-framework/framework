# Modelos, atributos y persistencia

## Definir la entidad

Un modelo concreto hereda de `Model` y declara columnas con los tipos exportados por `orionis.orm`. Este ejemplo es ejecutable sin base de datos:

```python
from typing import ClassVar
from orionis.orm import Boolean, Integer, Model, String


class Article(Model):
    id = Integer().primary().autoIncrement()
    title = String(180)
    status = String(30).default("draft")
    internal_token = String(80).nullable()
    published = Boolean().default(False)
    timestamps = False
    fillable: ClassVar[list[str]] = ["title", "status", "published"]
    hidden: ClassVar[list[str]] = ["internal_token"]
    casts: ClassVar[dict[str, str]] = {"published": "bool"}
    appends: ClassVar[list[str]] = ["label"]

    def setTitleAttribute(self, value: str) -> str:
        return value.strip()

    def getLabelAttribute(self, value=None) -> str:
        return self.title.upper()


article = Article({"title": " Orionis ", "published": "yes"})
assert Article.__meta__.table_name == "articles"
assert article.title == "Orionis"
assert article.published is True
assert article.toDict()["label"] == "ORIONIS"
assert article.isDirty("title")
```

La tabla deriva del nombre de clase mediante snake case y pluralización. Usa `table = "content_articles"` cuando la convención no encaje y `connection = "reporting"` para una conexión registrada. `primary_key`, `incrementing` y `uuids` adaptan la identidad. `uuids=True` genera una identidad cliente al guardar; declara también la columna y adapta `incrementing` si la clave no es una identidad de servidor.

Declara `created_at` y `updated_at` con tipos de fecha si quieres mantenimiento automático de timestamps. `timestamps=True` por sí solo **no añade columnas**. Los nombres se personalizan con `CREATED_AT` y `UPDATED_AT`. `table_definition` permite compartir una definición versionada con [migraciones](../../../database/docs/es/schema.md); no puede combinarse con columnas inline ni opciones de tabla/PK contradictorias.

`freshTimestamp()` devuelve un instante con la zona horaria de la aplicación. El ORM persiste los timestamps de creación, actualización y borrado lógico en UTC según la opción de cada columna. Al leer estas columnas, interpreta los valores sin zona como UTC, incluidas las filas históricas. Al asignar un valor sin zona al modelo, usa la hora de la aplicación. Puedes sobrescribir `newUniqueId()` para personalizar la generación de identidades.

## Controlar entrada y salida

El constructor, `fill()` y `update(attributes)` aplican asignación masiva. `fillable` es una lista permitida; `guarded` bloquea atributos y admite `"*"`. Una columna desconocida o no permitida produce `MassAssignmentException`. Una lista `fillable` vacía permite todas las columnas no bloqueadas: configura una política explícita para datos externos.

La asignación directa (`article.status = "published"`) y `setAttribute` aplican mutadores/casts, pero no la lista `fillable`. Úsalas únicamente desde lógica confiable. Un mutador devuelve el valor a almacenar; luego se aplica el cast. Los casts disponibles son `int`, `float`, `bool`, `datetime`, `date`, `json` y `uuid`; `None` permanece `None`. Los casts no sustituyen validación de entrada ni restricciones SQL.

El cast `datetime` devuelve un `pendulum.DateTime` en la zona horaria de la aplicación. Interpreta los valores sin zona como hora local de la aplicación y convierte los valores con zona y los timestamps POSIX sin cambiar el instante que representan.

Una columna de negocio con cast `datetime` guarda la hora civil de la aplicación si su tipo SQL descarta el desplazamiento. Sus valores históricos reciben la misma interpretación. Durante el cambio al horario de invierno, dos instantes pueden tener la misma hora civil. Para conservar esa distinción en los campos de negocio se necesita un tipo y un motor que conserven el desplazamiento o una representación UTC explícita. El cast `date` extrae el día local de un `datetime` y conserva las fechas puras.

`toDict()`/`serialize()` convierten los atributos y relaciones cargadas; `hidden` excluye secretos y `appends` incorpora accessors calculados. `toJson(**kwargs)` produce JSON. `only(*keys)` y `exclude(*keys)` seleccionan desde la representación serializada. Ocultar una columna no cifra su contenido ni impide consultarla.

## Guardar y actualizar

Después del arranque y con la tabla creada, una función de aplicación puede recibir el modelo anterior:

```python
async def publish(article: Article) -> bool:
    article.status = "published"
    article.published = True
    return await article.save()
```

`save()` inserta instancias nuevas y actualiza solo atributos sucios de instancias recuperadas. Devuelve `False` si un evento previo veta la operación o una actualización no encuentra la fila almacenada. Esa escritura fallida no emite eventos posteriores de éxito. `await Article.create({...})` devuelve la instancia, pero actualmente no expone como resultado booleano el veto de `save()`: si necesitas comprobar persistencia explícita, construye el modelo y comprueba `await model.save()`.

Los modelos recuperados mediante una conexión seleccionada conservan esa conexión exacta para las escrituras posteriores de instancia. Las instancias nuevas utilizan la política de conexión de su modelo.

`find(id)` y `first()` devuelven modelo o `None`; sus variantes `OrFail` lanzan `ModelNotFoundException`. `update({...})` de instancia devuelve booleano; `delete()` devuelve booleano y respeta soft deletes. Las [operaciones de builder](querying.md) devuelven recuentos y no equivalen al ciclo de cada instancia.

`getDirty`, `isDirty`, `isClean`, `getOriginal`, `wasChanged` y `getChanges` ayudan a decidir qué cambió antes/después de guardar. Un atributo recién asignado está sucio aunque no tuviera valor original. `syncOriginal()` publica una nueva instantánea original solo después de copiar correctamente todos los valores. No constituyen bloqueo optimista: dos escritores pueden sobrescribir cambios. Para unidades atómicas utiliza [transacciones](../../../database/docs/es/transactions.md) y, si el motor lo admite, locks adecuados.
