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

`freshTimestamp()` genera hora UTC y respeta la opción `timezone` de la columna de actualización, creación o borrado elegida, en ese orden. Una columna sin timezone usa datetime naive UTC; no representa automáticamente hora local. `newUniqueId()` se puede sobrescribir para una política de identidad cliente distinta del UUID predeterminado.

## Controlar entrada y salida

El constructor, `fill()` y `update(attributes)` aplican asignación masiva. `fillable` es una lista permitida; `guarded` bloquea atributos y admite `"*"`. Una columna desconocida o no permitida produce `MassAssignmentException`. Una lista `fillable` vacía permite todas las columnas no bloqueadas: configura una política explícita para datos externos.

La asignación directa (`article.status = "published"`) y `setAttribute` aplican mutadores/casts, pero no la lista `fillable`. Úsalas únicamente desde lógica confiable. Un mutador devuelve el valor a almacenar; luego se aplica el cast. Los casts disponibles son `int`, `float`, `bool`, `datetime`, `date`, `json` y `uuid`; `None` permanece `None`. Los casts no sustituyen validación de entrada ni restricciones SQL.

`toDict()`/`serialize()` convierten los atributos y relaciones cargadas; `hidden` excluye secretos y `appends` incorpora accessors calculados. `toJson(**kwargs)` produce JSON. `only(*keys)` y `exclude(*keys)` seleccionan desde la representación serializada. Ocultar una columna no cifra su contenido ni impide consultarla.

## Guardar y actualizar

Después del arranque y con la tabla creada, una función de aplicación puede recibir el modelo anterior:

```python
async def publish(article: Article) -> bool:
    article.status = "published"
    article.published = True
    return await article.save()
```

`save()` inserta instancias nuevas y actualiza solo atributos sucios de instancias recuperadas. Devuelve `False` si un evento previo veta la operación. `await Article.create({...})` devuelve la instancia, pero actualmente no expone como resultado booleano el veto de `save()`: si necesitas comprobar persistencia explícita, construye el modelo y comprueba `await model.save()`.

`find(id)` y `first()` devuelven modelo o `None`; sus variantes `OrFail` lanzan `ModelNotFoundException`. `update({...})` de instancia devuelve booleano; `delete()` devuelve booleano y respeta soft deletes. Las [operaciones de builder](querying.md) devuelven recuentos y no equivalen al ciclo de cada instancia.

`getDirty`, `isDirty`, `isClean`, `getOriginal`, `wasChanged` y `getChanges` ayudan a decidir qué cambió antes/después de guardar. No constituyen bloqueo optimista: dos escritores pueden sobrescribir cambios. Para unidades atómicas utiliza [transacciones](../../../database/docs/es/transactions.md) y, si el motor lo admite, locks adecuados.
